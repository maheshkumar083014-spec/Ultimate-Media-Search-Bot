import os
import json
import asyncio
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup

app = Flask(__name__)
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
FB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"
DASHBOARD_IMG = "https://i.ibb.co/3ykYmS7/user-photo.jpg" 

bot = Bot(token=TOKEN)

def init_fb():
    if not firebase_admin._apps:
        try:
            fb_json = os.getenv("FIREBASE_CONFIG_JSON")
            if fb_json:
                cred = credentials.Certificate(json.loads(fb_json))
                firebase_admin.initialize_app(cred, {"databaseURL": FB_URL})
                return True
        except: pass
    return False

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    asyncio.run(handle_logic(update))
    return "ok", 200

async def handle_logic(update):
    init_fb()
    if update.message and update.message.text == "/start":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("📊 Dashboard", callback_data='db')]])
        await bot.send_photo(chat_id=update.effective_chat.id, photo=DASHBOARD_IMG, caption="Bot Active!", reply_markup=kb)

@app.route("/")
def index():
    return "Bot is Live!", 200
