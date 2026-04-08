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
# Aapki Dashboard Image
PHOTO_URL = "https://i.ibb.co/3ykYmS7/user-photo.jpg" 

bot = Bot(token=TOKEN)

def init_firebase():
    if not firebase_admin._apps:
        fb_json = os.getenv("FIREBASE_CONFIG_JSON")
        if fb_json:
            try:
                cred = credentials.Certificate(json.loads(fb_json))
                firebase_admin.initialize_app(cred, {"databaseURL": FB_URL})
                return True
            except: return False
    return True

# --- KEYBOARDS ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📊 My Dashboard", callback_data='dashboard')],
        [InlineKeyboardButton("📺 Watch Ads & Earn", url="https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b")],
        [InlineKeyboardButton("💰 Withdraw", callback_data='withdraw')],
        [InlineKeyboardButton("📱 Social Media", callback_data='social')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_handler(update: Update):
    init_firebase()
    user = update.effective_user
    user_id = str(user.id)
    
    # Save User to Firebase
    ref = db.reference(f"users/{user_id}")
    if not ref.get():
        ref.set({"name": user.full_name, "balance": 74.50, "tasks": 1245}) # Sample data as per your image

    caption = (f"👋 *Welcome back, {user.first_name}!*\n\n"
               "🚀 Aapka Ad-Earning Dashboard taiyar hai.\n"
               "Niche diye buttons se apni earning check karein.")
    
    await bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=PHOTO_URL,
        caption=caption,
        parse_mode='Markdown',
        reply_markup=get_main_menu()
    )

async def cb_handler(update: Update):
    init_firebase()
    query = update.callback_query
    user_id = str(query.from_user.id)
    await query.answer()

    if query.data == 'dashboard':
        user_data = db.reference(f"users/{user_id}").get() or {}
        bal = user_data.get('balance', 0.0)
        tsk = user_data.get('tasks', 0)
        
        # Dashboard UI look
        text = (f"🖥 *YOUR AD-EARNING DASHBOARD*\n\n"
                f"👤 *User:* {query.from_user.first_name}\n"
                f"💰 *Available Balance:* `${bal}`\n"
                f"✅ *Ads Viewed:* `{tsk} / 2,000`\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Daily Ad Stream: *COMPLETED*")
        await query.edit_message_caption(caption=text, parse_mode='Markdown', reply_markup=get_main_menu())

    elif query.data == 'social':
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📺 YouTube", url="https://www.youtube.com/@USSoccerPulse")],
            [InlineKeyboardButton("📸 Instagram", url="https://www.instagram.com/digital_rockstar_m")],
            [InlineKeyboardButton("🔙 Back", callback_data='back')]
        ])
        await query.edit_message_caption(caption="🔗 *Our Social Media Links:*", parse_mode='Markdown', reply_markup=kb)

    elif query.data == 'back':
        await query.edit_message_caption(caption="Main Menu mein aapka swagat hai:", reply_markup=get_main_menu())

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    if update.message and update.message.text == "/start":
        loop.run_until_complete(start_handler(update))
    elif update.callback_query:
        loop.run_until_complete(cb_handler(update))
    loop.close()
    return "ok", 200

@app.route("/")
def index():
    return "Bot is Running!"
