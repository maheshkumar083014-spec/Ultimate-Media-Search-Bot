from flask import Flask, request, jsonify, render_template_string
import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os, hashlib, secrets, re

app = Flask(__name__)

# ==================== 🔐 CONFIGURATION ====================
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '0'))
ADMIN_SECRET = os.environ.get('ADMIN_SECRET', 'admin_secret_key')

# Firebase Config (Environment Variables se load)
firebase_config = {
    "type": "service_account",
    "project_id": os.environ.get('FIREBASE_PROJECT_ID'),
    "private_key_id": os.environ.get('FIREBASE_PRIVATE_KEY_ID'),
    "private_key": os.environ.get('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n'),
    "client_email": os.environ.get('FIREBASE_CLIENT_EMAIL'),
    "client_id": os.environ.get('FIREBASE_CLIENT_ID'),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": os.environ.get('FIREBASE_CLIENT_X509_CERT_URL')
}

# Initialize Firebase
try:
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
except:
    db = None  # Fallback for local testing

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# ==================== 🎨 WELCOME CARD HTML (Glassmorphism) ====================
WELCOME_CARD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome - Ultimate Media Search</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .welcome-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 24px;
            padding: 40px 30px;
            max-width: 420px;
            width: 100%;
            text-align: center;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.4);
            animation: slideUp 0.6s ease;
        }
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .profile-img {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            object-fit: cover;
            border: 4px solid rgba(255, 255, 255, 0.3);
            margin: 0 auto 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        }
        .welcome-title {
            font-size: 28px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 8px;
            text-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }
        .welcome-subtitle {
            color: rgba(255, 255, 255, 0.9);
            font-size: 16px;
            margin-bottom: 24px;
            line-height: 1.5;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin: 24px 0;
        }
        .stat-box {
            background: rgba(255, 255, 255, 0.15);
            padding: 16px 12px;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .stat-value {
            font-size: 22px;
            font-weight: 700;
            color: #FFD93D;
            margin-bottom: 4px;
        }
        .stat-label {
            font-size: 12px;
            color: rgba(255, 255, 255, 0.8);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .earn-info {
            background: rgba(255, 107, 53, 0.2);
            border: 1px solid rgba(255, 107, 53, 0.4);
            border-radius: 12px;
            padding: 16px;
            margin: 20px 0;
            text-align: left;
        }
        .earn-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            color: rgba(255, 255, 255, 0.95);
            font-size: 14px;
            border-bottom: 1px dashed rgba(255,255,255,0.2);
        }
        .earn-item:last-child { border-bottom: none; }
        .earn-points {
            background: linear-gradient(135deg, #FF6B35, #F7931E);
            padding: 4px 12px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 13px;
        }
        .dashboard-btn {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            background: linear-gradient(135deg, #FF6B35, #F7931E);
            color: white;
            text-decoration: none;
            padding: 16px 32px;
            border-radius: 16px;
            font-weight: 600;
            font-size: 16px;
            margin-top: 10px;
            transition: all 0.3s;
            box-shadow: 0 10px 30px rgba(255, 107, 53, 0.4);
            border: none;
            cursor: pointer;
            width: 100%;
            justify-content: center;
        }
        .dashboard-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 40px rgba(255, 107, 53, 0.6);
        }
        .footer-note {
            margin-top: 24px;
            font-size: 12px;
            color: rgba(255, 255, 255, 0.6);
        }
        .sparkle {
            position: absolute;
            width: 4px;
            height: 4px;
            background: white;
            border-radius: 50%;
            animation: sparkle 2s infinite;
            opacity: 0;
        }
        @keyframes sparkle {
            0%, 100% { opacity: 0; transform: scale(0); }
            50% { opacity: 1; transform: scale(1); }
        }
    </style>
</head>
<body>
    <div class="welcome-card">
        <img src="https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg" 
             alt="Welcome" class="profile-img">
        
        <h1 class="welcome-title">👋 Welcome, {{name}}!</h1>
        <p class="welcome-subtitle">Your journey to earn rewards starts now</p>
        
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-value" id="balance">0</div>
                <div class="stat-label">Balance</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="totalEarned">0</div>
                <div class="stat-label">Total Earned</div>
            </div>
        </div>
        
        <div class="earn-info">
            <div class="earn-item">
                <span>📺 View Ads</span>
                <span class="earn-points">+25 pts</span>
            </div>
            <div class="earn-item">
                <span>👍 Social Tasks</span>
                <span class="earn-points">+100 pts</span>
            </div>
            <div class="earn-item">
                <span>💵 Withdrawal Rate</span>
                <span class="earn-points">$1 = 100 pts</span>
            </div>
        </div>
        
        <a href="https://ultimate-media-search-bot-t7kj.vercel.app/dashboard?id={{uid}}&name={{name}}" 
           class="dashboard-btn" target="_blank">
            🚀 Open Dashboard
        </a>
        
        <p class="footer-note">✨ Complete daily tasks & earn real money!</p>
    </div>

    <script>
        // Animate stats on load
        document.addEventListener('DOMContentLoaded', () => {
            animateValue('balance', 0, {{balance}}, 1500);
            animateValue('totalEarned', 0, {{totalEarned}}, 1500);
        });
        
        function animateValue(id, start, end, duration) {
            const obj = document.getElementById(id);
            let startTimestamp = null;
            const step = (timestamp) => {
                if (!startTimestamp) startTimestamp = timestamp;
                const progress = Math.min((timestamp - startTimestamp) / duration, 1);
                const value = Math.floor(progress * (end - start) + start);
                obj.textContent = value.toLocaleString();
                if (progress < 1) window.requestAnimationFrame(step);
            };
            window.requestAnimationFrame(step);
        }
    </script>
</body>
</html>
'''

# ==================== 🎨 DASHBOARD HTML (Glassmorphism) ====================
DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Dashboard - Ultimate Media Search</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://www.gstatic.com/firebasejs/9.22.0/firebase-app-compat.js"></script>
    <script src="https://www.gstatic.com/firebasejs/9.22.0/firebase-firestore-compat.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --primary-orange: #FF6B35;
            --secondary-orange: #F7931E;
            --dark-bg: #1a1a2e;
            --glass-bg: rgba(255, 255, 255, 0.05);
            --glass-border: rgba(255, 255, 255, 0.1);
            --text-primary: #ffffff;
            --text-secondary: rgba(255, 255, 255, 0.7);
            --success: #00D9A3;
            --warning: #FFD93D;
        }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 20px;
            overflow-x: hidden;
        }
        .container { max-width: 480px; margin: 0 auto; }
        .glass-card {
            background: var(--glass-bg);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }
        .profile-header { text-align: center; margin-bottom: 30px; }
        .profile-image {
            width: 100px; height: 100px; border-radius: 50%;
            object-fit: cover; border: 3px solid var(--primary-orange);
            box-shadow: 0 0 30px rgba(255, 107, 53, 0.4);
            margin-bottom: 16px;
        }
        .user-name {
            font-size: 24px; font-weight: 700; margin-bottom: 8px;
            background: linear-gradient(135deg, var(--primary-orange), var(--secondary-orange));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .user-id { color: var(--text-secondary); font-size: 14px; }
        .balance-card {
            background: linear-gradient(135deg, rgba(255, 107, 53, 0.2), rgba(247, 147, 30, 0.1));
            border: 1px solid rgba(255, 107, 53, 0.3);
            text-align: center; padding: 30px;
        }
        .balance-label { font-size: 14px; color: var(--text-secondary); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }
        .balance-amount { font-size: 48px; font-weight: 700; color: var(--primary-orange); margin-bottom: 8px; }
        .balance-usd { font-size: 18px; color: var(--text-secondary); }
        .progress-container { margin: 20px 0; }
        .progress-label { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 14px; }
        .progress-bar { height: 12px; background: rgba(255, 255, 255, 0.1); border-radius: 10px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, var(--primary-orange), var(--secondary-orange)); border-radius: 10px; transition: width 0.5s ease; }
        .task-card { margin-bottom: 16px; }
        .task-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .task-title { font-size: 16px; font-weight: 600; }
        .task-points { background: linear-gradient(135deg, var(--primary-orange), var(--secondary-orange)); padding: 6px 12px; border-radius: 20px; font-size: 14px; font-weight: 600; }
        .task-link {
            width: 100%; padding: 14px; background: rgba(255, 107, 53, 0.1);
            border: 1px solid rgba(255, 107, 53, 0.3); border-radius: 12px;
            color: var(--primary-orange); text-decoration: none; display: block;
            text-align: center; font-weight: 500; margin-bottom: 12px;
        }
        .complete-btn {
            width: 100%; padding: 14px; background: linear-gradient(135deg, var(--primary-orange), var(--secondary-orange));
            border: none; border-radius: 12px; color: white; font-size: 16px;
            font-weight: 600; cursor: pointer; transition: all 0.3s;
        }
        .complete-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .timer-display { text-align: center; font-size: 24px; font-weight: 700; color: var(--warning); margin: 10px 0; display: none; }
        .timer-display.active { display: block; }
        .withdraw-btn {
            width: 100%; padding: 16px; background: linear-gradient(135deg, var(--success), #00B894);
            border: none; border-radius: 12px; color: white; font-size: 16px;
            font-weight: 600; cursor: pointer;
        }
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 20px; }
        .stat-item { text-align: center; padding: 16px; background: rgba(255, 255, 255, 0.03); border-radius: 12px; border: 1px solid var(--glass-border); }
        .stat-value { font-size: 24px; font-weight: 700; color: var(--primary-orange); margin-bottom: 4px; }
        .stat-label { font-size: 12px; color: var(--text-secondary); text-transform: uppercase; }
        .modal {
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.8); backdrop-filter: blur(5px); z-index: 1000;
            justify-content: center; align-items: center; padding: 20px;
        }
        .modal.active { display: flex; }
        .modal-content {
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            border: 1px solid var(--glass-border); border-radius: 24px;
            padding: 30px; width: 100%; max-width: 400px; position: relative;
        }
        .modal-header { font-size: 20px; font-weight: 700; margin-bottom: 20px; text-align: center; }
        .form-group { margin-bottom: 16px; }
        .form-label { display: block; margin-bottom: 8px; font-size: 14px; color: var(--text-secondary); }
        .form-input, .form-select {
            width: 100%; padding: 12px; background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--glass-border); border-radius: 8px;
            color: var(--text-primary); font-size: 14px;
        }
        .close-modal {
            position: absolute; top: 20px; right: 20px; background: none;
            border: none; color: var(--text-secondary); font-size: 24px; cursor: pointer;
        }
        .toast {
            position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%) translateY(100px);
            background: var(--glass-bg); backdrop-filter: blur(10px);
            border: 1px solid var(--glass-border); padding: 16px 24px;
            border-radius: 12px; z-index: 2000; transition: transform 0.3s;
        }
        .toast.show { transform: translateX(-50%) translateY(0); }
        .toast.success { border-color: var(--success); }
        .toast.error { border-color: #FF4757; }
        .section-title { font-size: 18px; font-weight: 600; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
        .section-title::before { content: ''; width: 4px; height: 20px; background: linear-gradient(180deg, var(--primary-orange), var(--secondary-orange)); border-radius: 2px; }
        .empty-state { text-align: center; padding: 40px; color: var(--text-secondary); }
        .empty-state-icon { font-size: 48px; margin-bottom: 16px; opacity: 0.5; }
        .loading { display: inline-block; width: 20px; height: 20px; border: 3px solid rgba(255,255,255,0.3); border-radius: 50%; border-top-color: white; animation: spin 1s infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <div class="profile-header">
            <img src="https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg" alt="Profile" class="profile-image">
            <h1 class="user-name" id="userName">Loading...</h1>
            <p class="user-id" id="userId">ID: ...</p>
        </div>
        <div class="glass-card balance-card">
            <div class="balance-label">Available Balance</div>
            <div class="balance-amount" id="balance">0</div>
            <div class="balance-usd">≈ $<span id="balanceUSD">0.00</span></div>
            <div class="stats-grid">
                <div class="stat-item"><div class="stat-value" id="totalEarned">0</div><div class="stat-label">Total Earned</div></div>
                <div class="stat-item"><div class="stat-value" id="adsViewed">0</div><div class="stat-label">Ads Viewed</div></div>
            </div>
        </div>
        <div class="glass-card">
            <div class="section-title">Daily Ad Progress</div>
            <div class="progress-container">
                <div class="progress-label"><span>Ads Viewed</span><span id="adProgressText">0 / 2000</span></div>
                <div class="progress-bar"><div class="progress-fill" id="adProgressBar" style="width: 0%"></div></div>
            </div>
        </div>
        <div class="glass-card">
            <div class="section-title">Daily Tasks</div>
            <div id="tasksContainer"><div class="empty-state"><div class="empty-state-icon">📋</div><p>Loading tasks...</p></div></div>
        </div>
        <div class="glass-card"><button class="withdraw-btn" onclick="openWithdrawModal()">💰 Request Payout</button></div>
    </div>
    <div class="modal" id="withdrawModal">
        <div class="modal-content">
            <button class="close-modal" onclick="closeWithdrawModal()">×</button>
            <div class="modal-header">Request Withdrawal</div>
            <form id="withdrawForm">
                <div class="form-group"><label class="form-label">Amount (Points)</label><input type="number" class="form-input" id="withdrawAmount" min="100" required><small style="color: var(--text-secondary); font-size: 12px;">Minimum: 100 points ($1)</small></div>
                <div class="form-group"><label class="form-label">Payment Method</label><select class="form-select" id="paymentMethod" required><option value="">Select method</option><option value="paypal">PayPal</option><option value="crypto">Cryptocurrency</option><option value="bank">Bank Transfer</option></select></div>
                <div class="form-group"><label class="form-label">Payment Details</label><input type="text" class="form-input" id="paymentDetails" placeholder="Enter your payment details" required></div>
                <button type="submit" class="complete-btn">Submit Request</button>
            </form>
        </div>
    </div>
    <div class="toast" id="toast"></div>
    <script>
        const tg = window.Telegram.WebApp; tg.expand(); tg.ready();
        const urlParams = new URLSearchParams(window.location.search);
        const userId = urlParams.get('id'); const userName = urlParams.get('name') || 'User';
        const firebaseConfig = { apiKey: "YOUR_API_KEY", authDomain: "YOUR_PROJECT.firebaseapp.com", projectId: "YOUR_PROJECT_ID", storageBucket: "YOUR_PROJECT.appspot.com", messagingSenderId: "YOUR_SENDER_ID", appId: "YOUR_APP_ID" };
        firebase.initializeApp(firebaseConfig); const db = firebase.firestore();
        let userData = null, currentTaskId = null, timerInterval = null;
        async function loadUserData() {
            try {
                const response = await fetch(`/api/user/${userId}`);
                const data = await response.json();
                if (data.success) { userData = data.data; updateUserUI(); }
                else showToast('Failed to load user data', 'error');
            } catch (error) { showToast('Connection error', 'error'); }
        }
        function updateUserUI() {
            document.getElementById('userName').textContent = userName;
            document.getElementById('userId').textContent = `ID: ${userId}`;
            document.getElementById('balance').textContent = userData.balance || 0;
            document.getElementById('balanceUSD').textContent = ((userData.balance || 0) / 100).toFixed(2);
            document.getElementById('totalEarned').textContent = userData.totalEarned || 0;
            document.getElementById('adsViewed').textContent = userData.adsViewed || 0;
            const adsViewed = userData.adsViewed || 0;
            const progressPercent = Math.min((adsViewed / 2000) * 100, 100);
            document.getElementById('adProgressBar').style.width = `${progressPercent}%`;
            document.getElementById('adProgressText').textContent = `${adsViewed} / 2000`;
        }
        async function loadTasks() {
            try {
                const response = await fetch('/api/tasks');
                const data = await response.json();
                const container = document.getElementById('tasksContainer');
                if (data.tasks.length === 0) { container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">📋</div><p>No tasks available</p></div>`; return; }
                container.innerHTML = data.tasks.map(task => `<div class="glass-card task-card" data-task-id="${task.id}"><div class="task-header"><div class="task-title">${task.title}</div><div class="task-points">+${task.points} pts</div></div><a href="${task.link}" target="_blank" class="task-link" onclick="startTask('${task.id}', '${task.type}')">🔗 Visit Link</a><div class="timer-display" id="timer-${task.id}">30s</div><button class="complete-btn" id="btn-${task.id}" onclick="completeTask('${task.id}', '${task.type}')" disabled>⏱️ Wait 30 seconds</button></div>`).join('');
            } catch (error) { console.error('Error loading tasks:', error); }
        }
        function startTask(taskId, type) {
            currentTaskId = taskId;
            const btn = document.getElementById(`btn-${taskId}`), timer = document.getElementById(`timer-${taskId}`);
            let seconds = 30; btn.disabled = true; timer.classList.add('active');
            timerInterval = setInterval(() => { seconds--; timer.textContent = `${seconds}s`; if (seconds <= 0) { clearInterval(timerInterval); btn.disabled = false; btn.textContent = '✅ Complete Task'; timer.classList.remove('active'); }}, 1000);
        }
        async function completeTask(taskId, type) {
            const btn = document.getElementById(`btn-${taskId}`); btn.innerHTML = '<span class="loading"></span>'; btn.disabled = true;
            try {
                const response = await fetch('/api/complete-task', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ userId: userId, taskId: taskId, type: type }) });
                const data = await response.json();
                if (data.success) { showToast(`+${data.points} points added!`, 'success'); await loadUserData(); const taskCard = document.querySelector(`[data-task-id="${taskId}"]`); if (taskCard) { taskCard.style.opacity = '0.5'; taskCard.querySelector('.complete-btn').textContent = '✓ Completed'; }}
                else { showToast(data.error || 'Task already completed', 'error'); btn.textContent = '✓ Completed'; }
            } catch (error) { showToast('Error completing task', 'error'); btn.textContent = '⚠️ Try Again'; btn.disabled = false; }
        }
        function openWithdrawModal() { document.getElementById('withdrawModal').classList.add('active'); document.getElementById('withdrawAmount').value = Math.max(100, userData.balance || 0); }
        function closeWithdrawModal() { document.getElementById('withdrawModal').classList.remove('active'); }
        document.getElementById('withdrawForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const amount = document.getElementById('withdrawAmount').value, paymentMethod = document.getElementById('paymentMethod').value, paymentDetails = document.getElementById('paymentDetails').value;
            try {
                const response = await fetch('/api/withdraw', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ userId: userId, amount: parseInt(amount), paymentMethod: paymentMethod, paymentDetails: paymentDetails }) });
                const data = await response.json();
                if (data.success) { showToast('Withdrawal request submitted!', 'success'); closeWithdrawModal(); await loadUserData(); }
                else showToast(data.error || 'Withdrawal failed', 'error');
            } catch (error) { showToast('Error submitting request', 'error'); }
        });
        function showToast(message, type = 'success') { const toast = document.getElementById('toast'); toast.textContent = message; toast.className = `toast ${type} show`; setTimeout(() => { toast.classList.remove('show'); }, 3000); }
        document.addEventListener('DOMContentLoaded', () => { loadUserData(); loadTasks(); setInterval(() => { loadUserData(); loadTasks(); }, 30000); });
        tg.onEvent('themeChanged', () => {});
    </script>
</body>
</html>
'''

# ==================== 🔧 ADMIN PANEL HTML ====================
ADMIN_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel - Ultimate Media Search</title>
    <script src="https://www.gstatic.com/firebasejs/9.22.0/firebase-app-compat.js"></script>
    <script src="https://www.gstatic.com/firebasejs/9.22.0/firebase-firestore-compat.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root { --primary: #6366f1; --primary-dark: #4f46e5; --success: #10b981; --danger: #ef4444; --warning: #f59e0b; --bg: #0f172a; --card-bg: rgba(30, 41, 59, 0.7); --border: rgba(148, 163, 184, 0.1); --text: #f1f5f9; --text-muted: #94a3b8; }
        body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; padding-bottom: 20px; border-bottom: 1px solid var(--border); }
        .header h1 { font-size: 28px; font-weight: 700; background: linear-gradient(135deg, var(--primary), #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 40px; }
        .stat-card { background: var(--card-bg); backdrop-filter: blur(10px); border: 1px solid var(--border); border-radius: 16px; padding: 24px; }
        .stat-label { font-size: 14px; color: var(--text-muted); margin-bottom: 8px; }
        .stat-value { font-size: 32px; font-weight: 700; color: var(--text); }
        .section { background: var(--card-bg); backdrop-filter: blur(10px); border: 1px solid var(--border); border-radius: 16px; padding: 24px; margin-bottom: 30px; }
        .section-title { font-size: 20px; font-weight: 600; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
        .form-group { margin-bottom: 20px; }
        .form-label { display: block; margin-bottom: 8px; font-size: 14px; color: var(--text-muted); }
        .form-input, .form-select, .form-textarea { width: 100%; padding: 12px; background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border); border-radius: 8px; color: var(--text); font-size: 14px; font-family: inherit; }
        .form-input:focus, .form-select:focus, .form-textarea:focus { outline: none; border-color: var(--primary); }
        .btn { padding: 12px 24px; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.3s; display: inline-flex; align-items: center; gap: 8px; }
        .btn-primary { background: linear-gradient(135deg, var(--primary), var(--primary-dark)); color: white; }
        .btn-success { background: var(--success); color: white; }
        .btn-danger { background: var(--danger); color: white; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3); }
        .task-list { display: flex; flex-direction: column; gap: 12px; }
        .task-item { background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border); border-radius: 12px; padding: 16px; display: flex; justify-content: space-between; align-items: center; }
        .task-info h4 { margin-bottom: 4px; }
        .task-info p { font-size: 13px; color: var(--text-muted); }
        .task-actions { display: flex; gap: 8px; }
        .user-table { width: 100%; border-collapse: collapse; }
        .user-table th, .user-table td { padding: 12px; text-align: left; border-bottom: 1px solid var(--border); }
        .user-table th { color: var(--text-muted); font-weight: 600; font-size: 13px; text-transform: uppercase; }
        .badge { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
        .badge-success { background: rgba(16, 185, 129, 0.2); color: var(--success); }
        .badge-warning { background: rgba(245, 158, 11, 0.2); color: var(--warning); }
        .badge-danger { background: rgba(239, 68, 68, 0.2); color: var(--danger); }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.8); z-index: 1000; justify-content: center; align-items: center; padding: 20px; }
        .modal.active { display: flex; }
        .modal-content { background: var(--card-bg); border: 1px solid var(--border); border-radius: 16px; padding: 30px; width: 100%; max-width: 500px; max-height: 90vh; overflow-y: auto; }
        .toast { position: fixed; bottom: 20px; right: 20px; padding: 16px 24px; border-radius: 8px; z-index: 2000; animation: slideIn 0.3s ease; }
        @keyframes slideIn { from { transform: translateX(400px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        .toast.success { background: var(--success); color: white; }
        .toast.error { background: var(--danger); color: white; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header"><h1>🔧 Admin Panel</h1><button class="btn btn-primary" onclick="openTaskModal()">+ Add Task</button></div>
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-label">Total Users</div><div class="stat-value" id="totalUsers">0</div></div>
            <div class="stat-card"><div class="stat-label">Active Tasks</div><div class="stat-value" id="activeTasks">0</div></div>
            <div class="stat-card"><div class="stat-label">Pending Withdrawals</div><div class="stat-value" id="pendingWithdrawals">0</div></div>
            <div class="stat-card"><div class="stat-label">Total Paid</div><div class="stat-value" id="totalPaid">$0</div></div>
        </div>
        <div class="section">
            <div class="section-title">📢 Broadcast Message</div>
            <div class="form-group"><label class="form-label">Message</label><textarea class="form-textarea" id="broadcastMessage" rows="3" placeholder="Enter message to send to all users..."></textarea></div>
            <button class="btn btn-primary" onclick="broadcastMessage()">Send to All Users</button>
        </div>
        <div class="section">
            <div class="section-title">📋 Daily Tasks</div>
            <div class="task-list" id="taskList"><p style="color: var(--text-muted);">Loading tasks...</p></div>
        </div>
        <div class="section">
            <div class="section-title">💰 Withdrawal Requests</div>
            <table class="user-table"><thead><tr><th>User</th><th>Amount</th><th>Method</th><th>Details</th><th>Status</th><th>Actions</th></tr></thead><tbody id="withdrawalsList"><tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Loading...</td></tr></tbody></table>
        </div>
        <div class="section">
            <div class="section-title">👥 All Users</div>
            <table class="user-table"><thead><tr><th>ID</th><th>Name</th><th>Balance</th><th>Total Earned</th><th>Joined</th><th>Status</th></tr></thead><tbody id="usersList"><tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Loading...</td></tr></tbody></table>
        </div>
    </div>
    <div class="modal" id="taskModal">
        <div class="modal-content">
            <h2 style="margin-bottom: 20px;">Add New Task</h2>
            <form id="taskForm">
                <div class="form-group"><label class="form-label">Task Title</label><input type="text" class="form-input" id="taskTitle" required></div>
                <div class="form-group"><label class="form-label">Task Link</label><input type="url" class="form-input" id="taskLink" required></div>
                <div class="form-group"><label class="form-label">Task Type</label><select class="form-select" id="taskType" required><option value="ad">Advertisement (+25 points)</option><option value="social">Social Task (+100 points)</option></select></div>
                <div class="form-group"><label class="form-label">Points</label><input type="number" class="form-input" id="taskPoints" value="25" required></div>
                <div style="display: flex; gap: 10px;"><button type="button" class="btn" onclick="closeTaskModal()" style="background: var(--border);">Cancel</button><button type="submit" class="btn btn-primary">Create Task</button></div>
            </form>
        </div>
    </div>
    <script>
        const firebaseConfig = { apiKey: "YOUR_API_KEY", authDomain: "YOUR_PROJECT.firebaseapp.com", projectId: "YOUR_PROJECT_ID", storageBucket: "YOUR_PROJECT.appspot.com", messagingSenderId: "YOUR_SENDER_ID", appId: "YOUR_APP_ID" };
        firebase.initializeApp(firebaseConfig); const db = firebase.firestore();
        async function loadDashboard() {
            try {
                const usersSnapshot = await db.collection('users').get();
                document.getElementById('totalUsers').textContent = usersSnapshot.size;
                const tasksSnapshot = await db.collection('tasks').where('active', '==', true).get();
                document.getElementById('activeTasks').textContent = tasksSnapshot.size;
                renderTasks(tasksSnapshot);
                const withdrawalsSnapshot = await db.collection('withdrawals').where('status', '==', 'pending').get();
                document.getElementById('pendingWithdrawals').textContent = withdrawalsSnapshot.size;
                renderWithdrawals(withdrawalsSnapshot);
                const paidSnapshot = await db.collection('withdrawals').where('status', '==', 'approved').get();
                let totalPaid = 0; paidSnapshot.forEach(doc => { totalPaid += doc.data().amountUSD || 0; });
                document.getElementById('totalPaid').textContent = `$${totalPaid.toFixed(2)}`;
                renderUsers(usersSnapshot);
            } catch (error) { console.error('Error loading dashboard:', error); showToast('Error loading data', 'error'); }
        }
        function renderTasks(snapshot) { const container = document.getElementById('taskList'); if (snapshot.empty) { container.innerHTML = '<p style="color: var(--text-muted);">No active tasks</p>'; return; } container.innerHTML = snapshot.docs.map(doc => { const task = doc.data(); return `<div class="task-item"><div class="task-info"><h4>${task.title}</h4><p>${task.link} • ${task.points} points • ${task.type}</p></div><div class="task-actions"><button class="btn btn-danger" onclick="deleteTask('${doc.id}')">Delete</button></div></div>`; }).join(''); }
        function renderWithdrawals(snapshot) { const container = document.getElementById('withdrawalsList'); if (snapshot.empty) { container.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No pending withdrawals</td></tr>'; return; } container.innerHTML = snapshot.docs.map(doc => { const withdrawal = doc.data(); return `<tr><td>${withdrawal.userName}</td><td>$${withdrawal.amountUSD} (${withdrawal.amount} pts)</td><td>${withdrawal.paymentMethod}</td><td>${withdrawal.paymentDetails}</td><td><span class="badge badge-warning">Pending</span></td><td><button class="btn btn-success" onclick="approveWithdrawal('${doc.id}')">Approve</button><button class="btn btn-danger" onclick="rejectWithdrawal('${doc.id}')">Reject</button></td></tr>`; }).join(''); }
        function renderUsers(snapshot) { const container = document.getElementById('usersList'); container.innerHTML = snapshot.docs.map(doc => { const user = doc.data(); const joinDate = user.joinedAt ? new Date(user.joinedAt.seconds * 1000).toLocaleDateString() : 'N/A'; return `<tr><td>${user.userId}</td><td>${user.name}</td><td>${user.balance || 0}</td><td>${user.totalEarned || 0}</td><td>${joinDate}</td><td><span class="badge ${user.isBanned ? 'badge-danger' : 'badge-success'}">${user.isBanned ? 'Banned' : 'Active'}</span></td></tr>`; }).join(''); }
        document.getElementById('taskForm').addEventListener('submit', async (e) => { e.preventDefault(); const task = { title: document.getElementById('taskTitle').value, link: document.getElementById('taskLink').value, type: document.getElementById('taskType').value, points: parseInt(document.getElementById('taskPoints').value), active: true, createdAt: firebase.firestore.FieldValue.serverTimestamp() }; try { await db.collection('tasks').add(task); showToast('Task created successfully', 'success'); closeTaskModal(); loadDashboard(); await broadcastNewTask(task); } catch (error) { showToast('Error creating task', 'error'); } });
        async function broadcastNewTask(task) { try { await fetch('/api/broadcast', { method: 'POST', headers: {'Content-Type': 'application/json', 'Authorization': process.env.ADMIN_SECRET}, body: JSON.stringify({ message: `🎯 <b>New Task Available!</b>\\n\\n${task.title}\\n\\n💰 Reward: ${task.points} points\\n\\nComplete it now in your dashboard!`, taskId: 'latest' }) }); } catch (error) { console.error('Broadcast error:', error); } }
        async function deleteTask(taskId) { if (!confirm('Delete this task?')) return; try { await db.collection('tasks').doc(taskId).update({ active: false }); showToast('Task deleted', 'success'); loadDashboard(); } catch (error) { showToast('Error deleting task', 'error'); } }
        async function approveWithdrawal(withdrawalId) { if (!confirm('Approve this withdrawal?')) return; try { await db.collection('withdrawals').doc(withdrawalId).update({ status: 'approved', approvedAt: firebase.firestore.FieldValue.serverTimestamp() }); showToast('Withdrawal approved', 'success'); loadDashboard(); } catch (error) { showToast('Error approving withdrawal', 'error'); } }
        async function rejectWithdrawal(withdrawalId) { if (!confirm('Reject this withdrawal? Balance will be refunded.')) return; try { const withdrawalDoc = await db.collection('withdrawals').doc(withdrawalId).get(); const withdrawal = withdrawalDoc.data(); await db.collection('users').doc(withdrawal.userId).update({ balance: firebase.firestore.FieldValue.increment(withdrawal.amount) }); await db.collection('withdrawals').doc(withdrawalId).update({ status: 'rejected', rejectedAt: firebase.firestore.FieldValue.serverTimestamp() }); showToast('Withdrawal rejected and balance refunded', 'success'); loadDashboard(); } catch (error) { showToast('Error rejecting withdrawal', 'error'); } }
        async function broadcastMessage() { const message = document.getElementById('broadcastMessage').value; if (!message) { showToast('Please enter a message', 'error'); return; } try { const response = await fetch('/api/broadcast', { method: 'POST', headers: {'Content-Type': 'application/json', 'Authorization': process.env.ADMIN_SECRET}, body: JSON.stringify({ message }) }); const data = await response.json(); if (data.success) { showToast(`Message sent to ${data.sentTo} users`, 'success'); document.getElementById('broadcastMessage').value = ''; } else { showToast('Error sending message', 'error'); } } catch (error) { showToast('Error sending message', 'error'); } }
        function openTaskModal() { document.getElementById('taskModal').classList.add('active'); }
        function closeTaskModal() { document.getElementById('taskModal').classList.remove('active'); document.getElementById('taskForm').reset(); }
        function showToast(message, type = 'success') { const toast = document.createElement('div'); toast.className = `toast ${type}`; toast.textContent = message; document.body.appendChild(toast); setTimeout(() => { toast.remove(); }, 3000); }
        document.addEventListener('DOMContentLoaded', loadDashboard);
    </script>
</body>
</html>
'''

# ==================== 🤖 TELEGRAM BOT FUNCTIONS ====================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Send Welcome Card when user sends /start"""
    user_id = message.from_user.id
    name = message.from_user.first_name
    
    # Create/Update user in Firestore
    if db:
        user_ref = db.collection('users').document(str(user_id))
        user_doc = user_ref.get()
        if not user_doc.exists:
            user_ref.set({
                'userId': str(user_id), 'name': name,
                'username': message.from_user.username or '',
                'balance': 0, 'adsViewed': 0, 'totalEarned': 0,
                'joinedAt': firestore.SERVER_TIMESTAMP,
                'lastActive': firestore.SERVER_TIMESTAMP, 'isBanned': False
            })
        else:
            user_ref.update({'lastActive': firestore.SERVER_TIMESTAMP, 'name': name})
    
    # ✅ Send Welcome Card as Web Page (HTML)
    welcome_url = f"https://ultimate-media-search-bot-t7kj.vercel.app/welcome?id={user_id}&name={name}"
    
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("🚀 Open Welcome Card", url=welcome_url)
    markup.add(btn)
    
    caption = (
        f"👋 <b>Welcome, {name}!</b>\n\n"
        f"🎯 <b>Ultimate Media Search Bot</b>\n\n"
        f"✨ Earn money by completing simple tasks:\n"
        f"• View Ads: +25 points\n"
        f"• Social Tasks: +100 points\n\n"
        f"💰 <b>Withdrawal:</b> $1 = 100 points\n\n"
        f"🎁 <b>Click below for your personalized Welcome Card!</b>"
    )
    
    photo_url = "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg"
    bot.send_photo(message.chat.id, photo_url, caption=caption, reply_markup=markup)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Access Denied")
        return
    markup = types.InlineKeyboardMarkup()
    admin_url = f"https://ultimate-media-search-bot-t7kj.vercel.app/admin?token={secrets.token_urlsafe(32)}"
    btn = types.InlineKeyboardButton("🔧 Open Admin Panel", url=admin_url)
    markup.add(btn)
    bot.reply_to(message, "🔧 Admin Panel Access", reply_markup=markup)

# ==================== 🌐 FLASK ROUTES ====================

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data(as_text=True)
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return '', 400

@app.route('/')
def index():
    return "✅ Ultimate Media Search Bot API is running!"

@app.route('/welcome')
def welcome_card():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    balance = 0
    total_earned = 0
    if db:
        user_doc = db.collection('users').document(uid).get()
        if user_doc.exists:
            data = user_doc.to_dict()
            balance = data.get('balance', 0)
            total_earned = data.get('totalEarned', 0)
    return render_template_string(WELCOME_CARD_HTML, uid=uid, name=name, balance=balance, totalEarned=total_earned)

@app.route('/dashboard')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/admin')
def admin():
    token = request.args.get('token')
    if token and db:
        # Verify admin token (add your logic here)
        pass
    return render_template_string(ADMIN_HTML)

@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    if not db:
        return jsonify({'success': False, 'error': 'Database not connected'}), 500
    user_ref = db.collection('users').document(user_id)
    user_doc = user_ref.get()
    if user_doc.exists:
        return jsonify({'success': True, 'data': user_doc.to_dict()})
    return jsonify({'success': False, 'error': 'User not found'}), 404

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    if not db:
        return jsonify({'success': True, 'tasks': []})
    tasks_ref = db.collection('tasks').where('active', '==', True).order_by('createdAt', direction=firestore.Query.DESCENDING)
    tasks = []
    for task in tasks_ref.stream():
        task_data = task.to_dict()
        task_data['id'] = task.id
        tasks.append(task_data)
    return jsonify({'success': True, 'tasks': tasks})

@app.route('/api/complete-task', methods=['POST'])
def complete_task():
    data = request.json
    user_id, task_id, task_type = data.get('userId'), data.get('taskId'), data.get('type')
    if not all([user_id, task_id, task_type]) or not db:
        return jsonify({'success': False, 'error': 'Missing parameters'}), 400
    
    @firestore.transactional
    def update_in_transaction(transaction, user_ref, task_ref):
        user_doc = user_ref.get(transaction=transaction)
        if not user_doc.exists: return False
        user_data = user_doc.to_dict()
        if user_data.get('isBanned'): return False
        today = datetime.now().date().isoformat()
        completed_tasks = user_data.get('completedTasks', {})
        if task_id in completed_tasks.get(today, []): return False
        points = 25 if task_type == 'ad' else 100
        new_balance = user_data.get('balance', 0) + points
        new_total = user_data.get('totalEarned', 0) + points
        if task_type == 'ad':
            new_ads = user_data.get('adsViewed', 0) + 1
            transaction.update(user_ref, {'balance': new_balance, 'totalEarned': new_total, 'adsViewed': new_ads, 'lastActive': firestore.SERVER_TIMESTAMP})
        else:
            transaction.update(user_ref, {'balance': new_balance, 'totalEarned': new_total, 'lastActive': firestore.SERVER_TIMESTAMP})
        if today not in completed_tasks: completed_tasks[today] = []
        completed_tasks[today].append(task_id)
        transaction.update(user_ref, {'completedTasks': completed_tasks})
        return True
    
    user_ref = db.collection('users').document(user_id)
    task_ref = db.collection('tasks').document(task_id)
    transaction = db.transaction()
    success = update_in_transaction(transaction, user_ref, task_ref)
    if success:
        return jsonify({'success': True, 'points': 25 if task_type == 'ad' else 100})
    return jsonify({'success': False, 'error': 'Task already completed or invalid'}), 400

@app.route('/api/withdraw', methods=['POST'])
def request_withdrawal():
    data = request.json
    user_id, amount, payment_method, payment_details = data.get('userId'), data.get('amount'), data.get('paymentMethod'), data.get('paymentDetails')
    if not all([user_id, amount, payment_method, payment_details]) or not db:
        return jsonify({'success': False, 'error': 'Missing parameters'}), 400
    amount = int(amount)
    if amount < 100:
        return jsonify({'success': False, 'error': 'Minimum withdrawal is 100 points ($1)'}), 400
    
    @firestore.transactional
    def process_withdrawal(transaction, user_ref):
        user_doc = user_ref.get(transaction=transaction)
        if not user_doc.exists: return False
        user_data = user_doc.to_dict()
        if user_data.get('balance', 0) < amount: return False
        transaction.update(user_ref, {'balance': user_data['balance'] - amount})
        withdrawal_ref = db.collection('withdrawals').document()
        transaction.set(withdrawal_ref, {
            'userId': user_id, 'userName': user_data.get('name', ''),
            'amount': amount, 'amountUSD': amount / 100,
            'paymentMethod': payment_method, 'paymentDetails': payment_details,
            'status': 'pending', 'createdAt': firestore.SERVER_TIMESTAMP
        })
        return True
    
    user_ref = db.collection('users').document(user_id)
    transaction = db.transaction()
    success = process_withdrawal(transaction, user_ref)
    if success:
        return jsonify({'success': True, 'message': 'Withdrawal request submitted'})
    return jsonify({'success': False, 'error': 'Insufficient balance'}), 400

@app.route('/api/broadcast', methods=['POST'])
def broadcast():
    auth_header = request.headers.get('Authorization')
    if auth_header != ADMIN_SECRET or not db:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    data = request.json
    message_text, task_id = data.get('message'), data.get('taskId')
    if not message_text:
        return jsonify({'success': False, 'error': 'Message required'}), 400
    users_ref = db.collection('users').where('isBanned', '==', False).stream()
    sent_count = 0
    for user_doc in users_ref:
        user_data = user_doc.to_dict()
        uid = user_data.get('userId')
        try:
            if task_id:
                markup = types.InlineKeyboardMarkup()
                dashboard_url = f"https://ultimate-media-search-bot-t7kj.vercel.app/dashboard?id={uid}&task={task_id}"
                btn = types.InlineKeyboardButton("Complete Task Now 🎯", url=dashboard_url)
                markup.add(btn)
                bot.send_message(uid, message_text, reply_markup=markup)
            else:
                bot.send_message(uid, message_text)
            sent_count += 1
        except: continue
    return jsonify({'success': True, 'sentTo': sent_count})

if __name__ == '__main__':
    webhook_url = f"{os.environ.get('VERCEL_URL', 'http://localhost:5000')}/webhook"
    try:
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
    except: pass
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
