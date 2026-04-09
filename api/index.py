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
                cred_dict = json.loads(fb_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {"databaseURL": FB_URL})
                return True
        except Exception as e:
            print(f"Firebase Init Error: {e}")
    return False

def get_main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 My Dashboard", callback_data='db')],
        [InlineKeyboardButton("📺 Watch Ads", url="https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b")],
        [InlineKeyboardButton("📱 Support", callback_data='help')]
    ])

async def handle_logic(update: Update):
    # Safe Firebase Init
    fb_connected = init_fb()
    
    if update.message and update.message.text == "/start":
        user = update.effective_user
        welcome_msg = f"🔥 *Welcome {user.first_name}!*\n\nBot is now online. Click below to view your earnings."
        
        # Try to save user if FB is connected
        if fb_connected:
            try:
                db.reference(f"users/{user.id}").update({"name": user.first_name})
            except: pass

        await bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=DASHBOARD_IMG,
            caption=welcome_msg,
            parse_mode='Markdown',
            reply_markup=get_main_kb()
        )

    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == 'db':
            # Default values if FB fails
            bal, tsk = "0.00", "0"
            if fb_connected:
                data = db.reference(f"users/{query.from_user.id}").get() or {}
                bal = data.get('balance', "0.00")
                tsk = data.get('tasks', "0")
            
            await query.edit_message_caption(
                caption=f"🖥 *DASHBOARD*\n💰 Balance: `${bal}`\n✅ Ads: `{tsk}`",
                parse_mode='Markdown',
                reply_markup=get_main_kb()
            )

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, bot)
        asyncio.run(handle_logic(update))
    except Exception as e:
        print(f"Webhook Error: {e}")
    return "ok", 200

@app.route("/")
def index():
    return "Bot is Live and Active!", 200
