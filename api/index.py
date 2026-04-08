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
# Aapki Dashboard wali photo ka link
DASHBOARD_IMG = "https://i.ibb.co/3ykYmS7/user-photo.jpg" 

bot = Bot(token=TOKEN)

def init_firebase():
    if not firebase_admin._apps:
        fb_json = os.getenv("FIREBASE_CONFIG_JSON")
        if fb_json:
            try:
                cred = credentials.Certificate(json.loads(fb_json))
                firebase_admin.initialize_app(cred, {"databaseURL": FB_URL})
            except: pass

# --- DASHBOARD KEYBOARD ---
def main_menu():
    # Dhyan dein: yahan hum 'url' nahi 'callback_data' use kar rahe hain
    # Isse "Not Found" wala page nahi khulega, bot chat mein hi reply dega
    keyboard = [
        [InlineKeyboardButton("📊 View My Dashboard", callback_data='show_db')],
        [InlineKeyboardButton("📺 Watch Ads & Earn", url="https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b")],
        [InlineKeyboardButton("💰 Request Payout", callback_data='payout')],
        [InlineKeyboardButton("📱 Social Links", callback_data='socials')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def process_update(update: Update):
    init_firebase()
    
    # 1. Jab koi /start dabaye
    if update.message and update.message.text == "/start":
        user = update.effective_user
        # User ko Firebase mein check/save karein
        ref = db.reference(f"users/{user.id}")
        if not ref.get():
            ref.set({"name": user.full_name, "balance": 74.50, "tasks": 1245})

        await bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=DASHBOARD_IMG,
            caption=f"👋 *Welcome back, {user.first_name}!*\n\nAapka earning panel niche taiyar hai.",
            parse_mode='Markdown',
            reply_markup=main_menu()
        )

    # 2. Jab koi Button dabaye (Dashboard/Social)
    elif update.callback_query:
        query = update.callback_query
        user_id = query.from_user.id
        await query.answer() # Button ki loading hatane ke liye

        if query.data == 'show_db':
            data = db.reference(f"users/{user_id}").get() or {}
            bal = data.get('balance', 0.0)
            tsk = data.get('tasks', 0)
            
            # Chat ke andar hi text update hoga
            dashboard_text = (
                f"🖥 *OFFICIAL DASHBOARD*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 *User:* {query.from_user.first_name}\n"
                f"💰 *Balance:* `${bal}`\n"
                f"✅ *Ads Viewed:* `{tsk} / 2,000`\n"
                f"📈 *Status:* `Active`"
            )
            await query.edit_message_caption(caption=dashboard_text, parse_mode='Markdown', reply_markup=main_menu())

        elif query.data == 'socials':
            social_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("YouTube", url="https://www.youtube.com/@USSoccerPulse")],
                [InlineKeyboardButton("🔙 Back to Dashboard", callback_data='back_home')]
            ])
            await query.edit_message_caption(caption="🔗 *Follow our official links:*", reply_markup=social_kb)
        
        elif query.data == 'back_home':
            await query.edit_message_caption(caption="Main Menu:", reply_markup=main_menu())

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    # Async loop handle karne ke liye
    asyncio.run(process_update(update))
    return "ok", 200

@app.route("/")
def home():
    return "Bot is Active!", 200
