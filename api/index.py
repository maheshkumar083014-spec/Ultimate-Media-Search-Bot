import os
import json
import telebot
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db

# 1. Config
TOKEN = "8701635891:AAFmgU89KRhd2dhE-PqRY-mBmGy_SxQEGOg"
DB_URL = os.environ.get('FIREBASE_DB_URL')
SERVICE_ACCOUNT_JSON = os.environ.get('FIREBASE_SERVICE_ACCOUNT')

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# 2. Firebase Connect
if not firebase_admin._apps:
    try:
        if SERVICE_ACCOUNT_JSON:
            info = json.loads(SERVICE_ACCOUNT_JSON)
            cred = credentials.Certificate(info)
            firebase_admin.initialize_app(cred, {'databaseURL': DB_URL})
            print("✅ Firebase Connected")
    except Exception as e:
        print(f"❌ Firebase Error: {e}")

# 3. Bot Handlers
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    try:
        if not firebase_admin._apps:
            bot.send_message(message.chat.id, "❌ Firebase setup is incomplete in Vercel.")
            return

        user_ref = db.reference(f'users/{user_id}').get()
        if not user_ref:
            db.reference(f'users/{user_id}').set({
                "username": message.from_user.username or "User",
                "points": 0,
                "status": "free"
            })
        
        bot.send_message(message.chat.id, "✅ Connection Success! Aapka bot kaam kar raha hai.")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Debug Error: {str(e)}")

# 4. Webhook
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route('/')
def index():
    return "<h1>Bot Status: ONLINE ✅</h1>"
