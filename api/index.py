import os
import json
import telebot
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db

# --- 1. Configuration ---
# Aapka provide kiya gaya token
TOKEN = "8701635891:AAFmgU89KRhd2dhE-PqRY-mBmGy_SxQEGOg"
DB_URL = os.environ.get('FIREBASE_DB_URL')
SERVICE_ACCOUNT_JSON = os.environ.get('FIREBASE_SERVICE_ACCOUNT')

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# --- 2. Firebase Connection ---
if not firebase_admin._apps:
    try:
        if SERVICE_ACCOUNT_JSON:
            info = json.loads(SERVICE_ACCOUNT_JSON)
            cred = credentials.Certificate(info)
            firebase_admin.initialize_app(cred, {'databaseURL': DB_URL})
            print("✅ Firebase Connected!")
    except Exception as e:
        print(f"❌ Firebase Error: {e}")

# --- 3. Bot Logic ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    try:
        user_ref = db.reference(f'users/{user_id}').get()
        if not user_ref:
            db.reference(f'users/{user_id}').set({
                "username": message.from_user.username or "User",
                "points": 0,
                "status": "free"
            })
        
        welcome_text = "✨ *Welcome to Ultimate Media Search Bot V3*\nAapka account sync ho gaya hai."
        bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, "System error. Please try again later.")

# --- 4. Webhook Route ---
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200
    return "Forbidden", 403

@app.route('/')
def index():
    return "<h1>Bot Status: ONLINE ✅</h1><p>Webhook is active.</p>"
