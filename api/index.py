import os
import time
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template_string
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

app = Flask(__name__)

# --- CONFIG ---
WELCOME_IMG = "https://i.ibb.co/zWJHms9p/image.jpg"
YT = "https://www.youtube.com/@USSoccerPulse"
FB = "https://www.facebook.com/61574378159053"
INSTA = "https://www.instagram.com/digital_rockstar_m"

# --- FIREBASE INIT ---
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
        except: pass

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
            user_name = update.effective_user.first_name
            user_ref = db.reference(f'users/{chat_id}')
            
            if update.message and update.message.text and update.message.text.startswith("/start"):
                if not user_ref.get():
                    user_ref.set({"pts": 10, "refs": 0, "name": user_name})
                
                dash_url = f"https://{request.host}/dashboard?id={chat_id}"
                markup = ReplyKeyboardMarkup([[KeyboardButton("📊 Open Dashboard", web_app=WebAppInfo(url=dash_url))]], resize_keyboard=True)
                
                bot.send_photo(
                    chat_id, WELCOME_IMG, 
                    caption=f"🔥 *Assalam-o-Alaikum {user_name}!*\n\nAapka earning bot taiyar hai. Rozana tasks poore karein aur paise kamayein!",
                    parse_mode="Markdown", reply_markup=markup
                )
            return "ok", 200
        except: return "ok", 200
    return "Bot is Active"

# --- DASHBOARD WITH TASKS ---
@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id')
    init_firebase()
    u = db.reference(f'users/{uid}').get() or {"pts": 0, "refs": 0, "name": "User"}
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { background: #0b0e14; color: white; font-family: sans-serif; padding: 15px; margin: 0; text-align: center; }
            .card { background: linear-gradient(145deg, #1e293b, #0f172a); border-radius: 20px; padding: 20px; border: 1px solid #334155; box-shadow: 0 8px 32px rgba(0,0,0,0.5); }
            .points { font-size: 45px; color: #fbbf24; font-weight: bold; margin: 10px 0; }
            .task-box { background: #161b22; border-radius: 15px; padding: 15px; margin-top: 20px; text-align: left; border: 1px solid #30363d; }
            .task-item { display: flex; justify-content: space-between; align-items: center; background: #21262d; padding: 12px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #30363d; }
            .btn-go { background: #238636; color: white; padding: 8px 15px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: bold; }
            .section-title { color: #58a6ff; font-weight: bold; margin-bottom: 10px; display: block; }
            .tip { font-size: 12px; color: #8b949e; margin-top: 20px; font-style: italic; }
        </style>
    </head>
    <body>
        <div class="card">
            <p style="margin:0; color:#8b949e;">Welcome, {{name}}</p>
            <div class="points">{{pts}}</div>
            <p style="margin:0; letter-spacing: 1px; font-size:12px;">AVAILABLE POINTS</p>
        </div>

        <div class="task-box">
            <span class="section-title">🎯 DAILY EARNING TASKS</span>
            
            <div class="task-item">
                <span>🔴 Subscribe YouTube</span>
                <a href="{{yt}}" class="btn-go">GO (+5)</a>
            </div>
            
            <div class="task-item">
                <span>🟣 Follow Instagram</span>
                <a href="{{insta}}" class="btn-go">GO (+5)</a>
            </div>

            <div class="task-item">
                <span>🔵 Watch Video Ad</span>
                <a href="https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b" class="btn-go">EARN (+10)</a>
            </div>
        </div>

        <div class="task-box" style="background: #121d2f; border-color: #58a6ff;">
            <span class="section-title" style="color: #fbbf24;">🚀 PRO TIP: SHARE & EARN</span>
            <p style="font-size: 13px; line-height: 1.4;">
                Aap upar diye gaye links ko apne doston ke sath share karein. Agar wo aapke link se video dekhte hain, toh aapko extra bonus milega! Profile videos share karne par ₹2 se ₹10 tak ka reward mil sakta hai.
            </p>
        </div>

        <p class="tip">Sabhi tasks poore karne ke baad 24 ghante mein points update hote hain.</p>
        <p style="font-size:10px; color:#484f58; margin-top:30px;">EarnPro Official Dashboard v3.0</p>
    </body>
    </html>
    """, pts=u['pts'], name=u['name'], yt=YT, insta=INSTA, fb=FB)
