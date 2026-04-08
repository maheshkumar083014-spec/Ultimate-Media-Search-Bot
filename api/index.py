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
PHOTO_URL = "https://i.ibb.co/3ykYmS7/user-photo.jpg"

bot = Bot(token=TOKEN)

# Firebase Initialize
def init_fb():
    if not firebase_admin._apps:
        fb_json = os.getenv("FIREBASE_CONFIG_JSON")
        if fb_json:
            cred = credentials.Certificate(json.loads(fb_json))
            firebase_admin.initialize_app(cred, {"databaseURL": FB_URL})

# Main Keyboard
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 My Dashboard", callback_data='db')],
        [InlineKeyboardButton("📺 Watch Ads & Earn", url="https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b")],
        [InlineKeyboardButton("💰 Withdraw", callback_data='wd')],
        [InlineKeyboardButton("📱 Social Media", callback_data='sm')]
    ])

async def handle_update(update: Update):
    init_fb()
    if update.message and update.message.text == "/start":
        user = update.effective_user
        ref = db.reference(f"users/{user.id}")
        if not ref.get():
            ref.set({"name": user.full_name, "balance": 0.0, "tasks": 0})
        
        await bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=PHOTO_URL,
            caption=f"🔥 *Welcome {user.first_name}!*\nStart earning by watching ads.",
            parse_mode='Markdown',
            reply_markup=main_menu()
        )
    
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        if query.data == 'db':
            data = db.reference(f"users/{user_id}").get() or {}
            txt = f"📝 *DASHBOARD*\n\n💰 Balance: ${data.get('balance', 0)}\n✅ Tasks: {data.get('tasks', 0)}"
            await query.edit_message_caption(caption=txt, parse_mode='Markdown', reply_markup=main_menu())
        
        elif query.data == 'sm':
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("YouTube", url="https://www.youtube.com/@USSoccerPulse")], [InlineKeyboardButton("Back", callback_data='home')]])
            await query.edit_message_caption(caption="🔗 Social Media Links:", reply_markup=kb)
        
        elif query.data == 'home':
            await query.edit_message_caption(caption="Main Menu:", reply_markup=main_menu())

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    asyncio.run(handle_update(update))
    return "ok", 200

@app.route("/")
def index():
    return "Bot is Live!"
