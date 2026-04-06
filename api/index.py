import os
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request
from telegram import Update, Bot

app = Flask(__name__)

# --- Firebase Setup ---
if not firebase_admin._apps:
    try:
        raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "")
        private_key = raw_key.replace('\\n', '\n')
        
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
        print(f"Firebase Init Error: {e}")

# --- Bot Setup ---
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

@app.route('/api/index', methods=['POST'])
def webhook():
    if request.method == "POST":
        try:
            json_string = request.get_json(force=True)
            update = Update.de_json(json_string, bot)
            
            if update.message and update.message.text:
                text = update.message.text
                chat_id = update.message.chat_id
                user_name = update.message.from_user.first_name

                if text == "/start":
                    # Database Entry
                    db.reference(f'users/{chat_id}').set({"name": user_name})
                    bot.send_message(chat_id=chat_id, text=f"Mubarak ho {user_name}! Bot setup mukammal ho gaya hai.")
                else:
                    bot.send_message(chat_id=chat_id, text="Aapka message mil gaya!")
                    
            return "ok", 200
        except Exception as e:
            print(f"Error: {e}")
            return "error", 500
    return "done", 200

@app.route('/')
def index():
    return "Bot is live!"
