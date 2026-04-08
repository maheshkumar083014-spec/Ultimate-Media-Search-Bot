import os
import json
import asyncio
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup

app = Flask(__name__)

# --- CONFIG ---
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
FB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"
DASHBOARD_IMG = "https://i.ibb.co/3ykYmS7/user-photo.jpg" 

bot = Bot(token=TOKEN)

def init_fb():
    if not firebase_admin._apps:
        fb_json = os.getenv("FIREBASE_CONFIG_JSON")
        if fb_json:
            try:
                cred = credentials.Certificate(json.loads(fb_json))
                firebase_admin.initialize_app(cred, {"databaseURL": FB_URL})
            except: pass

def get_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 My Dashboard", callback_data='db')],
        [InlineKeyboardButton("📺 Watch Ads", url="https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b")],
        [InlineKeyboardButton("📱 Social Media", callback_data='sm')]
    ])

async def logic(update: Update):
    init_fb()
    if update.message and update.message.text == "/start":
        await bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=DASHBOARD_IMG,
            caption=f"👋 *Welcome!*\nAapka dashboard niche hai.",
            parse_mode='Markdown',
            reply_markup=get_kb()
        )
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == 'db':
            await query.edit_message_caption(caption="🖥 *DASHBOARD*\nBalance: $74.50", parse_mode='Markdown', reply_markup=get_kb())

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>", methods=["POST", "GET"])
def main_handler(path):
    if request.method == "POST":
        data = request.get_json(force=True)
        update = Update.de_json(data, bot)
        asyncio.run(logic(update))
        return "ok", 200
    return "Bot is Online!", 200

# Vercel entry point
def handler(event, context):
    return app(event, context)
