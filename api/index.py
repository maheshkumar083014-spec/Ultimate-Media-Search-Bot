"""
🤖 Ultimate Media Search Bot 2026
Full-stack Telegram Earn Bot with Firebase + Vercel Deployment
✅ Single-file serverless compatible
✅ Firebase REST API (asia-southeast1 region)
✅ Mobile-responsive Dashboard & Admin Panel
"""

import os
import sys
import json
import time
import logging
import hashlib
import secrets
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# ─────────────────────────────────────────────────────────────────────
# 🔧 Configuration & Logging
# ─────────────────────────────────────────────────────────────────────

os.environ['PYTHONIOENCODING'] = 'utf-8'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)
logger.info("🚀 Starting Ultimate Media Search Bot 2026...")

# Environment Variables
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8701635891:AAFmgU89KRhd2dhE-PqRY-mBmGy_SxQEGOg')
FIREBASE_DB_URL = os.environ.get(
    'FIREBASE_DB_URL',
    'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
).rstrip('/')

# App Configuration
APP_CONFIG = {
    'POINTS_PER_DOLLAR': 100,
    'AD_POINTS': 25,
    'SOCIAL_POINTS': 100,
    'REFERRAL_BONUS': 50,
    'MIN_WITHDRAW': 100,  # Points
    'AD_LINK': 'https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b',
    'YOUTUBE': 'https://youtube.com/@USSoccerPulse',
    'INSTAGRAM': 'https://instagram.com/digital_rockstar_m',
    'FACEBOOK': 'https://www.facebook.com/UltimateMediaSearch',
    'BANNER': 'https://i.ibb.co/9kmTw4Gh/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg'
}

# Frontend Firebase Config (Client-Side SDK - Safe to expose)
FIREBASE_CONFIG = {
    'apiKey': os.environ.get('FIREBASE_API_KEY', 'AIzaSyD50eWvysruXgtgpDhhCVE2zdbSbLkFBwk'),
    'authDomain': 'ultimatemediasearch.firebaseapp.com',
    'databaseURL': FIREBASE_DB_URL,
    'projectId': 'ultimatemediasearch',
    'storageBucket': 'ultimatemediasearch.firebasestorage.app',
    'messagingSenderId': '123003124713',
    'appId': os.environ.get('FIREBASE_APP_ID', '1:123003124713:web:c738c97b2772b112822978')
}

logger.info(f"✅ Config loaded | Firebase: {FIREBASE_DB_URL[:50]}...")

# ─────────────────────────────────────────────────────────────────────
# 🗄️ Firebase REST API Functions (No Admin SDK - Vercel Compatible)
# ─────────────────────────────────────────────────────────────────────

import requests

def fb_request(method, path, data=None):
    """Generic Firebase REST API request"""
    try:
        url = f"{FIREBASE_DB_URL}/{path}.json"
        headers = {'Content-Type': 'application/json'}
        timeout = 10
        
        if method == 'GET':
            resp = requests.get(url, headers=headers, timeout=timeout)
        elif method == 'PUT':
            resp = requests.put(url, json=data, headers=headers, timeout=timeout)
        elif method == 'PATCH':
            resp = requests.patch(url, json=data, headers=headers, timeout=timeout)
        elif method == 'POST':
            resp = requests.post(url, json=data, headers=headers, timeout=timeout)
        elif method == 'DELETE':
            resp = requests.delete(url, headers=headers, timeout=timeout)
        else:
            return None, "Invalid method"
        
        if resp.status_code in [200, 201]:
            return resp.json(), None
        logger.warning(f"Firebase {method} {resp.status_code}: {path}")
        return None, f"Firebase error: {resp.status_code}"
    except requests.Timeout:
        return None, "Firebase timeout"
    except Exception as e:
        logger.error(f"Firebase {method} error: {e}")
        return None, str(e)

def get_user(tid):
    """Get user from Firebase"""
    data, _ = fb_request('GET', f'users/{tid}')
    return data

def create_user(tid, name, username, referral_code=None):
    """Create new user in Firebase"""
    timestamp = int(time.time() * 1000)
    my_ref_code = 'UMS' + hashlib.sha256(f"{tid}{secrets.token_hex(4)}".encode()).hexdigest()[:6].upper()
    
    user_data = {
        'uid': tid,
        'name': name,
        'username': username,
        'referral_code': my_ref_code,
        'referred_by': referral_code,
        'points': 0,
        'pending_points': 0,
        'total_earned': 0,
        'total_withdrawn': 0,
        'ad_views': 0,
        'tasks_completed': 0,
        'joined_at': timestamp,
        'last_active': timestamp,
        'last_ad_date': '',
        'daily_ad_completed': False,
        'is_banned': False,
        'is_admin': False
    }
    
    success, error = fb_request('PUT', f'users/{tid}', user_data)
    
    if success and referral_code:
        # Reward referrer
        all_users, _ = fb_request('GET', 'users')
        if all_users:
            for uid, udata in all_users.items():
                if udata.get('referral_code') == referral_code:
                    fb_request('PATCH', f'users/{uid}', {
                        'points': (udata.get('points', 0) or 0) + APP_CONFIG['REFERRAL_BONUS'],
                        'total_earned': (udata.get('total_earned', 0) or 0) + APP_CONFIG['REFERRAL_BONUS'],
                        'referral_count': (udata.get('referral_count', 0) or 0) + 1
                    })
                    fb_request('PUT', f'referrals/{uid}/{tid}', {
                        'joined_at': timestamp,
                        'bonus': APP_CONFIG['REFERRAL_BONUS']
                    })
                    break
    
    logger.info(f"✅ User created: {tid} | Referral: {my_ref_code}")
    return user_data

