import os
import time
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup

app = Flask(__name__)

# --- CONFIGURATION ---
ADMIN_ID = "8701635891"
# Direct Image Link for Bot
WELCOME_IMAGE = "https://i.ibb.co/zWJHms9p/image.jpg"

# Deep Links (For Direct App Opening)
YT_LINK = "https://www.youtube.com/@USSoccerPulse"
FB_LINK = "fb://facewebmodal/f?href=https://www.facebook.com/61574378159053"
INSTA_LINK = "instagram://user?username=digital_rockstar_m"
AD_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"

# --- FIREBASE INIT ---
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
        firebase_admin.initialize_app(cred, {'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'})
    except Exception as e:
        print(f"Firebase Error: {e}")

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

# --- KEYBOARDS ---
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 My Dashboard", callback_data="dash")],
        [InlineKeyboardButton("📺 Watch Ad (Earn 5 pts)", url=AD_LINK)],
        [InlineKeyboardButton("✅ Confirm Ad View", callback_data="confirm_ad")],
        [InlineKeyboardButton("📱 Social Tasks (15 pts)", callback_data="social_menu")],
        [InlineKeyboardButton("👫 Invite & Earn (15 pts)", callback_data="invite_link")],
        [InlineKeyboardButton("💸 Withdraw Cash", callback_data="withdraw_now")]
    ])

@app.route('/api/index', methods=['POST'])
def webhook():
    if request.method == "POST":
        try:
            update = Update.de_json(request.get_json(force=True), bot)
            if not update: return "ok", 200

            # --- MESSAGE HANDLING ---
            if update.message:
                chat_id = str(update.message.chat_id)
                user_ref = db.reference(f'users/{chat_id}')
                user_data = user_ref.get()

                # Withdrawal Input Security
                if user_data and user_data.get('state') == 'AWAITING_WITHDRAWAL':
                    details = update.message.text
                    user_ref.update({"state": "NORMAL", "pending_details": details})
                    bot.send_message(chat_id, "✅ Details Saved! Admin ko notification bhej di gayi hai. 24-48 hours intezar karein.")
                    bot.send_message(ADMIN_ID, f"💰 *WITHDRAW REQUEST*\nUser: {chat_id}\nDetails: {details}\nBalance: {user_data.get('pts')} pts", parse_mode="Markdown")
                    return "ok", 200

                # /start handling
                if update.message.text and update.message.text.startswith("/start"):
                    if not user_data:
                        # New User + Referral Check
                        pts = 10
                        referrer = None
                        if " " in update.message.text:
                            ref_id = update.message.text.split()[1]
                            if ref_id != chat_id:
                                referrer = ref_id
                                r_ref = db.reference(f'users/{ref_id}')
                                r_data = r_ref.get()
                                if r_data:
                                    r_ref.update({"pts": r_data.get('pts', 0) + 15, "refs": r_data.get('refs', 0) + 1})
                                    bot.send_message(ref_id, "🎊 Naya referral juda! +15 Points added.")

                        user_ref.set({"pts": pts, "refs": 0, "last_ad": 0, "name": update.message.from_user.first_name, "state": "NORMAL"})

                    bot.send_photo(
                        chat_id, WELCOME_IMAGE,
                        caption=f"🔥 *DIGITAL ROCKSTAR EARNING* 🔥\n\nSwaagat hai {update.message.from_user.first_name}!\nYahan aap daily tasks se unlimited kama sakte hain.\n\n🚀 *Mehnat karein, kamayein!*",
                        reply_markup=main_keyboard(), parse_mode="Markdown"
                    )

            # --- CALLBACK HANDLING ---
            elif update.callback_query:
                query = update.callback_query
                chat_id = str(query.message.chat_id)
                user_ref = db.reference(f'users/{chat_id}')
                user_data = user_ref.get()

                if query.data == "dash":
                    pts = user_data.get('pts', 0)
                    refs = user_data.get('refs', 0)
                    query.edit_message_caption(
                        caption=f"👤 *USER DASHBOARD*\n\n💰 Total Balance: {pts} Points\n👥 Total Referrals: {refs}\n💵 Earning: ₹{pts/10}\n\nKeep sharing to earn more!",
                        reply_markup=main_keyboard(), parse_mode="Markdown"
                    )

                elif query.data == "confirm_ad":
                    now = time.time()
                    if now - user_data.get('last_ad', 0) > 30:
                        new_pts = user_data.get('pts', 0) + 5
                        user_ref.update({"pts": new_pts, "last_ad": now})
                        query.answer("✅ +5 Points Added!", show_alert=True)
                        query.edit_message_caption(caption=f"💰 Points Update! Balance: {new_pts}", reply_markup=main_keyboard())
                    else:
                        query.answer("⏳ 30 seconds ad watch karein pehle!", show_alert=True)

                elif query.data == "social_menu":
                    kb = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔴 YouTube", url=YT_LINK)],
                        [InlineKeyboardButton("🔵 Facebook", url=FB_LINK), InlineKeyboardButton("🟣 Instagram", url=INSTA_LINK)],
                        [InlineKeyboardButton("💰 Claim 15 Pts", callback_data="claim_soc")]
                    ])
                    query.edit_message_caption(caption="📱 *SOCIAL TASKS*\nSabhi links ko follow karein aur Claim dabayein:", reply_markup=kb, parse_mode="Markdown")

                elif query.data == "claim_soc":
                    if not user_data.get('soc_claimed'):
                        user_ref.update({"pts": user_data.get('pts', 0) + 15, "soc_claimed": True})
                        query.answer("🎉 15 Points Added!", show_alert=True)
                        query.edit_message_caption(caption="✅ Tasks Completed!", reply_markup=main_keyboard())
                    else:
                        query.answer("❌ Ye task pehle ho chuka hai.", show_alert=True)

                elif query.data == "invite_link":
                    link = f"https://t.me/{bot.get_me().username}?start={chat_id}"
                    query.edit_message_caption(caption=f"🤝 *REFER & EARN*\nShare this link. Per refer: 15 points!\n\n`{link}`", reply_markup=main_keyboard(), parse_mode="Markdown")

                elif query.data == "withdraw_now":
                    if user_data.get('pts', 0) < 100:
                        query.answer("⚠️ Min 100 points required!", show_alert=True)
                    else:
                        user_ref.update({"state": "AWAITING_WITHDRAWAL"})
                        query.edit_message_caption(caption="🏦 *WITHDRAWAL*\n\nApna Mobile No, Paytm/GPay aur UPI ID niche likh kar bhejein:", reply_markup=None)

            return "ok", 200
        except Exception as e:
            print(f"Error: {e}")
            return "error", 500
    return "done", 200

@app.route('/')
def index():
    return "<h1>Bot is Active and Secure!</h1>"
