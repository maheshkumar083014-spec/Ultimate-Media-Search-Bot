import os, firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

app = Flask(__name__)

# --- APKE SARE DETAILS ---
TOKEN = os.getenv("BOT_TOKEN")
YT = "https://www.youtube.com/@USSoccerPulse"
FB = "https://www.facebook.com/61574378159053"
INSTA = "https://instagram.com/digital_rockstar_m"
AD_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"

bot = Bot(token=TOKEN)

# --- FIREBASE SETUP ---
if not firebase_admin._apps:
    p_key = os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n').strip('"')
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": "ultimatemediasearch",
        "private_key": p_key,
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "token_uri": "https://oauth2.googleapis.com/token",
    })
    firebase_admin.initialize_app(cred, {'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'})

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        if update.message and update.message.text:
            chat_id = str(update.message.chat_id)
            user_ref = db.reference(f'users/{chat_id}')
            data = user_ref.get()

            # 1. WELCOME SMS & EARNING PLAN
            if update.message.text.startswith("/start"):
                if not data:
                    # Naye user ko 10 coins bonus (Earning Plan)
                    user_ref.set({"pts": 10, "refs": 0, "name": update.message.from_user.first_name})
                
                # DASHBOARD BUTTON
                dash_url = f"https://{request.host}/dashboard?id={chat_id}"
                menu = ReplyKeyboardMarkup([[KeyboardButton("📊 Dashboard", web_app=WebAppInfo(url=dash_url))]], resize_keyboard=True)
                
                # 2. SOCIAL TASKS BUTTONS
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔴 YouTube Task", url=YT)],
                    [InlineKeyboardButton("🔵 Facebook Task", url=FB)],
                    [InlineKeyboardButton("🟣 Instagram Task", url=INSTA)],
                    [InlineKeyboardButton("👫 Invite & Earn (+15)", callback_data="invite")]
                ])

                welcome_msg = "🚀 *Welcome to EARNPRO!*\n\n💰 *Earning Plan:*\n• Join Bonus: +10 Coins\n• Daily Ad: +10 Coins\n• Per Refer: +15 Coins\n\nNiche Dashboard se apni earning check karein!"
                bot.send_message(chat_id, welcome_msg, reply_markup=menu, parse_mode="Markdown")
                bot.send_message(chat_id, "✅ *Complete Tasks to Earn:*", reply_markup=kb, parse_mode="Markdown")

        return "ok", 200
    return "Bot is Active!"

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', 'Unknown')
    u = db.reference(f'users/{uid}').get() or {"pts": 0}
    # 3. AD LINK YAHAN BHI HAI
    return render_template('dashboard.html', pts=u.get('pts', 0), uid=uid, ad_link=AD_LINK)
