import os
import time
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup

app = Flask(__name__)

# --- 1. Firebase Configuration ---
if not firebase_admin._apps:
    try:
        raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n').strip().strip('"').strip("'")
        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": "ultimatemediasearch",
            "private_key": raw_key,
            "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
            "token_uri": "https://oauth2.googleapis.com/token",
        })
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
        })
    except Exception as e:
        print(f"Firebase Init Error: {e}")

# --- 2. Bot Settings ---
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
AD_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"
MOTIVATION = "\n\n🚀 *Mehnat rang layegi! Roz earning karo aur doston ko bulao!*"

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📺 Watch Ad & Earn (5 pts)", url=AD_LINK)],
        [InlineKeyboardButton("✅ Confirm Ad View", callback_data="confirm_ad")],
        [InlineKeyboardButton("🔗 Invite Friends (15 pts)", callback_data="invite")],
        [InlineKeyboardButton("💰 My Balance", callback_data="balance")]
    ]
    return InlineKeyboardMarkup(keyboard)

@app.route('/api/index', methods=['POST'])
def webhook():
    if request.method == "POST":
        try:
            update = Update.de_json(request.get_json(force=True), bot)
            
            # --- Handle Messages ---
            if update.message:
                chat_id = update.message.chat_id
                text = update.message.text
                user_ref = db.reference(f'users/{chat_id}')
                user_data = user_ref.get()

                # /start with Referral Logic
                if text.startswith("/start"):
                    if not user_data:
                        # Naya user banane par 10 welcome points
                        initial_points = 10
                        user_ref.set({"points": initial_points, "last_ad_time": 0, "name": update.message.from_user.first_name})
                        
                        # Check if referred by someone
                        if " " in text:
                            referrer_id = text.split()[1]
                            ref_path = db.reference(f'users/{referrer_id}')
                            ref_data = ref_path.get()
                            if ref_data and str(referrer_id) != str(chat_id):
                                new_points = ref_data.get('points', 0) + 15
                                ref_path.update({"points": new_points})
                                bot.send_message(referrer_id, f"🎊 Mubarak! Aapke link se koi join hua. +15 Points added!")
                    
                    update.message.reply_text(
                        f"Welcome {update.message.from_user.first_name}! 🤑\nEarn points by watching ads and inviting friends." + MOTIVATION,
                        reply_markup=get_main_keyboard(),
                        parse_mode="Markdown"
                    )

                # /redeem Code Logic
                elif text.startswith("/redeem"):
                    code = text.split()[1] if len(text.split()) > 1 else ""
                    if code == "GIFT10": # Aap ye code badal sakte hain
                        current_pts = user_data.get('points', 0) if user_data else 0
                        user_ref.update({"points": current_pts + 10})
                        update.message.reply_text("✅ Sahi Code! 10 Points aapke account mein daal diye gaye hain." + MOTIVATION)
                    else:
                        update.message.reply_text("❌ Galat ya purana code! Sahi code use karein.")

            # --- Handle Buttons ---
            elif update.callback_query:
                query = update.callback_query
                chat_id = query.message.chat_id
                user_ref = db.reference(f'users/{chat_id}')
                user_data = user_ref.get()
                
                if query.data == "confirm_ad":
                    now = time.time()
                    last_ad = user_data.get('last_ad_time', 0)
                    
                    if now - last_ad > 3600: # 1 Hour Timer
                        new_pts = user_data.get('points', 0) + 5
                        user_ref.update({"points": new_pts, "last_ad_time": now})
                        query.answer("✅ +5 Points Added!", show_alert=True)
                        query.edit_message_text(f"Shukriya! Aapne ad dekha. 5 points mil gaye.\n💰 Naya Balance: {new_pts}" + MOTIVATION, reply_markup=get_main_keyboard())
                    else:
                        wait_min = int((3600 - (now - last_ad)) / 60)
                        query.answer(f"⏳ Ad abhi locked hai! {wait_min} minute baad try karein.", show_alert=True)

                elif query.data == "invite":
                    bot_info = bot.get_me()
                    invite_link = f"https://t.me/{bot_info.username}?start={chat_id}"
                    query.edit_message_text(f"📢 *Invite & Earn*\nIs link ko share karein. Har join par 15 points milenge!\n\n`{invite_link}`" + MOTIVATION, reply_markup=get_main_keyboard(), parse_mode="Markdown")

                elif query.data == "balance":
                    pts = user_data.get('points', 0) if user_data else 0
                    query.answer(f"💰 Aapka Balance: {pts} Points", show_alert=True)

            return "ok", 200
        except Exception as e:
            print(f"Error: {e}")
            return "error", 500
    return "done", 200

@app.route('/')
def index():
    return "Earning Bot is Live and Running!"
