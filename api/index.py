import os, time, firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template, render_template_string
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

app = Flask(__name__)

# --- CONFIG (Data from User Summary) ---
ADMIN_ID = "8701635891"
WELCOME_IMG = "https://i.ibb.co/zWJHms9p/image.jpg"
YT = "https://www.youtube.com/@USSoccerPulse"
FB = "https://www.facebook.com/61574378159053"
INSTA = "https://instagram.com/digital_rockstar_m"
AD_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"

# --- FIREBASE SETUP ---
if not firebase_admin._apps:
    raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n').strip().strip('"').strip("'")
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": "ultimatemediasearch",
        "private_key": raw_key,
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "token_uri": "https://oauth2.googleapis.com/token"
    })
    firebase_admin.initialize_app(cred, {'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'})

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        if update.message and update.message.text:
            chat_id = str(update.message.chat_id)
            user_ref = db.reference(f'users/{chat_id}')
            data = user_ref.get()
            dashboard_url = f"https://{request.host}/dashboard?id={chat_id}"

            if update.message.text.startswith("/start"):
                if not data:
                    user_ref.set({"pts": 10, "refs": 0, "name": update.message.from_user.first_name})
                
                # Blue Menu Button
                menu = ReplyKeyboardMarkup([[KeyboardButton("📊 Dashboard", web_app=WebAppInfo(url=dashboard_url))]], resize_keyboard=True)
                
                # Social Links Buttons
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔴 YouTube", url=YT)],
                    [InlineKeyboardButton("🔵 Facebook", url=FB), InlineKeyboardButton("🟣 Instagram", url=INSTA)],
                    [InlineKeyboardButton("👫 Invite & Earn", callback_data="invite")]
                ])

                bot.send_photo(chat_id, WELCOME_IMG, caption="💎 *EARNPRO OFFICIAL*\n\nNiche diye gaye Dashboard button se apni kamai check karein!", reply_markup=menu, parse_mode="Markdown")
                bot.send_message(chat_id, "Check Social Tasks here:", reply_markup=kb)
        return "ok", 200
    return "Bot is Active!"

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', 'Unknown')
    u = db.reference(f'users/{uid}').get() or {"pts": 0, "refs": 0}
    return render_template('dashboard.html', pts=u['pts'], refs=u['refs'], uid=uid, ad_link=AD_LINK)
