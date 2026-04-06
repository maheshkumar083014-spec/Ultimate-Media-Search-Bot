import os
import time
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup

app = Flask(__name__)

# --- CONFIGURATION (Updated by User) ---
ADMIN_ID = "8701635891" 
WELCOME_IMAGE = "https://ibb.co/zWJHms9p" 

# --- DEEP LINKS (Direct App Open) ---
YT = "https://www.youtube.com/@USSoccerPulse"
FB = "fb://facewebmodal/f?href=https://www.facebook.com/61574378159053"
INSTA = "instagram://user?username=digital_rockstar_m"
AD_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"

# --- FIREBASE SETUP ---
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

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 My Dashboard", callback_data="dash")],
        [InlineKeyboardButton("📺 Watch Ad (30s Wait)", url=AD_LINK)],
        [InlineKeyboardButton("✅ Claim Ad Points", callback_data="claim_ad")],
        [InlineKeyboardButton("📱 Social Tasks (15 pts)", callback_data="social")],
        [InlineKeyboardButton("👫 Invite Friends (15 pts)", callback_data="invite")],
        [InlineKeyboardButton("💸 Withdraw Cash", callback_data="withdraw")]
    ])

@app.route('/api/index', methods=['POST'])
def webhook():
    if request.method == "POST":
        try:
            update = Update.de_json(request.get_json(force=True), bot)
            
            if update.message:
                chat_id = update.message.chat_id
                user_ref = db.reference(f'users/{chat_id}')
                data = user_ref.get() or {"pts": 10, "refs": 0, "last_ad": 0}

                # Withdrawal Logic: Save Details
                if data.get('state') == 'WAIT_DETAILS':
                    user_ref.update({"state": "NORMAL", "withdraw_info": update.message.text})
                    bot.send_message(chat_id, "✅ Aapki details save ho gayi hain! Payment 24-48 hours mein process hogi.")
                    bot.send_message(ADMIN_ID, f"💰 *NEW WITHDRAWAL REQUEST*\n\nUser ID: `{chat_id}`\nDetails: {update.message.text}\nPoints: {data.get('pts')}", parse_mode="Markdown")
                    return "ok", 200

                # /start with Referral Tracking
                if update.message.text.startswith("/start"):
                    is_new = False
                    if not user_ref.get():
                        is_new = True
                        user_ref.set({"pts": 10, "refs": 0, "last_ad": 0, "name": update.message.from_user.first_name})
                        
                        # Referral logic
                        if " " in update.message.text:
                            ref_id = update.message.text.split()[1]
                            if str(ref_id) != str(chat_id):
                                r_ref = db.reference(f'users/{ref_id}')
                                r_data = r_ref.get()
                                if r_data:
                                    r_ref.update({"pts": r_data.get('pts', 0) + 15, "refs": r_data.get('refs', 0) + 1})
                                    bot.send_message(ref_id, f"🎊 Naya referral! +15 Points mil gaye.")

                    bot.send_photo(
                        chat_id, 
                        WELCOME_IMAGE, 
                        caption=f"💎 *WELCOME TO DIGITAL ROCKSTAR* 💎\n\nHello {update.message.from_user.first_name}!\nDaily tasks poore karein aur unlimited earn karein.\n\n🚀 *Mehnat karein, kamai karein!*", 
                        reply_markup=main_kb(), 
                        parse_mode="Markdown"
                    )

            elif update.callback_query:
                query = update.callback_query
                chat_id = query.message.chat_id
                user_ref = db.reference(f'users/{chat_id}')
                data = user_ref.get()

                if query.data == "dash":
                    pts = data.get('pts', 10)
                    refs = data.get('refs', 0)
                    query.edit_message_caption(
                        caption=f"👤 *USER DASHBOARD*\n\n💰 Balance: {pts} Points\n👥 Total Referrals: {refs}\n💵 Value: ₹{pts/10}\n\nDoston ko invite karein earning badhane ke liye!",
                        reply_markup=main_kb(),
                        parse_mode="Markdown"
                    )

                elif query.data == "claim_ad":
                    now = time.time()
                    if now - data.get('last_ad', 0) > 30: # 30 Second Watch Security
                        user_ref.update({"pts": data.get('pts', 0) + 5, "last_ad": now})
                        query.answer("✅ +5 Points Added!", show_alert=True)
                    else:
                        query.answer("⏳ Ad 30 seconds tak watch karein!", show_alert=True)

                elif query.data == "social":
                    s_kb = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔴 YouTube Sub", url=YT)],
                        [InlineKeyboardButton("🔵 FB Follow", url=FB), InlineKeyboardButton("🟣 Insta Like", url=INSTA)],
                        [InlineKeyboardButton("✅ Claim Social Pts", callback_data="claim_soc")]
                    ])
                    query.edit_message_caption(caption="📱 *SOCIAL TASKS*\nFollow & Subscribe karein aur Claim dabayein:", reply_markup=s_kb, parse_mode="Markdown")

                elif query.data == "claim_soc":
                    if not data.get('soc_done'):
                        user_ref.update({"pts": data.get('pts', 0) + 15, "soc_done": True})
                        query.answer("🎉 15 Points Added!", show_alert=True)
                        query.edit_message_caption(caption="✅ Tasks Complete!", reply_markup=main_kb())
                    else:
                        query.answer("❌ Ye task aap pehle hi kar chuke hain.", show_alert=True)

                elif query.data == "withdraw":
                    if data.get('pts', 0) < 100:
                        query.answer("⚠️ Minimum 100 points required!", show_alert=True)
                    else:
                        user_ref.update({"state": "WAIT_DETAILS"})
                        query.edit_message_caption(caption="🏦 *WITHDRAWAL*\n\nApna Mobile No, Paytm/GPay aur UPI ID likh kar bhejein:", reply_markup=None)

                elif query.data == "invite":
                    link = f"https://t.me/{bot.get_me().username}?start={chat_id}"
                    query.edit_message_caption(caption=f"👫 *REFER & EARN*\n\nHar referral par 15 points milega.\nAapka Link:\n`{link}`", reply_markup=main_kb(), parse_mode="Markdown")

            return "ok", 200
        except Exception as e:
            print(f"Error: {e}")
            return "error", 500
    return "done", 200

@app.route('/')
def index():
    return "Bot is Running Perfectly!"
