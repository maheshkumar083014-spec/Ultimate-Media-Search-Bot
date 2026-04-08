import os
import json
import asyncio
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup

app = Flask(__name__)

# --- CONFIGURATION ---
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
FB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"
# Aapka Dashboard Image (Jo welcome aur dashboard dono mein dikhegi)
DASHBOARD_IMG = "https://i.ibb.co/3ykYmS7/user-photo.jpg" 

bot = Bot(token=TOKEN)

# Firebase Initialize Function
def init_fb():
    if not firebase_admin._apps:
        fb_json = os.getenv("FIREBASE_CONFIG_JSON")
        if fb_json:
            try:
                cred = credentials.Certificate(json.loads(fb_json))
                firebase_admin.initialize_app(cred, {"databaseURL": FB_URL})
            except Exception as e:
                print(f"Firebase Init Error: {e}")

# --- KEYBOARDS ---
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 My Dashboard", callback_data='db_view')],
        [InlineKeyboardButton("📺 Watch Ads & Earn", url="https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b")],
        [InlineKeyboardButton("💰 Request Payout", callback_data='withdraw_req')],
        [InlineKeyboardButton("📱 Social Channels", callback_data='social_links')]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- BOT LOGIC ---
async def handle_update(update: Update):
    init_fb()
    
    # 1. Start Command
    if update.message and update.message.text == "/start":
        user = update.effective_user
        user_ref = db.reference(f"users/{user.id}")
        
        # New user setup
        if not user_ref.get():
            user_ref.set({
                "username": user.first_name,
                "balance": 0.00,
                "tasks": 0,
                "status": "Active"
            })

        welcome_text = (
            f"🔥 *Welcome back, {user.first_name}!*\n\n"
            f"Aapka Ad-Earning Dashboard taiyar hai.\n"
            f"Niche diye buttons se earning shuru karein!"
        )
        
        await bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=DASHBOARD_IMG,
            caption=welcome_text,
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard()
        )

    # 2. Button Clicks (Callback Queries)
    elif update.callback_query:
        query = update.callback_query
        user_id = query.from_user.id
        await query.answer()

        if query.data == 'db_view':
            data = db.reference(f"users/{user_id}").get() or {}
            bal = data.get('balance', 0.0)
            tsk = data.get('tasks', 0)
            
            db_text = (
                f"🖥 *AD-EARNING DASHBOARD*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 *User:* {query.from_user.first_name}\n"
                f"💰 *Available Balance:* `${bal}`\n"
                f"✅ *Ads Viewed:* `{tsk} / 2,000`\n"
                f"📊 *Daily Status:* `COMPLETED`\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            await query.edit_message_caption(caption=db_text, parse_mode='Markdown', reply_markup=main_menu_keyboard())

        elif query.data == 'social_links':
            social_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("YouTube", url="https://www.youtube.com/@USSoccerPulse")],
                [InlineKeyboardButton("Instagram", url="https://www.instagram.com/digital_rockstar_m")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data='home')]
            ])
            await query.edit_message_caption(caption="📱 *Connect with our Social Media:*", parse_mode='Markdown', reply_markup=social_kb)

        elif query.data == 'home':
            await query.edit_message_caption(caption="🔥 *Main Menu:*", reply_markup=main_menu_keyboard())

# --- FLASK ROUTES ---
@app.route("/webhook", methods=["POST"])
def webhook():
    if request.method == "POST":
        data = request.get_json(force=True)
        update = Update.de_json(data, bot)
        # Async run
        asyncio.run(handle_update(update))
        return "ok", 200

@app.route("/")
def index():
    return "<h1>Bot is Online and Secure!</h1>", 200

# Vercel requirements
def handler(event, context):
    return app(event, context)
