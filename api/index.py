import os
import json
import asyncio
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup

app = Flask(__name__)

# --- CONFIGURATIONS ---
FB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
PHOTO_URL = "https://i.ibb.co/3ykYmS7/user-photo.jpg"

# --- FIREBASE INIT ---
firebase_config_env = os.getenv("FIREBASE_CONFIG_JSON")
if firebase_config_env and not firebase_admin._apps:
    try:
        config_dict = json.loads(firebase_config_env)
        cred = credentials.Certificate(config_dict)
        firebase_admin.initialize_app(cred, {"databaseURL": FB_URL})
    except Exception as e:
        print(f"Firebase Init Error: {e}")

bot = Bot(token=TOKEN)

# --- KEYBOARDS ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📊 My Dashboard", callback_data='dashboard')],
        [InlineKeyboardButton("📺 Watch Ads & Earn", url="https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b")],
        [InlineKeyboardButton("💰 Withdraw", callback_data='withdraw')],
        [InlineKeyboardButton("📱 Social Media", callback_data='social_links')]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- ASYNC HANDLERS ---
async def start_command(update: Update):
    user = update.effective_user
    ref = db.reference(f"users/{user.id}")
    if not ref.get():
        ref.set({
            "name": user.full_name,
            "balance": 0.0,
            "tasks_completed": 0,
            "joined_at": {".sv": "timestamp"}
        })
    
    await bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=PHOTO_URL,
        caption=f"🔥 *Welcome {user.first_name}!*\n\nEarning aur Dashboard ke liye niche buttons use karein.",
        parse_mode='Markdown',
        reply_markup=get_main_menu()
    )

async def handle_callback(update: Update):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    await query.answer()

    if data == 'dashboard':
        user_data = db.reference(f"users/{user_id}").get() or {}
        balance = user_data.get('balance', 0)
        tasks = user_data.get('tasks_completed', 0)
        text = f"📝 *DASHBOARD*\n\n💰 Balance: ${balance}\n✅ Tasks: {tasks}\n📈 Status: Active"
        await query.edit_message_caption(caption=text, parse_mode='Markdown', reply_markup=get_main_menu())

    elif data == 'social_links':
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("YouTube", url="https://www.youtube.com/@USSoccerPulse")],
            [InlineKeyboardButton("Instagram", url="https://www.instagram.com/digital_rockstar_m")],
            [InlineKeyboardButton("🔙 Back", callback_data='back')]
        ])
        await query.edit_message_caption(caption="🔗 *Follow Us:*", parse_mode='Markdown', reply_markup=kb)

    elif data == 'withdraw':
        await query.edit_message_caption(caption="⚠️ *Withdrawal*\n\nMinimum $10 required.", reply_markup=get_main_menu())

    elif data == 'back':
        await query.edit_message_caption(caption="Main Menu:", reply_markup=get_main_menu())

# --- ROUTES ---
@app.route("/webhook", methods=["POST"])
def webhook():
    if request.method == "POST":
        data = request.get_json(force=True)
        update = Update.de_json(data, bot)
        
        # Async execution
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if update.message and update.message.text == "/start":
            loop.run_until_complete(start_command(update))
        elif update.callback_query:
            loop.run_until_complete(handle_callback(update))
        
        loop.close()
        return "ok", 200

@app.route("/")
def index():
    return "Bot is active with v20+"

if __name__ == "__main__":
    app.run()
