import os
import time
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template_string
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup

app = Flask(__name__)

# --- 1. Firebase Setup ---
if not firebase_admin._apps:
    raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n').strip().strip('"').strip("'")
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": "ultimatemediasearch",
        "private_key": raw_key,
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "token_uri": "https://oauth2.googleapis.com/token",
    })
    firebase_admin.initialize_app(cred, {'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'})

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

# --- Links & Config ---
YT_LINK = "https://www.youtube.com/@USSoccerPulse"
FB_LINK = "https://www.facebook.com/profile.php?id=61574378159053"
INSTA_LINK = "https://www.instagram.com/digital_rockstar_m?igsh=ajV3eGhhdWg1YnR4"
AD_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"

MOTIVATION = "\n\n✨ *Sapne bade hain toh mehnat bhi badi karni hogi. Roz earn karein!*"

# --- Keyboards ---
def main_menu():
    keyboard = [
        [InlineKeyboardButton("💰 My Wallet & Dashboard", callback_data="dashboard")],
        [InlineKeyboardButton("📺 Watch Ad (5 pts)", url=AD_LINK)],
        [InlineKeyboardButton("🌟 Social Tasks (Earn More)", callback_data="social_tasks")],
        [InlineKeyboardButton("👫 Invite & Earn (15 pts)", callback_data="invite")],
        [InlineKeyboardButton("💸 Withdraw Money", callback_data="withdraw")]
    ]
    return InlineKeyboardMarkup(keyboard)

@app.route('/api/index', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    if update.message:
        chat_id = update.message.chat_id
        user_ref = db.reference(f'users/{chat_id}')
        data = user_ref.get()

        if update.message.text.startswith("/start"):
            if not data:
                user_ref.set({"points": 10, "name": update.message.from_user.first_name, "tasks": {}})
            
            welcome_text = (
                f"💎 *WELCOME TO DIGITAL ROCKSTAR EARNING BOT* 💎\n\n"
                f"Hello {update.message.from_user.first_name}!\n"
                f"Aap yahan simple tasks pure karke real money earn kar sakte hain."
                f"{MOTIVATION}"
            )
            bot.send_message(chat_id, welcome_text, reply_markup=main_menu(), parse_mode="Markdown")

        # Withdrawal Data Handling
        elif data and data.get('awaiting_withdrawal'):
            user_ref.update({"withdrawal_info": update.message.text, "awaiting_withdrawal": False})
            bot.send_message(chat_id, "✅ Aapki details save ho gayi hain! Hamari team 24-48 hours mein verify karke payment kar degi.")

    elif update.callback_query:
        query = update.callback_query
        chat_id = query.message.chat_id
        user_ref = db.reference(f'users/{chat_id}')
        data = user_ref.get()

        if query.data == "social_tasks":
            kb = [
                [InlineKeyboardButton("🔴 YouTube Sub (5 pts)", url=YT_LINK)],
                [InlineKeyboardButton("🔵 Facebook Follow (5 pts)", url=FB_LINK)],
                [InlineKeyboardButton("🟣 Instagram Like (5 pts)", url=INSTA_LINK)],
                [InlineKeyboardButton("✅ Claim Points", callback_data="claim_social")],
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ]
            query.edit_message_text("📱 *Social Tasks*\nLinks par click karein, subscribe/follow karein aur Claim dabayein.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

        elif query.data == "claim_social":
            # Simple simulation: User claims 15 points for all social tasks once
            if not data.get('social_claimed'):
                user_ref.update({"points": data['points'] + 15, "social_claimed": True})
                query.answer("🎉 15 Points added for Social Tasks!", show_alert=True)
            else:
                query.answer("❌ Aap ye tasks pehle hi kar chuke hain.", show_alert=True)

        elif query.data == "dashboard" or query.data == "balance":
            pts = data.get('points', 0)
            query.edit_message_text(f"💳 *USER DASHBOARD*\n\n👤 Name: {data.get('name')}\n💰 Total Balance: {pts} Points\n💵 Value: ₹{pts/10} (approx)\n\nHar 10 points = ₹1", reply_markup=main_menu(), parse_mode="Markdown")

        elif query.data == "withdraw":
            if data.get('points', 0) < 100:
                query.answer("⚠️ Minimum 100 points chahiye withdrawal ke liye!", show_alert=True)
            else:
                user_ref.update({"awaiting_withdrawal": True})
                query.edit_message_text("🏦 *WITHDRAWAL SECTION*\n\nApna Mobile Number aur UPI ID (Google Pay/Paytm/PhonePe) niche likh kar bhejein.\n\nExample: 9876543210, example@upi")

        elif query.data == "invite":
            link = f"https://t.me/{bot.get_me().username}?start={chat_id}"
            query.edit_message_text(f"🤝 *INVITE FRIENDS*\nShare your link and earn 15 points per referral!\n\n`{link}`", reply_markup=main_menu(), parse_mode="Markdown")

        elif query.data == "back":
            query.edit_message_text("💎 *DIGITAL ROCKSTAR MENU*", reply_markup=main_menu())

    return "ok", 200

# --- Dashboard Web Page ---
@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { background: linear-gradient(135deg, #1a1a2e, #16213e); color: white; font-family: 'Segoe UI', sans-serif; text-align: center; padding: 50px; }
            .card { background: rgba(255,255,255,0.1); padding: 30px; border-radius: 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.3); }
            h1 { color: #4ecca3; }
            .btn { background: #4ecca3; color: #1a1a2e; padding: 15px 30px; text-decoration: none; border-radius: 50px; font-weight: bold; display: inline-block; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🚀 Rockstar Dashboard</h1>
            <p>Bot is Online & Paying!</p>
            <p>Go to Telegram to check your live balance.</p>
            <a href="https://t.me/{{ bot_username }}" class="btn">Open Telegram Bot</a>
        </div>
    </body>
    """, bot_username=bot.get_me().username)
