from flask import Flask, request, jsonify, render_template
import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, db
import os
import requests
from datetime import datetime

app = Flask(__name__)

# Initialize Telegram Bot
BOT_TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# Initialize Firebase Admin
cred = credentials.Certificate({
    "type": "service_account",
    "project_id": "ultimatemediasearch",
    "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID", "dummy"),
    "private_key": os.environ.get("FIREBASE_PRIVATE_KEY", "-----BEGIN PRIVATE KEY-----\ndummy\n-----END PRIVATE KEY-----\n"),
    "client_email": "firebase-adminsdk@ultimatemediasearch.iam.gserviceaccount.com",
    "client_id": os.environ.get("FIREBASE_CLIENT_ID", "dummy"),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk%40ultimatemediasearch.iam.gserviceaccount.com"
})

firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

# Routes
@app.route('/')
def home():
    return "Ultimate Media Search Bot API is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return jsonify({"status": "ok"}), 200

@app.route('/set-webhook', methods=['GET'])
def set_webhook():
    webhook_url = request.host_url.rstrip('/') + '/webhook'
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return jsonify({"status": "webhook set", "url": webhook_url})

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# Telegram Bot Commands
@bot.message_handler(commands=['start'])
def send_welcome(message):
    uid = message.from_user.id
    name = message.from_user.first_name
    username = message.from_user.username or ""
    
    # Initialize user in Firebase if not exists
    user_ref = db.reference(f'users/{uid}')
    user_data = user_ref.get()
    
    if not user_data:
        user_ref.set({
            'uid': uid,
            'name': name,
            'username': username,
            'points': 0,
            'earnings': 0.0,
            'ads_watched_today': 0,
            'last_ad_date': '',
            'social_tasks': {
                'youtube': False,
                'instagram': False,
                'facebook': False
            },
            'joined_at': datetime.now().isoformat(),
            'total_earned': 0.0
        })
    
    # Create inline keyboard
    markup = types.InlineKeyboardMarkup(row_width=1)
    dashboard_url = f"https://ultimate-media-search-bot-t7kj.vercel.app/dashboard?id={uid}&name={name}"
    btn = types.InlineKeyboardButton("🎯 Open Dashboard", url=dashboard_url)
    markup.add(btn)
    
    welcome_text = f"""👋 *Good Morning, {name}!*

Welcome to *Ultimate Media Search Bot*!

💰 *Earn Money by:*
• Watching Ads (+25 Points)
• Social Tasks (+100 Points)

💵 *Withdrawal:* 100 Points = $1.00

Click below to start earning!"""
    
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(commands=['balance'])
def check_balance(message):
    uid = message.from_user.id
    user_ref = db.reference(f'users/{uid}')
    user_data = user_ref.get()
    
    if user_data:
        points = user_data.get('points', 0)
        earnings = points / 100.0
        text = f"""💰 *Your Balance:*

📊 Points: {points}
💵 Earnings: ${earnings:.2f}

💡 100 Points = $1.00"""
        bot.send_message(message.chat.id, text, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "User not found. Please /start first.")

# Error handler
@bot.error_handler(Exception)
def error_handler(error):
    print(f"Error: {error}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
