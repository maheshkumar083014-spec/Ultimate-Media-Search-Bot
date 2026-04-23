import os
import json
import threading
import requests
import telebot
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

# ================= CRITICAL DATA =================
TELEGRAM_BOT_TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
FIREBASE_DB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"
DEEPSEEK_API_KEY = "sk-783d645ce9e84eb8b954786a016561ea"
UPI_ID = "8543083014@ikwik"
WELCOME_IMAGE = "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg"
# =================================================

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def get_fb_ref(path):
    return f"{FIREBASE_DB_URL}/{path}.json"

def fetch_fb(path):
    return requests.get(get_fb_ref(path)).json()

def write_fb(path, data):
    return requests.post(get_fb_ref(path), json=data).json()

def update_fb(path, data):
    return requests.patch(get_fb_ref(path), json=data).json()

# Telegram Bot Logic
@bot.message_handler(commands=['start'])
def send_welcome(message):
    uid = str(message.from_user.id)
    username = message.from_user.first_name
    db_ref = f"users/{uid}"
    
    # Initialize user if new
    if fetch_fb(db_ref) is None:
        write_fb(db_ref, {"username": username, "points": 0, "plan": "free", "multiplier": 1})
        
    user_data = fetch_fb(db_ref)
    balance = user_data.get("points", 0)
    plan = user_data.get("plan", "free")
    
    caption = f"👋 Welcome {username}!\n💰 Balance: {balance} pts\n📦 Plan: {plan.upper()}"
    bot.send_photo(message.chat.id, photo=WELCOME_IMAGE, caption=caption)

@bot.message_handler(func=lambda m: True)
def echo_all(message):
    bot.reply_text(message, "Use /start to refresh status or visit the web dashboard!")

def run_bot():
    bot.infinity_polling()

# Flask Routes
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
    
    if action == 'approve':
        current = fetch_fb(f"users/{uid}")
        update_fb(f"users/{uid}", {
            "payment_status": "approved",
            "plan": "pro",
            "multiplier": 2,
            "points": current.get("points", 0) + 500
        })
    elif action == 'reject':
        update_fb(f"users/{uid}", {"payment_status": "rejected", "plan": "free", "multiplier": 1})
    elif action == 'update_points':
        current = fetch_fb(f"users/{uid}")
        update_fb(f"users/{uid}", {"points": current.get("points", 0) + data.get("points", 0)})
        
    return jsonify({"success": True, "message": f"User {uid} {action}d"})

if __name__ == '__main__':
    # Run bot in background thread
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