def add_points(tid, points, type_, description=''):
    """Add points to user with history"""
    user = get_user(tid)
    if not user:
        return False, "User not found"
    
    timestamp = int(time.time() * 1000)
    updates = {
        'points': (user.get('points', 0) or 0) + points,
        'total_earned': (user.get('total_earned', 0) or 0) + points,
        'tasks_completed': (user.get('tasks_completed', 0) or 0) + 1,
        'last_active': timestamp,
        f'history/{timestamp}': {
            'points': points,
            'type': type_,
            'description': description,
            'timestamp': timestamp
        }
    }
    
    if type_ == 'ad_view':
        updates['ad_views'] = (user.get('ad_views', 0) or 0) + 1
    
    success, error = fb_request('PATCH', f'users/{tid}', updates)
    return success, error

logger.info("✅ Firebase functions ready")

# ─────────────────────────────────────────────────────────────────────
# 🌐 Flask Application
# ─────────────────────────────────────────────────────────────────────

from flask import Flask, request, jsonify, render_template_string, redirect, make_response

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()
app.config['JSON_AS_ASCII'] = False

logger.info("✅ Flask app initialized")

# ─────────────────────────────────────────────────────────────────────
# 🎨 HTML Templates (Inline for Vercel Compatibility)
# ─────────────────────────────────────────────────────────────────────

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="theme-color" content="#f59e0b">
<title>💰 Ultimate Media Search - Earn Dashboard</title>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-database-compat.js"></script>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--gold:#f59e0b;--gold-dark:#d97706;--brown:#78350f;--brown-dark:#451a03;--cream:#fef3c7;--glass:rgba(255,248,235,.9);--border:rgba(217,119,6,.3)}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:linear-gradient(180deg,#fef3c7 0%,#fde68a 20%,#f59e0b 40%,#d97706 60%,#92400e 80%,#78350f 100%);min-height:100vh;color:#292524;overflow-x:hidden;position:relative}
body::before{content:"";position:fixed;inset:0;background:radial-gradient(circle at 20% 20%,rgba(251,191,36,.25) 0%,transparent 50%),radial-gradient(circle at 80% 60%,rgba(217,119,6,.15) 0%,transparent 50%);z-index:0;pointer-events:none}
.container{max-width:480px;margin:0 auto;padding:16px;position:relative;z-index:1;padding-bottom:100px}
.welcome{text-align:center;padding:20px 0 10px}
.profile-ring{width:90px;height:90px;border-radius:50%;background:linear-gradient(135deg,#fbbf24,#d97706,#92400e);padding:3px;margin:0 auto 12px;animation:pulse 3s infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(245,158,11,.4)}50%{box-shadow:0 0 0 12px rgba(245,158,11,0)}}
.profile-img{width:100%;height:100%;border-radius:50%;object-fit:cover;border:3px solid #fffbeb}
.welcome-text{font-size:1.3rem;font-weight:700;color:#fff;text-shadow:0 2px 10px rgba(69,26,3,.3)}
.welcome-name{font-size:1.5rem;font-weight:800;color:#fffbeb;text-shadow:0 2px 15px rgba(69,26,3,.4)}
.card{background:var(--glass);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border:1px solid var(--border);border-radius:24px;padding:20px;margin-top:16px;box-shadow:0 8px 32px rgba(120,53,15,.2),inset 0 1px 0 rgba(255,255,255,.5)}
.card-title{font-size:1rem;font-weight:800;text-align:center;color:var(--brown-dark);text-transform:uppercase;letter-spacing:1px;margin-bottom:16px;padding-bottom:12px;border-bottom:2px solid rgba(217,119,6,.15)}
.task-section{background:rgba(254,243,199,.6);border:1px solid rgba(217,119,6,.2);border-radius:16px;padding:14px;margin-bottom:16px}
.task-section-title{font-size:.75rem;font-weight:700;color:var(--brown-dark);text-transform:uppercase;margin-bottom:12px}
.task-icons{display:flex;gap:8px;margin-bottom:12px}
.task-btn{width:48px;height:48px;border-radius:14px;display:flex;flex-direction:column;align-items:center;justify-content:center;border:none;cursor:pointer;transition:.2s}
.task-btn:active{transform:scale(.92)}.task-btn:disabled{opacity:.6;cursor:not-allowed}
.task-btn .icon{font-size:1.2rem}.task-btn .label{font-size:.5rem;font-weight:600;color:var(--brown)}
.task-btn.ad{background:linear-gradient(135deg,#bbf7d0,#86efac)}.task-btn.done{background:linear-gradient(135deg,#fef3c7,#fde68a)}.task-btn.off{background:linear-gradient(135deg,#fed7aa,#fdba74)}
.task-row{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid rgba(217,119,6,.1)}
.task-row:last-child{border:none}
.task-label{font-size:.8rem;font-weight:600;color:var(--brown-dark)}
.badge{padding:4px 12px;border-radius:20px;font-size:.65rem;font-weight:700;text-transform:uppercase}
.badge.done{background:rgba(34,197,94,.15);color:#16a34a;border:1px solid rgba(34,197,94,.3)}.badge.avail{background:rgba(59,130,246,.15);color:#2563eb;border:1px solid rgba(59,130,246,.3)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px}
.tracker,.withdraw{background:rgba(254,243,199,.6);border:1px solid rgba(217,119,6,.2);border-radius:16px;padding:14px}
.section-title{font-size:.7rem;font-weight:700;color:var(--brown-dark);text-transform:uppercase;margin-bottom:10px}
.tracker-info{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.tracker-badge{background:linear-gradient(135deg,#d97706,#92400e);color:#fff;padding:2px 6px;border-radius:4px;font-size:.55rem;font-weight:800}
.tracker-label{font-size:.6rem;color:#78716c}.tracker-value{font-size:.7rem;color:var(--brown-dark);font-weight:600}
.progress-big{text-align:center;margin:10px 0}.progress-num{font-size:1.2rem;font-weight:800;color:var(--brown-dark)}
.progress-bg{width:100%;height:7px;background:rgba(217,119,6,.15);border-radius:10px;overflow:hidden}
.progress-fill{height:100%;border-radius:10px;background:linear-gradient(90deg,#f59e0b,#d97706,#92400e);transition:width .8s ease-out}
.withdraw{text-align:center;display:flex;flex-direction:column;justify-content:center;align-items:center}
.balance-label{font-size:.6rem;color:#78716c;margin-bottom:4px}
.balance{font-size:1.6rem;font-weight:900;background:linear-gradient(135deg,#92400e,#451a03);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:10px}
.btn-withdraw{width:100%;padding:10px 16px;border-radius:12px;border:none;background:linear-gradient(135deg,#92400e,#78350f,#451a03);color:#fffbeb;font-size:.75rem;font-weight:700;cursor:pointer;text-transform:uppercase;box-shadow:0 4px 12px rgba(69,26,3,.3)}
.btn-withdraw:active{transform:scale(.96)}.btn-withdraw:disabled{opacity:.5;cursor:not-allowed}
.social-title{font-size:.75rem;font-weight:700;color:var(--brown-dark);text-transform:uppercase;margin-bottom:10px}
.social-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}
.social-card{background:rgba(254,243,199,.7);border:1px solid rgba(217,119,6,.2);border-radius:14px;padding:12px 8px;text-align:center;text-decoration:none;display:block;cursor:pointer;transition:.2s}
.social-card:active{transform:scale(.95)}
.social-icon{width:40px;height:40px;border-radius:12px;display:flex;align-items:center;justify-content:center;margin:0 auto 8px;font-size:1.1rem}
.social-icon.yt{background:linear-gradient(135deg,#fee2e2,#fecaca)}.social-icon.ig{background:linear-gradient(135deg,#fce7f3,#fbcfe8)}.social-icon.fb{background:linear-gradient(135deg,#dbeafe,#bfdbfe)}
.social-name{font-size:.6rem;font-weight:700;color:var(--brown-dark)}.social-handle{font-size:.5rem;color:#78716c}
.actions{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:16px}
.action-btn{padding:14px;border-radius:16px;border:none;font-size:.75rem;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px}
.action-btn:active{transform:scale(.96)}
.action-btn.primary{background:linear-gradient(135deg,#d97706,#92400e);color:#fff;box-shadow:0 4px 15px rgba(217,119,6,.4)}
.action-btn.secondary{background:rgba(255,255,255,.2);backdrop-filter:blur(10px);color:#fff;border:1px solid rgba(255,255,255,.3)}
.ref-card{background:linear-gradient(135deg,rgba(251,191,36,.2),rgba(217,119,6,.15));border:1px solid rgba(217,119,6,.25);border-radius:16px;padding:14px;margin-top:16px;text-align:center}
.ref-box{display:flex;align-items:center;background:rgba(255,255,255,.6);border-radius:10px;padding:8px 12px;margin:10px 0}
.ref-box code{flex:1;font-size:.65rem;color:var(--brown-dark);word-break:break-all}
.copy-btn{background:linear-gradient(135deg,#d97706,#92400e);color:#fff;border:none;padding:6px 12px;border-radius:8px;font-size:.65rem;font-weight:700;cursor:pointer}
.toast{position:fixed;top:20px;left:50%;transform:translateX(-50%) translateY(-100px);background:rgba(30,41,59,.95);backdrop-filter:blur(12px);color:#fff;padding:12px 24px;border-radius:14px;font-size:.8rem;font-weight:600;z-index:1000;transition:transform .4s cubic-bezier(.175,.885,.32,1.275);box-shadow:0 10px 40px rgba(0,0,0,.3);display:flex;align-items:center;gap:8px;max-width:90vw}
.toast.show{transform:translateX(-50%) translateY(0)}
.toast.success{border-left:4px solid #22c55e}.toast.error{border-left:4px solid #ef4444}.toast.info{border-left:4px solid #3b82f6}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.6);backdrop-filter:blur(4px);z-index:100;display:none;align-items:center;justify-content:center;padding:20px}
.modal.active{display:flex}
.modal-box{background:linear-gradient(145deg,#fffbeb,#fef3c7);border:1px solid rgba(217,119,6,.3);border-radius:24px;padding:24px;width:100%;max-width:360px;box-shadow:0 20px 60px rgba(0,0,0,.3);animation:modalIn .3s ease-out}
@keyframes modalIn{from{opacity:0;transform:scale(.9) translateY(20px)}to{opacity:1;transform:scale(1) translateY(0)}}
.modal-title{font-size:1rem;font-weight:800;color:var(--brown-dark);text-align:center;margin-bottom:16px}
.modal-input{width:100%;padding:12px 16px;border-radius:12px;border:1px solid rgba(217,119,6,.3);background:rgba(255,255,255,.8);font-size:.8rem;margin-bottom:12px;outline:none}
.modal-input:focus{border-color:var(--gold);box-shadow:0 0 0 3px rgba(245,158,11,.2)}
.modal-btn{width:100%;padding:12px;border-radius:12px;border:none;font-size:.8rem;font-weight:700;cursor:pointer}
.modal-btn.primary{background:linear-gradient(135deg,#d97706,#92400e);color:#fff;margin-bottom:8px}
.modal-btn.secondary{background:rgba(217,119,6,.1);color:var(--brown)}
.bottom-nav{position:fixed;bottom:0;left:0;right:0;background:rgba(255,248,235,.95);backdrop-filter:blur(20px);border-top:1px solid rgba(217,119,6,.2);padding:8px 16px;padding-bottom:max(8px,env(safe-area-inset-bottom));display:flex;justify-content:space-around;z-index:50}
.nav-item{display:flex;flex-direction:column;align-items:center;gap:2px;padding:6px 12px;border-radius:12px;cursor:pointer;border:none;background:none}
.nav-item.active{background:rgba(217,119,6,.15)}
.nav-item .icon{font-size:1.2rem}.nav-item .label{font-size:.55rem;font-weight:600;color:#78716c}
.nav-item.active .label{color:var(--gold-dark)}
.confetti{position:fixed;width:8px;height:8px;z-index:200;pointer-events:none}
::-webkit-scrollbar{width:0}
@media(max-width:360px){.container{padding:12px}.card{padding:16px}.balance{font-size:1.4rem}.progress-num{font-size:1rem}}
</style>
</head>
<body>
<div class="toast" id="toast"><span id="toastIcon">✅</span><span id="toastMsg">Success!</span></div>
<div class="modal" id="withdrawModal"><div class="modal-box">
<div class="modal-title">💰 Request Withdrawal</div>
<p style="font-size:.75rem;color:#78716c;text-align:center;margin-bottom:12px">Available: <strong id="modalBalance">$0.00</strong></p>
<select id="withdrawMethod" class="modal-input"><option value="">Select Payment</option><option value="paypal">💳 PayPal</option><option value="crypto">₿ USDT (TRC20)</option><option value="bank">🏦 Bank Transfer</option></select>
<input type="text" id="withdrawAddress" class="modal-input" placeholder="PayPal email / Wallet address">
<button class="modal-btn primary" onclick="submitWithdraw()">Submit Request</button>
<button class="modal-btn secondary" onclick="closeModal('withdrawModal')">Cancel</button>
</div></div>
<div class="modal" id="refModal"><div class="modal-box">
<div class="modal-title">👥 Invite Friends</div>
<p style="font-size:.75rem;color:#78716c;text-align:center;margin-bottom:12px">Earn <strong style="color:var(--gold-dark)">+50 Points</strong> per friend!</p>
<div class="ref-box"><code id="refLink">Loading...</code><button class="copy-btn" onclick="copyRef()">Copy</button></div>
<div style="display:flex;justify-content:space-around;margin:12px 0"><div style="text-align:center"><div style="font-size:1.2rem;font-weight:800;color:var(--brown-dark)" id="refCount">0</div><div style="font-size:.6rem;color:#78716c">Referrals</div></div><div style="text-align:center"><div style="font-size:1.2rem;font-weight:800;color:#22c55e" id="refEarn">0</div><div style="font-size:.6rem;color:#78716c">Points</div></div></div>
<button class="modal-btn primary" onclick="shareRef()">📤 Share on Telegram</button>
<button class="modal-btn secondary" onclick="closeModal('refModal')">Close</button>
</div></div>
<div class="container">
<div class="welcome"><div class="profile-ring"><img src="{{ banner }}" class="profile-img" onerror="this.style.display='none'"></div><div class="welcome-text">Welcome back,</div><div class="welcome-name" id="userName">Loading...</div></div>
<div class="card">
<div class="card-title"><span>📊 Your Ad-Earning Dashboard</span></div>
<div class="task-section">
<div class="task-section-title">📅 Today's Tasks</div>
<div class="task-icons">
<button class="task-btn ad" onclick="watchAd()" id="adBtn"><span class="icon">📺</span><span class="label" id="adLabel">Daily Ad</span></button>
<button class="task-btn done" onclick="showToast('Check completed tasks','info')"><span class="icon">✅</span><span class="label">Completed</span></button>
<button class="task-btn off" onclick="openOffer()"><span class="icon">💎</span><span class="label">Offerwall</span></button>
</div>
<div class="task-row"><span class="task-label">Daily Ad Stream</span><span class="badge done" id="adBadge">COMPLETED</span></div>
<div class="task-row"><span class="task-label">Offerwall Task</span><span class="badge avail">PENDING</span></div>
</div>
<div class="grid">
<div class="tracker">
<div class="section-title">📊 AD View Tracker</div>
<div class="tracker-info"><span class="tracker-badge">AD</span><div><div class="tracker-label">AD VIEWED:</div><div class="tracker-value" id="adSmall">0 / 2,000</div></div></div>
<div class="progress-big"><div class="progress-num" id="adBig">0 / 2,000</div></div>
<div class="progress-bg"><div class="progress-fill" id="progress" style="width:0%"></div></div>
</div>
<div class="withdraw">
<div class="section-title">💰 BALANCE</div>
<div class="balance-label">AVAILABLE:</div>
<div class="balance" id="balance">$0.00</div>
<button class="btn-withdraw" onclick="openWithdraw()" id="withdrawBtn">Request Payout</button>
</div>
</div>
<div style="margin-top:16px">
<div class="social-title">🔗 Social Media Tasks</div>
<div class="social-grid">
<a href="{{ youtube }}" target="_blank" onclick="claim('youtube')" class="social-card"><div class="social-icon yt">▶️</div><div class="social-name">YouTube</div><div class="social-handle">@USSoccerPulse</div></a>
<a href="{{ instagram }}" target="_blank" onclick="claim('instagram')" class="social-card"><div class="social-icon ig">📷</div><div class="social-name">Instagram</div><div class="social-handle">@digital_rockstar_m</div></a>
<a href="{{ facebook }}" target="_blank" onclick="claim('facebook')" class="social-card"><div class="social-icon fb">📘</div><div class="social-name">Facebook</div><div class="social-handle">UltimateMediaSearch</div></a>
</div>
</div>
</div>
<div class="social-grid" style="margin-top:8px">
<a href="{{ youtube }}" target="_blank" onclick="claim('youtube')" style="background:rgba(255,255,255,.15);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.2);border-radius:14px;padding:14px 8px;text-align:center;text-decoration:none;display:block;color:#fff"><div style="width:44px;height:44px;border-radius:50%;background:#ef4444;display:flex;align-items:center;justify-content:center;margin:0 auto 8px;font-size:1.2rem">▶️</div><div style="font-size:.65rem;font-weight:700">YouTube</div></a>
<a href="{{ instagram }}" target="_blank" onclick="claim('instagram')" style="background:rgba(255,255,255,.15);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.2);border-radius:14px;padding:14px 8px;text-align:center;text-decoration:none;display:block;color:#fff"><div style="width:44px;height:44px;border-radius:50%;background:linear-gradient(135deg,#f43f5e,#a855f7);display:flex;align-items:center;justify-content:center;margin:0 auto 8px;font-size:1.2rem">📷</div><div style="font-size:.65rem;font-weight:700">Instagram</div></a>
<a href="{{ facebook }}" target="_blank" onclick="claim('facebook')" style="background:rgba(255,255,255,.15);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.2);border-radius:14px;padding:14px 8px;text-align:center;text-decoration:none;display:block;color:#fff"><div style="width:44px;height:44px;border-radius:50%;background:#2563eb;display:flex;align-items:center;justify-content:center;margin:0 auto 8px;font-size:1.2rem">📘</div><div style="font-size:.65rem;font-weight:700">Facebook</div></a>
</div>
<div class="actions">
<button class="action-btn primary" onclick="openModal('refModal')">👥 Invite <span style="font-size:.65rem;opacity:.8">+50</span></button>
<button class="action-btn secondary" onclick="refresh()">🔄 Refresh</button>
</div>
<div class="ref-card">
<div style="font-size:.75rem;font-weight:700;color:var(--brown-dark);margin-bottom:8px">👥 Referral Stats</div>
<div style="display:flex;justify-content:space-around"><div><div style="font-size:1.1rem;font-weight:800;color:var(--gold-dark)" id="dRef">0</div><div style="font-size:.6rem;color:#78716c">Friends</div></div><div><div style="font-size:1.1rem;font-weight:800;color:#22c55e" id="dRefP">0</div><div style="font-size:.6rem;color:#78716c">Points</div></div><div><div style="font-size:1.1rem;font-weight:800;color:var(--brown-dark)" id="dTotal">$0.00</div><div style="font-size:.6rem;color:#78716c">Total</div></div></div>
</div>
</div>
<nav class="bottom-nav">
<button class="nav-item active"><span class="icon">🏠</span><span class="label">Home</span></button>
<button class="nav-item"><span class="icon">📋</span><span class="label">Tasks</span></button>
<button class="nav-item"><span class="icon">💰</span><span class="label">Earn</span></button>
<button class="nav-item"><span class="icon">👤</span><span class="label">Profile</span></button>
</nav>
<script>
const FC={{ firebase_config | safe }};firebase.initializeApp(FC);const db=firebase.database();const CFG={{ app_config | safe }};const P=new URLSearchParams(location.search);let UID=P.get('id');let UNAME=P.get('name')||'User';let UDATA={};let ADCOUNT=0;let CLAIMED=JSON.parse(localStorage.getItem('c_'+UID)||'{}');const tg=window.Telegram?.WebApp;if(tg){tg.ready();tg.expand();if(tg.initDataUnsafe?.user){UID=UID||tg.initDataUnsafe.user.id;UNAME=UNAME||tg.initDataUnsafe.user.first_name||'User';}}
document.addEventListener('DOMContentLoaded',()=>{if(!UID){document.body.innerHTML='<div style="padding:40px;text-align:center"><h2>⚠️ Open from Telegram Bot</h2></div>';return;}document.getElementById('userName').textContent=UNAME+'!';loadUser();});
async function loadUser(){try{const s=await db.ref('users/'+UID).once('value');let d=s.val();if(!d){const rc='UMS'+String(UID).slice(-6).toUpperCase();const newUser={uid:UID,name:UNAME,username:UNAME,referral_code:rc,points:0,total_earned:0,ad_views:0,tasks_completed:0,joined_at:Date.now(),last_ad_date:'',daily_ad_completed:false};await db.ref('users/'+UID).set(newUser);d=newUser;}UDATA=d;ADCOUNT=d.ad_views||0;db.ref('users/'+UID).on('value',snap=>{const data=snap.val();if(data){UDATA={...UDATA,...data};ADCOUNT=data.ad_views||0;updateUI();}});}catch(e){console.error(e);}}
function updateUI(){const p=UDATA.points||0;const u=(p/CFG.POINTS_PER_DOLLAR).toFixed(2);const pr=Math.min((ADCOUNT/2000)*100,100);document.getElementById('balance').textContent='$'+u;document.getElementById('modalBalance').textContent='$'+u;document.getElementById('adSmall').textContent=ADCOUNT.toLocaleString()+' / 2,000';document.getElementById('adBig').textContent=ADCOUNT.toLocaleString()+' / 2,000';document.getElementById('progress').style.width=pr+'%';const td=new Date().toDateString();const dn=(UDATA.last_ad_date||'')===td;const bg=document.getElementById('adBadge');bg.textContent=dn?'COMPLETED':'AVAILABLE';bg.className='badge '+(dn?'done':'avail');document.getElementById('withdrawBtn').disabled=p<CFG.MIN_WITHDRAW;const rc=UDATA.referral_count||0;document.getElementById('refCount').textContent=rc;document.getElementById('refEarn').textContent=rc*CFG.REFERRAL_BONUS;document.getElementById('dRef').textContent=rc;document.getElementById('dRefP').textContent=rc*CFG.REFERRAL_BONUS;document.getElementById('dTotal').textContent='$'+((UDATA.total_earned||0)/CFG.POINTS_PER_DOLLAR).toFixed(2);const rl='https://t.me/UltimateMediaSearchBot?start='+(UDATA.referral_code||'UMS'+String(UID).slice(-6).toUpperCase());document.getElementById('refLink').textContent=rl;}
async function watchAd(){const td=new Date().toDateString();if((UDATA.last_ad_date||'')===td){showToast('Already completed today!','info');return;}window.open(CFG.AD_LINK,'_blank');const btn=document.getElementById('adBtn');const lbl=document.getElementById('adLabel');btn.style.opacity='.6';btn.disabled=true;let s=30;const orig=lbl.textContent;const t=setInterval(async()=>{s--;lbl.textContent=s+'s';if(s<=0){clearInterval(t);try{await db.ref('users/'+UID).update({ad_views:(UDATA.ad_views||0)+1,points:(UDATA.points||0)+CFG.AD_POINTS,total_earned:(UDATA.total_earned||0)+CFG.AD_POINTS,last_ad_date:td});ADCOUNT=(UDATA.ad_views||0)+1;UDATA.points=(UDATA.points||0)+CFG.AD_POINTS;UDATA.total_earned=(UDATA.total_earned||0)+CFG.AD_POINTS;UDATA.last_ad_date=td;updateUI();showToast('🎉 +'+CFG.AD_POINTS+' Points!','success');btn.style.opacity='1';btn.disabled=false;lbl.textContent='Done';}catch(e){showToast('Failed','error');}}},1000);}
function openOffer(){window.open(CFG.AD_LINK,'_blank');showToast('💎 Offerwall opened!','info');}
async function claim(plat){if(CLAIMED[plat]){showToast('Already claimed!','info');return;}CLAIMED[plat]=true;localStorage.setItem('c_'+UID,JSON.stringify(CLAIMED));try{await db.ref('users/'+UID).update({points:(UDATA.points||0)+CFG.SOCIAL_POINTS,total_earned:(UDATA.total_earned||0)+CFG.SOCIAL_POINTS,tasks_completed:(UDATA.tasks_completed||0)+1});UDATA.points=(UDATA.points||0)+CFG.SOCIAL_POINTS;UDATA.total_earned=(UDATA.total_earned||0)+CFG.SOCIAL_POINTS;updateUI();showToast('🎉 +'+CFG.SOCIAL_POINTS+' Points!','success');}catch(e){showToast('Task recorded!','success');}}
function openWithdraw(){if((UDATA.points||0)<CFG.MIN_WITHDRAW){showToast('Need 100 points ($1)!','error');return;}document.getElementById('withdrawModal').classList.add('active');}
function openModal(id){document.getElementById(id).classList.add('active');}
function closeModal(id){document.getElementById(id).classList.remove('active');}
async function submitWithdraw(){const m=document.getElementById('withdrawMethod').value;const a=document.getElementById('withdrawAddress').value.trim();if(!m||!a){showToast('Fill all fields','error');return;}const p=UDATA.points||0;try{await db.ref('withdrawals/'+UID+'/'+Date.now()).set({amount:p,usd:(p/CFG.POINTS_PER_DOLLAR).toFixed(2),method:m,address:a,status:'pending',requested_at:Date.now()});await db.ref('users/'+UID).update({points:0,total_withdrawn:(UDATA.total_withdrawn||0)+p,pending_withdrawal:true});UDATA.points=0;closeModal('withdrawModal');updateUI();showToast('✅ Withdrawal submitted! 24-48h','success');}catch(e){showToast('Failed','error');}}
function copyRef(){navigator.clipboard.writeText(document.getElementById('refLink').textContent).then(()=>showToast('Copied!','success'));}
function shareRef(){const l=document.getElementById('refLink').textContent;if(tg)tg.openTelegramLink('https://t.me/share/url?url='+encodeURIComponent(l));else window.open('https://t.me/share/url?url='+encodeURIComponent(l),'_blank');}
function showToast(m,t='success'){const i={success:'✅',error:'❌',info:'ℹ️'};document.getElementById('toastIcon').textContent=i[t]||'✅';document.getElementById('toastMsg').textContent=m;const el=document.getElementById('toast');el.style.background=t==='green'?'rgba(34,197,94,.95)':t==='orange'?'rgba(245,158,11,.95)':'rgba(59,130,246,.95)';el.className='toast show';setTimeout(()=>el.className='toast',3000);}
function refresh(){showToast('🔄 Refreshing...','info');loadUser();}
document.querySelectorAll('.modal').forEach(m=>m.addEventListener('click',e=>{if(e.target===m)m.classList.remove('active');}));
</script>
</body>
</html>'''

ADMIN_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🔧 Admin Panel - Ultimate Media Search</title>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-database-compat.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#0f172a;color:#f1f5f9;min-height:100vh}
.container{max-width:900px;margin:0 auto;padding:20px}
.header{display:flex;justify-content:space-between;align-items:center;padding:16px 0;border-bottom:1px solid #334155;margin-bottom:24px}
.header h1{font-size:1.3rem;font-weight:700;color:#fbbf24}
.card{background:#1e293b;border:1px solid #334155;border-radius:16px;padding:20px;margin-bottom:16px}
.card-title{font-size:1rem;font-weight:700;color:#fbbf24;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid #334155}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:20px}
.stat{background:#0f172a;border:1px solid #334155;border-radius:12px;padding:16px;text-align:center}
.stat-value{font-size:1.5rem;font-weight:800;color:#fbbf24}.stat-label{font-size:.75rem;color:#94a3b8;margin-top:4px}
table{width:100%;border-collapse:collapse}
th,td{padding:12px;text-align:left;border-bottom:1px solid #334155;font-size:.85rem}
th{color:#94a3b8;font-weight:600}
.badge{padding:4px 10px;border-radius:20px;font-size:.7rem;font-weight:600}
.badge.pending{background:rgba(245,158,11,.15);color:#f59e0b}.badge.approved{background:rgba(34,197,94,.15);color:#22c55e}.badge.rejected{background:rgba(239,68,68,.15);color:#ef4444}
.btn{padding:8px 16px;border-radius:8px;border:none;font-size:.8rem;font-weight:600;cursor:pointer;margin:2px}
.btn-approve{background:rgba(34,197,94,.2);color:#22c55e}.btn-reject{background:rgba(239,68,68,.2);color:#ef4444}
.btn-broadcast{background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff}
.input{width:100%;padding:10px 14px;border-radius:8px;border:1px solid #334155;background:#0f172a;color:#f1f5f9;margin-bottom:10px;font-size:.9rem}
.input:focus{outline:none;border-color:#6366f1}
.toast{position:fixed;top:20px;right:20px;background:#1e293b;border-left:4px solid #22c55e;padding:12px 20px;border-radius:8px;z-index:1000;display:none}
.toast.show{display:block;animation:slideIn .3s ease}
@keyframes slideIn{from{transform:translateX(100%);opacity:0}to{transform:translateX(0);opacity:1}}
</style>
</head>
<body>
<div class="toast" id="toast">✅ Success!</div>
<div class="container">
<div class="header"><h1>🔧 Admin Panel</h1><button onclick="logout()" style="background:#334155;color:#f1f5f9;border:none;padding:8px 16px;border-radius:8px;cursor:pointer">Logout</button></div>
<div class="card">
<div class="card-title">📊 Platform Statistics</div>
<div class="stats-grid">
<div class="stat"><div class="stat-value" id="statUsers">0</div><div class="stat-label">Total Users</div></div>
<div class="stat"><div class="stat-value" id="statPoints">0</div><div class="stat-label">Points Distributed</div></div>
<div class="stat"><div class="stat-value" id="statPending">0</div><div class="stat-label">Pending Reviews</div></div>
<div class="stat"><div class="stat-value" id="statRate">0%</div><div class="stat-label">Approval Rate</div></div>
</div>
</div>
<div class="card">
<div class="card-title">📋 Pending Submissions</div>
<div id="submissionsList"><p style="color:#94a3b8;text-align:center;padding:20px">Loading...</p></div>
</div>
<div class="card">
<div class="card-title">📢 Broadcast Message</div>
<textarea id="broadcastMsg" class="input" rows="4" placeholder="Enter message to send to all users..."></textarea>
<button class="btn btn-broadcast" onclick="sendBroadcast()">Send to All Users</button>
</div>
</div>
<script>
const FC={{ firebase_config | safe }};firebase.initializeApp(FC);const db=firebase.database();const ADMIN_KEY='{{ admin_key }}';
document.addEventListener('DOMContentLoaded',()=>{if(!verifyAdmin()){document.body.innerHTML='<div style="padding:40px;text-align:center"><h2>🔐 Admin Access Required</h2></div>';return;}loadStats();loadSubmissions();});
function verifyAdmin(){const params=new URLSearchParams(location.search);return params.get('key')===ADMIN_KEY;}
function logout(){window.location.href='/';}
async function loadStats(){try{const usersSnap=await db.ref('users').once('value');const subsSnap=await db.ref('submissions').once('value');const users=usersSnap.val()||{};const subs=subsSnap.val()||{};const totalUsers=Object.keys(users).filter(k=>!users[k].is_banned).length;const totalPoints=Object.values(users).reduce((sum,u)=>sum+(u.total_earned||0),0);const pending=Object.values(subs).filter(s=>s.status==='pending').length;const reviewed=Object.values(subs).filter(s=>s.status==='approved'||s.status==='rejected');const approved=reviewed.filter(s=>s.status==='approved').length;const rate=reviewed.length?Math.round((approved/reviewed.length)*100):0;document.getElementById('statUsers').textContent=totalUsers;document.getElementById('statPoints').textContent=totalPoints.toLocaleString();document.getElementById('statPending').textContent=pending;document.getElementById('statRate').textContent=rate+'%';}catch(e){console.error(e);}}
async function loadSubmissions(){try{const snap=await db.ref('submissions').orderByChild('status').equalTo('pending').limitToFirst(20).once('value');const subs=snap.val();const list=document.getElementById('submissionsList');if(!subs||Object.keys(subs).length===0){list.innerHTML='<p style="color:#22c55e;text-align:center;padding:20px">🎉 No pending submissions!</p>';return;}list.innerHTML=Object.entries(subs).map(([id,s])=>`<table><tr><td><strong>${s.user_name||'Unknown'}</strong><br><small style="color:#94a3b8">${s.task_type||'task'}</small></td><td style="text-align:right"><span class="badge pending">Pending</span><br><button class="btn btn-approve" onclick="review('${id}',true)">✓</button><button class="btn btn-reject" onclick="review('${id}',false)">✗</button></td></tr></table>`).join('');}catch(e){console.error(e);}}
async function review(subId,approved){try{await db.ref('submissions/'+subId).update({status:approved?'approved':'rejected',reviewed_at:Date.now()});if(approved){const sub=await db.ref('submissions/'+subId).once('value');const data=sub.val();if(data&&data.user_id){await db.ref('users/'+data.user_id+'/points').transaction(p=>(p||0)+100);await db.ref('users/'+data.user_id+'/total_earned').transaction(e=>(e||0)+100);}}loadSubmissions();loadStats();showToast('Submission '+ (approved?'approved':'rejected'));}catch(e){showToast('Error: '+e.message,'error');}}
async function sendBroadcast(){const msg=document.getElementById('broadcastMsg').value.trim();if(!msg){showToast('Enter a message','error');return;}try{const usersSnap=await db.ref('users').once('value');const users=usersSnap.val()||{};let sent=0;for(const uid of Object.keys(users)){if(!users[uid].is_banned){await db.ref('users/'+uid+'/notifications').push({message:msg,sent_at:Date.now(),read:false});sent++;}}showToast('Sent to '+sent+' users!');document.getElementById('broadcastMsg').value='';}catch(e){showToast('Error: '+e.message,'error');}}
function showToast(msg,type='success'){const t=document.getElementById('toast');t.textContent=msg;t.style.borderLeftColor=type==='error'?'#ef4444':'#22c55e';t.className='toast show';setTimeout(()=>t.className='toast',3000);}
</script>
</body>
</html>'''

# ─────────────────────────────────────────────────────────────────────
# 🤖 Telegram Bot Initialization
# ─────────────────────────────────────────────────────────────────────

try:
    import telebot
    from telebot import types
    bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML', threaded=False)
    logger.info("✅ Telegram Bot initialized")
except Exception as e:
    logger.warning(f"⚠️ Bot init warning: {e}")
    bot = None

def init_user(tid, name, uname, ref=None):
    """Create or update user"""
    user = get_user(tid)
    if not user:
        return create_user(tid, name, uname, ref)
    fb_request('PATCH', f'users/{tid}', {'last_active': int(time.time()*1000), 'name': name})
    return user

# ─────────────────────────────────────────────────────────────────────
# 🌐 Flask Routes
# ─────────────────────────────────────────────────────────────────────

@app.route('/')
def root():
    """Root - Info page"""
    return '''<html><head><title>Ultimate Media Search</title><meta name="viewport" content="width=device-width,initial-scale=1"></head>
    <body style="background:#0f172a;color:#fff;text-align:center;padding:60px 20px;font-family:sans-serif">
    <h1 style="font-size:2rem;margin-bottom:20px">🤖 Ultimate Media Search Bot</h1>
    <p style="color:#94a3b8;margin-bottom:30px">Earn money by watching ads & completing simple tasks!</p>
    <a href="https://t.me/UltimateMediaSearchBot" style="display:inline-block;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;padding:14px 32px;border-radius:12px;text-decoration:none;font-weight:600">🚀 Open on Telegram</a>
    </body></html>'''

@app.route('/dashboard')
def dashboard():
    """Premium User Dashboard (TWA)"""
    tid = request.args.get('id')
    name = request.args.get('name', 'User')
    
    if not tid:
        return '<html><body style="background:#0f172a;color:#fff;text-align:center;padding:40px"><h2>⚠️ Open from Telegram bot with /start</h2></body></html>'
    
    # Initialize user
    try:
        init_user(int(tid), name, name)
    except:
        pass
    
    return render_template_string(
        DASHBOARD_HTML,
        firebase_config=json.dumps(FIREBASE_CONFIG),
        app_config=json.dumps(APP_CONFIG),
        banner=APP_CONFIG['BANNER'],
        youtube=APP_CONFIG['YOUTUBE'],
        instagram=APP_CONFIG['INSTAGRAM'],
        facebook=APP_CONFIG['FACEBOOK']
    )

@app.route('/admin')
def admin_panel():
    """Admin Panel"""
    admin_key = request.args.get('key', '')
    return render_template_string(
        ADMIN_HTML,
        firebase_config=json.dumps(FIREBASE_CONFIG),
        admin_key=admin_key
    )

@app.route('/favicon.ico')
@app.route('/favicon.png')
def favicon():
    """Handle favicon - return 204 No Content"""
    return '', 204

@app.route('/webhook', methods=['POST'])
def webhook():
    """Telegram Webhook Handler"""
    if not bot:
        return 'Bot unavailable', 503
    try:
        update = request.get_json(force=True)
        if update:
            bot.process_new_updates([types.Update.de_json(update)])
        return '', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/<tid>', methods=['GET'])
def api_get_user(tid):
    """API: Get user data"""
    user = get_user(tid)
    if user:
        user['balance_usd'] = (user.get('points', 0) or 0) / APP_CONFIG['POINTS_PER_DOLLAR']
        return jsonify({'success': True, 'data': user})
    return jsonify({'success': False, 'error': 'User not found'}), 404

@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'ultimate-media-search-2026',
        'timestamp': int(time.time() * 1000),
        'firebase_region': 'asia-southeast1'
    }), 200

# ─────────────────────────────────────────────────────────────────────
# 🤖 Bot Handlers
# ─────────────────────────────────────────────────────────────────────

if bot:
    @bot.message_handler(commands=['start'])
    def handle_start(msg):
        try:
            uid = msg.from_user.id
            name = msg.from_user.first_name or 'User'
            uname = msg.from_user.username or ''
            
            # Parse referral
            ref = None
            if msg.text and '/start ' in msg.text:
                parts = msg.text.split()
                if len(parts) > 1:
                    ref = parts[1].strip()
            
            user = init_user(uid, name, uname, ref)
            
            caption = f"""
🌟 <b>Welcome {name}!</b>

💬 <i>"Your smartphone is now your ATM!"</i> 💰

🎁 <b>How to Earn:</b>
├ 📺 Watch Ads → +{APP_CONFIG['AD_POINTS']} Points
├ 📱 Social Tasks → +{APP_CONFIG['SOCIAL_POINTS']} Points
├ 👥 Refer Friends → +{APP_CONFIG['REFERRAL_BONUS']} Points
└ 💰 <b>{APP_CONFIG['POINTS_PER_DOLLAR']} Points = $1.00</b>

👇 Open your Premium Dashboard!
            """
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            dashboard_url = f"/dashboard?id={uid}&name={name}"
            
            markup.add(
                types.InlineKeyboardButton("🚀 Open Dashboard", url=dashboard_url),
                types.InlineKeyboardButton("👥 Invite Friends", callback_data=f"invite:{uid}")
            )
            
            try:
                bot.send_photo(msg.chat.id, photo=APP_CONFIG['BANNER'], caption=caption, reply_markup=markup)
            except:
                bot.send_message(msg.chat.id, caption, reply_markup=markup)
                
        except Exception as e:
            logger.error(f"Start error: {e}")
            bot.send_message(msg.chat.id, "⚠️ Error. Try /start again.")

    @bot.callback_query_handler(func=lambda c: c.data.startswith('invite:'))
    def handle_invite(call):
        try:
            uid = int(call.data.split(':')[1])
            if call.from_user.id != uid:
                bot.answer_callback_query(call.id, "Unauthorized", show_alert=True)
                return
            
            user = get_user(uid)
            rc = user.get('referral_code', '') if user else ''
            rl = f"https://t.me/UltimateMediaSearchBot?start={rc}"
            
            text = f"""
👥 <b>Invite & Earn!</b>

🎁 +{APP_CONFIG['REFERRAL_BONUS']} Points per friend!

🔗 Your Link:
<code>{rl}</code>
            """
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📋 Copy Link", switch_inline_query=rl))
            
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"Invite error: {e}")
            bot.answer_callback_query(call.id, "Error", show_alert=True)

# ─────────────────────────────────────────────────────────────────────
# 🔧 Error Handlers & Webhook Setup
# ─────────────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found', 'available': ['/dashboard', '/webhook', '/health', '/admin']}), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

# Auto-set webhook on first request
WEBHOOK_SET = False

@app.before_request
def set_webhook_once():
    global WEBHOOK_SET
    if not WEBHOOK_SET and bot and request.path == '/webhook':
        try:
            host = request.host_url.rstrip('/')
            webhook_url = f"{host}/webhook"
            bot.set_webhook(webhook_url)
            logger.info(f"✅ Webhook set: {webhook_url}")
        except Exception as e:
            logger.error(f"Set webhook error: {e}")
        WEBHOOK_SET = True

logger.info("✅ Serverless function ready for Vercel!")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🚀 Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
