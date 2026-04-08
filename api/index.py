import os
import json
import asyncio
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup

# Flask app initialize
app = Flask(__name__)

# --- CONFIG ---
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
FB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"
DASHBOARD_IMG = "https://i.ibb.co/3ykYmS7/user-photo.jpg" 

bot = Bot(token=TOKEN)

# Firebase Init
def init_fb():
    if not firebase_admin._apps:
        fb_json = os.getenv("FIREBASE_CONFIG_JSON")
        if fb_json:
            try:
                cred = credentials.Certificate(json.loads(fb_json))
                firebase_admin.initialize_app(cred, {"databaseURL": FB_URL})
            except Exception as e:
                print(f"Firebase Error: {e}")

# Main Keyboard
def get_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 My Dashboard", callback_data='db')],
        [InlineKeyboardButton("📺 Watch Ads", url="https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b")],
        [InlineKeyboardButton("💰 Withdraw", callback_data='wd')],
        [InlineKeyboardButton("📱 Social Media", callback_data='sm')]
    ])

# Handle Logic
async def handle_logic(update: Update):
    init_fb()
    
    if update.message and update.message.text == "/start":
        user = update.effective_user
        # Firebase entry
        try:
            ref = db.reference(f"users/{user.id}")
            if not ref.get():
                ref.set({"name": user.full_name, "balance": 74.50, "tasks": 1245})
        except: pass

        await bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=DASHBOARD_IMG,
            caption=f"🔥 *Welcome back, {user.first_name}!*\n\nAapka earning panel niche taiyar hai.",
            parse_mode='Markdown',
            reply_markup=get_keyboard()
        )

    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        
        if query.data == 'db':
            # Balance fetch
            try:
                data = db.reference(f"users/{query.from_user.id}").get() or {}
                bal = data.get('balance', 0.0)
                tsk = data.get('tasks', 0)
            except:
                bal, tsk = "Error", "Error"

            text = (f"🖥 *OFFICIAL DASHBOARD*\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"💰 *Balance:* `${bal}`\n"
                    f"✅ *Ads Viewed:* `{tsk} / 2,000`\n"
                    f"📈 *Status:* `Active`")
            await query.edit_message_caption(caption=text, parse_mode='Markdown', reply_markup=get_keyboard())

        elif query.data == 'sm':
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("YouTube", url="https://www.youtube.com/@USSoccerPulse")], [InlineKeyboardButton("🔙 Back", callback_data='home')]])
            await query.edit_message_caption(caption="🔗 Social Media Links:", reply_markup=kb)

        elif query.data == 'home':
            await query.edit_message_caption(caption="Main Menu:", reply_markup=get_keyboard())

# Flask Route
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, bot)
        # Use existing loop or create new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(handle_logic(update))
        loop.close()
        return "ok", 200
    except Exception as e:
        print(f"Critical Error: {e}")
        return "error", 500

@app.route("/")
def index():
    return "Bot is Active!", 200
