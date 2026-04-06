import os
import json
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request
from telegram import Update, Bot

app = Flask(__name__)

# --- Firebase Setup ---
# Aapki share ki hui JSON key yahan use hogi
service_account_info = {
    "type": "service_account",
    "project_id": "ultimatemediasearch",
    "private_key_id": "b173e6b31008c84db4211a8a29153491fd4849b2",
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
    "client_email": "firebase-adminsdk-fbsvc@ultimatemediasearch.iam.gserviceaccount.com",
    "client_id": "107810087265546309339",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/metadata/x509/firebase-adminsdk-fbsvc%40ultimatemediasearch.iam.gserviceaccount.com"
}

if not firebase_admin._apps:
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
    })

# --- Telegram Setup ---
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

@app.route('/api/index', methods=['POST'])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        chat_id = update.effective_chat.id
        
        if update.message:
            text = update.message.text
            
            if text == "/start":
                # User ka data Firebase mein save karna
                user_ref = db.reference(f'users/{chat_id}')
                user_ref.set({
                    'username': update.effective_user.username,
                    'last_seen': str(update.message.date)
                })
                bot.send_message(chat_id=chat_id, text="Welcome! Aapka data Firebase mein save ho gaya hai. Ab aap media search kar sakte hain.")
            
            else:
                # Search Logic (Sample)
                bot.send_message(chat_id=chat_id, text=f"Aapne search kiya: {text}\nMain database mein media dhoond raha hoon...")
                
        return "ok"
    return "done"

@app.route('/')
def index():
    return "Bot is active on Vercel with Firebase!"
