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
# Dashboard Image Link
DASHBOARD_IMG = "https://i.ibb.co/3ykYmS7/user-photo.jpg" 

bot = Bot(token=TOKEN)

# Firebase Setup
def init_firebase():
    if not firebase_admin._apps:
        fb_json = os.getenv("FIREBASE_CONFIG_JSON")
        if fb_json:
            try:
                cred = credentials.Certificate(json.loads(fb_json))
                firebase_admin.initialize_app(cred, {"databaseURL": FB_URL})
            except: pass

# Keyboard UI
def main_menu():
    keyboard = [
        [InlineKeyboardButton("📊 My Dashboard", callback_data='db')],
        [InlineKeyboardButton("📺 Watch Ads & Earn", url="https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b")],
        [InlineKeyboardButton("💰 Withdraw", callback_data='wd')],
        [InlineKeyboardButton("📱 Social Media", callback_data='sm')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def handle_update(update: Update):
    init_firebase()
    
    # 1. Start Command
    if update.message and update.message.text == "/start":
        user = update.effective_user
        ref = db.reference(f"users/{user.id}")
        if not ref.get():
            # Initial Data
            ref.set({"name": user.first_name, "balance": 0.00, "tasks": 0})
        
        await bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=DASHBOARD_IMG,
            caption=f"👋 *Welcome back, {user.first_name}!*\n\nAapka Ad-Earning Dashboard taiyar hai.\nNiche diye buttons se earning shuru karein!",
            parse_mode='Markdown',
            reply_markup=main_menu()
        )

    # 2. Button Clicks
    elif update.callback_query:
        query = update.callback_query
        user_id = query.from_user.id
        await query.answer()

        if query.data == 'db':
            data = db.reference(f"users/{user_id}").get() or {}
            bal = data.get('balance', 0.0)
            tsk = data.get('tasks', 0)
            
            txt = (f"🖥 *YOUR AD-EARNING DASHBOARD*\n"
                   f"━━━━━━━━━━━━━━━━━━━━\n"
                   f"👤 *User:* {query.from_user.first_name}\n"
                   f"💰 *Available Balance:* `${bal}`\n"
                   f"✅ *Ads Viewed:* `{tsk} / 2,000`\n"
                   f"━━━━━━━━━━━━━━━━━━━━\n"
                   f"Daily Ad Stream: *COMPLETED*")
            await query.edit_message_caption(caption=txt, parse_mode='Markdown', reply_markup=main_menu())

        elif query.data == 'sm':
            social_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("YouTube", url="https://www.youtube.com/@USSoccerPulse")],
                [InlineKeyboardButton("Instagram", url="https://www.instagram.com/digital_rockstar_m")],
                [InlineKeyboardButton("🔙 Back", callback_data='home')]
            ])
            await query.edit_message_caption(caption="🔗 *Our Social Media Links:*", parse_mode='Markdown', reply_markup=social_kb)
        
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
    return "Bot is Live!", 200
