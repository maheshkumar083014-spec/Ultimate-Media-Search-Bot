import os
import time
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template_string
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

app = Flask(__name__)

# --- CONFIG ---
WELCOME_IMG = "https://i.ibb.co/zWJHms9p/image.jpg"
YT_LINK = "https://www.youtube.com/@USSoccerPulse"
FB_LINK = "https://www.facebook.com/61574378159053"
INSTA_LINK = "https://www.instagram.com/digital_rockstar_m"
AD_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"

# --- FIREBASE INIT FIX ---
def init_firebase():
    if not firebase_admin._apps:
        try:
            raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n').strip().strip('"').strip("'")
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": os.getenv("FIREBASE_PROJECT_ID", "ultimatemediasearch"),
                "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": raw_key,
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
            })
            firebase_admin.initialize_app(cred, {'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'})
            return True
        except Exception as e:
            return False
    return True

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == "POST":
        try:
            init_firebase()
            update = Update.de_json(request.get_json(force=True), bot)
            if not update or not update.effective_user: return "ok", 200
            
            chat_id = str(update.effective_user.id)
            user_ref = db.reference(f'users/{chat_id}')
            user_data = user_ref.get()

            if update.message and update.message.text and update.message.text.startswith("/start"):
                if not user_data:
                    user_ref.set({"pts": 10, "refs": 0, "name": update.effective_user.first_name})
                
                # Dynamic Dashboard URL
                dash_url = f"https://{request.host}/dashboard?id={chat_id}"
                
                markup = ReplyKeyboardMarkup([[KeyboardButton("📊 My Dashboard", web_app=WebAppInfo(url=dash_url))]], resize_keyboard=True)
                inline_kb = InlineKeyboardMarkup([[InlineKeyboardButton("📺 Watch Ad (5 pts)", url=AD_LINK)], [InlineKeyboardButton("👫 Invite Friends", callback_data="invite")]])

                bot.send_photo(chat_id, WELCOME_IMG, caption=f"🔥 *EarnPro Bot Mein Swagat Hai!*\n\nAap niche diye gaye 'Dashboard' button se apni earning check kar sakte hain.", reply_markup=inline_kb, parse_mode="Markdown")
                bot.send_message(chat_id, "Dashboard par aapko aapke saare links mil jayenge.", reply_markup=markup)

            elif update.callback_query and update.callback_query.data == "invite":
                bot.send_message(chat_id, f"🎁 *Invite Link:* https://t.me/{bot.get_me().username}?start={chat_id}", parse_mode="Markdown")

            return "ok", 200
        except: return "ok", 200
    return "<h1>Bot is Active</h1>"

# --- REAL DASHBOARD ---
@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id')
    init_firebase()
    u = db.reference(f'users/{uid}').get() or {"pts": 0, "refs": 0, "name": "Guest"}
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { background: #0f172a; color: white; font-family: sans-serif; margin: 0; padding: 15px; text-align: center; }
            .header { background: linear-gradient(to right, #3b82f6, #8b5cf6); padding: 20px; border-radius: 15px; margin-bottom: 15px; }
            .stats { display: flex; justify-content: space-around; background: #1e293b; padding: 15px; border-radius: 15px; border: 1px solid #334155; }
            .points { font-size: 32px; color: #fbbf24; font-weight: bold; }
            .guide { background: #064e3b; padding: 15px; border-radius: 12px; margin: 15px 0; text-align: left; border-left: 5px solid #10b981; }
            .links-box { background: #1e293b; border-radius: 15px; padding: 15px; text-align: left; }
            .btn { display: block; background: #334155; color: white; padding: 12px; margin: 10px 0; border-radius: 10px; text-decoration: none; font-weight: bold; }
            .btn:hover { background: #475569; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>Welcome, {{name}}!</h2>
            <p>EarnPro Dashboard</p>
        </div>

        <div class="stats">
            <div><small>POINTS</small><div class="points">{{pts}}</div></div>
            <div><small>REFERRALS</small><div class="points">{{refs}}</div></div>
        </div>

        <div class="guide">
            🚀 <b>Earning Tip:</b> Hamare Instagram, Facebook aur YouTube videos ko doston ke sath share karein. Har share par aapko extra points milenge!
        </div>

        <div class="links-box">
            <h3 style="color:#fbbf24; margin-top:0;">🔗 My Social Links</h3>
            <a href="{{yt}}" class="btn">🔴 Subscribe YouTube</a>
            <a href="{{fb}}" class="btn">🔵 Follow Facebook</a>
            <a href="{{insta}}" class="btn">🟣 Follow Instagram</a>
        </div>
    </body>
    </html>
    """, pts=u['pts'], refs=u['refs'], name=u['name'], yt=YT_LINK, fb=FB_LINK, insta=INSTA_LINK)
