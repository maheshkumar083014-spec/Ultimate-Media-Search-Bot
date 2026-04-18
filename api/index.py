import os, firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

app = Flask(__name__)

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN") # 8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw
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
            
            # Welcome Bonus +10
            if not user_ref.get():
                user_ref.set({"pts": 10, "refs": 0, "name": update.message.from_user.first_name})

            # Dashboard WebApp
            dash_url = f"https://{request.host}/dashboard?id={chat_id}"
            menu = ReplyKeyboardMarkup([[KeyboardButton("📊 Open Dashboard", web_app=WebAppInfo(url=dash_url))]], resize_keyboard=True)
            
            # Tasks Keyboard
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📺 YouTube Task", url="https://www.youtube.com/@USSoccerPulse")],
                [InlineKeyboardButton("📸 Instagram Task", url="https://instagram.com/digital_rockstar_m")],
                [InlineKeyboardButton("🔵 Facebook Task", url="https://www.facebook.com/61574378159053")]
            ])

            bot.send_message(chat_id, "💰 *EARNPRO ACTIVE*\n\nJoin Bonus: +10 Coins\nRefer: +15 Coins\n\nComplete tasks below or open Dashboard!", reply_markup=menu, parse_mode="Markdown")
            bot.send_message(chat_id, "👇 *Social Tasks:*", reply_markup=kb, parse_mode="Markdown")
        return "ok", 200
    return "Bot status: Running"

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', 'Unknown')
    u = db.reference(f'users/{uid}').get() or {"pts": 0}
    return render_template('dashboard.html', pts=u.get('pts', 0), uid=uid, ad_link=AD_LINK)
