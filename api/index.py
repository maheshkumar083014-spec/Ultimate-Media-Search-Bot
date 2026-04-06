import os
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

app = Flask(__name__)

# --- 1. Firebase Initialization ---
if not firebase_admin._apps:
    # Environment Variables se data uthana
    raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "")
    private_key = raw_key.replace('\\n', '\n') # Slash-n fix
    
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

# --- 2. Telegram Bot Setup ---
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

# Start Command Logic
def start(update, context):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # User ko Database mein save karna
    try:
        user_ref = db.reference(f'users/{chat_id}')
        user_ref.set({
            "first_name": user.first_name,
            "username": user.username,
            "status": "active"
        })
        update.message.reply_text(f"Assalam-o-Alaikum {user.first_name}!\n\nBot aur Database dono connect ho chuke hain. Aap ab movies ya media search kar sakte hain.")
    except Exception as e:
        update.message.reply_text("Bot active hai lekin Database connect nahi ho saka. Key check karein.")

# Webhook Route
@app.route('/api/index', methods=['POST'])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        
        # Dispatcher setup (Version 13.15 style)
        dispatcher = Dispatcher(bot, None, workers=0)
        dispatcher.add_handler(CommandHandler("start", start))
        
        dispatcher.process_update(update)
        return "ok"
    return "done"

@app.route('/')
def index():
    return "Bot is running perfectly on Vercel!"
