import os
import sys
import flask
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db
from telegram import Update, Bot

# Flask App Initialization
app = Flask(__name__)

# --- 1. Firebase Setup ---
if not firebase_admin._apps:
    try:
        # Environment variables se data nikalna
        raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "")
        private_key = raw_key.replace('\\n', '\n').strip().strip('"').strip("'")
        
        cred_dict = {
            "type": "service_account",
            "project_id": "ultimatemediasearch",
            "private_key": private_key,
            "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
        })
    except Exception as e:
        print(f"Firebase Error: {e}")

# --- 2. Telegram Bot Setup ---
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

@app.route('/api/index', methods=['POST'])
def webhook():
    if request.method == "POST":
        try:
            # Telegram se aane wala data read karna
            json_string = request.get_json(force=True)
            update = Update.de_json(json_string, bot)
            
            if update.message and update.message.text:
                text = update.message.text
                chat_id = update.message.chat_id
                user_name = update.message.from_user.first_name

                # Start Command Logic
                if text == "/start":
                    # Database mein user save karna
                    try:
                        db.reference(f'users/{chat_id}').set({
                            "name": user_name,
                            "username": update.message.from_user.username
                        })
                        bot.send_message(chat_id=chat_id, text=f"Assalam-o-Alaikum {user_name}!\n\nBot aur Database dono sahi kaam kar rahe hain. ✅")
                    except:
                        bot.send_message(chat_id=chat_id, text="Bot active hai par Database connect nahi ho saka.")
                
                # Default response
                else:
                    bot.send_message(chat_id=chat_id, text=f"Aapne kaha: {text}")
                    
            return "ok", 200
        except Exception as e:
            print(f"Webhook Error: {e}")
            return "error", 500
    return "done", 200

@app.route('/')
def index():
    return "Bot is running perfectly!"
