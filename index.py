import os
import time
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

# ================= CRITICAL DATA =================
TELEGRAM_BOT_TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
FIREBASE_DB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"
DEEPSEEK_API_KEY = "sk-783d645ce9e84eb8b954786a016561ea"
UPI_ID = "8543083014@ikwik"
WELCOME_IMAGE = "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg"
# =================================================

# Firebase REST Helper (Lightweight & Vercel-Safe)
def fb_get(path):
    return requests.get(f"{FIREBASE_DB_URL}/{path}.json").json()
def fb_set(path, data):
    return requests.post(f"{FIREBASE_DB_URL}/{path}.json", json=data).json()
def fb_update(path, data):
    return requests.patch(f"{FIREBASE_DB_URL}/{path}.json", json=data).json()

# ================= WEB ROUTES =================
@app.route('/')
def dashboard():
    return send_from_directory('.', 'dashboard.html')

@app.route('/admin')
def admin_panel():
    return send_from_directory('.', 'admin.html')

@app.route('/api/chat', methods=['POST'])
def ai_chat():
    data = request.json
    messages = data.get('messages', [])
    if not messages:
        return jsonify({"error": "No messages provided"}), 400
        
    messages.insert(0, {"role": "system", "content": "You are Ultimate Media Search AI. Assist users with tasks, earning, promotion, and platform rules."})
    try:
        res = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": messages, "max_tokens": 500}
        )
        return jsonify(res.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/payment', methods=['POST'])
def handle_payment():
    data = request.json
    uid = data.get('uid')
    action = data.get('action')
    
    if not uid:
        return jsonify({"error": "User ID required"}), 400

    if action == 'approve':
        current = fb_get(f"users/{uid}")
        fb_update(f"users/{uid}", {
            "payment_status": "approved",
            "plan": "pro",
            "multiplier": 2,
            "points": (current.get("points", 0) or 0) + 500
        })
    elif action == 'reject':
        fb_update(f"users/{uid}", {"payment_status": "rejected", "plan": "free", "multiplier": 1})
    elif action == 'update_points':
        current = fb_get(f"users/{uid}")
        fb_update(f"users/{uid}", {"points": (current.get("points", 0) or 0) + int(data.get("points", 0))})
        
    return jsonify({"success": True, "message": f"User {uid} {action}d successfully"})

# NOTE: Vercel auto-detects 'app'. Do NOT use app.run() or bot.polling() here.
# Run Telegram bot separately on Replit/Railway using the same DB & Token.
