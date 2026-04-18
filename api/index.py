import os, time, firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template_string
from telegram import Update, Bot, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

app = Flask(__name__)

# --- CONFIG ---
ADMIN_ID = "8701635891"
WELCOME_IMG = "https://i.ibb.co/zWJHms9p/image.jpg"
YT = "https://www.youtube.com/@USSoccerPulse"
FB = "https://www.facebook.com/61574378159053"
INSTA = "https://instagram.com/digital_rockstar_m"
AD_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"

# --- FIREBASE ---
if not firebase_admin._apps:
    raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n').strip().strip('"').strip("'")
    cred = credentials.Certificate({"type": "service_account", "project_id": "ultimatemediasearch", "private_key": raw_key, "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"), "token_uri": "https://oauth2.googleapis.com/token"})
    firebase_admin.initialize_app(cred, {'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'})

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        if update.message and update.message.text:
            chat_id = str(update.message.chat_id)
            dashboard_url = f"https://{request.host}/dashboard?id={chat_id}"
            
            # Save User if new
            user_ref = db.reference(f'users/{chat_id}')
            if not user_ref.get():
                user_ref.set({"pts": 10, "refs": 0, "name": update.message.from_user.first_name})

            menu = ReplyKeyboardMarkup([[KeyboardButton("📊 Dashboard", web_app=WebAppInfo(url=dashboard_url))]], resize_keyboard=True)
            bot.send_photo(chat_id, WELCOME_IMG, caption="🚀 *EARNPRO DASHBOARD LIVE*\n\nNiche diye gaye button se Dashboard kholein aur kamai shuru karein!", reply_markup=menu, parse_mode="Markdown")
        return "ok", 200
    return "Bot is Active!"

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', 'Unknown')
    u = db.reference(f'users/{uid}').get() or {"pts": 0, "refs": 0}
    return render_template_string("""
    <!DOCTYPE html>
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background: #0b0e14; color: white; font-family: sans-serif; padding: 15px; margin: 0; }
        .card { background: #161b22; border-radius: 25px; padding: 25px; border: 1px solid #30363d; margin-bottom: 20px; text-align: center; }
        .coin-text { font-size: 55px; color: #fbbf24; font-weight: bold; margin: 10px 0; }
        .task-row { background: #1c2128; border-radius: 15px; padding: 15px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; border: 1px solid #30363d; }
        .btn-action { background: #fbbf24; color: black; border: none; padding: 8px 18px; border-radius: 20px; font-weight: bold; text-decoration: none; font-size: 13px; }
        .promo-box { border: 1px dashed #2563eb; padding: 20px; border-radius: 20px; text-align: center; background: rgba(37,99,235,0.05); }
    </style></head>
    <body>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <div style="background: #2563eb; padding: 5px 15px; border-radius: 10px; font-weight: bold;">EARNPRO</div>
            <div style="color: #8b949e;">ID: EP-{{uid[:6]}}</div>
        </div>

        <div class="card">
            <small style="color: #8b949e;">AVAILABLE COINS</small>
            <div class="coin-text">{{u.pts}}.00</div>
            <div style="background: rgba(255,255,255,0.05); padding: 5px 15px; border-radius: 20px; display: inline-block; font-size: 12px;">MIN. PAYOUT: 200</div>
        </div>

        <h3 style="margin-left: 10px;">Tasks</h3>
        <div class="task-row" style="border-left: 4px solid #2563eb;">
            <div><b>Daily Reward</b><br><small style="color: #8b949e;">+5.00 Coins</small></div>
            <div style="color: #8b949e;">Claimed</div>
        </div>
        <div class="task-row" style="border-left: 4px solid #fbbf24;">
            <div><b>Video Ad Task</b><br><small style="color: #8b949e;">+10.00 Coins</small></div>
            <a href="{{ad_link}}" class="btn-action">Watch</a>
        </div>
        <div class="task-row" style="border-left: 4px solid #ff0000;">
            <div><b>YouTube Task</b><br><small style="color: #8b949e;">Subscribe & Earn</small></div>
            <a href="{{yt}}" class="btn-action" style="background: #ff0000; color: white;">Sub</a>
        </div>

        <div class="promo-box">
            <small style="color: #8b949e;">YOUR INVITATION CODE</small>
            <h2 style="color: #2563eb; letter-spacing: 3px; margin: 10px 0;">EP-{{uid[:6]}}</h2>
            <button onclick="window.location.href='https://t.me/share/url?url=https://t.me/bot?start={{uid}}'" style="background: #2563eb; color: white; border: none; padding: 12px; width: 100%; border-radius: 12px; font-weight: bold;">SHARE & EARN +15</button>
        </div>
    </body></html>
    """, u=u, uid=uid, ad_link=AD_LINK, yt=YT)
