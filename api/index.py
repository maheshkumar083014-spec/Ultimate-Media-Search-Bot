import os
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template_string
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

app = Flask(__name__)

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
WELCOME_IMG = "https://i.ibb.co/zWJHms9p/image.jpg"
YT = "https://www.youtube.com/@USSoccerPulse"
FB = "https://www.facebook.com/61574378159053"
INSTA = "https://www.instagram.com/digital_rockstar_m"

def init_fb():
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
        except: return False
    return True

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == "POST":
        try:
            update = Update.de_json(request.get_json(force=True), bot)
            if update.message and update.message.text:
                chat_id = str(update.message.chat_id)
                user_name = update.effective_user.first_name
                
                init_fb()
                try: db.reference(f'users/{chat_id}').update({"name": user_name})
                except: pass

                # IMPORTANT: Yahan URL ke piche /dashboard lagana zaroori hai
                dash_url = f"https://{request.host}/dashboard?id={chat_id}&name={user_name}"
                
                kb = ReplyKeyboardMarkup([[KeyboardButton("📊 Dashboard", web_app=WebAppInfo(url=dash_url))]], resize_keyboard=True)
                
                bot.send_photo(
                    chat_id, WELCOME_IMG, 
                    caption=f"🔥 *Welcome {user_name}!*\n\nBot active hai. Niche Dashboard button se apni earning aur tasks check karein.",
                    parse_mode="Markdown", reply_markup=kb
                )
            return "ok", 200
        except: return "ok", 200
    return "<h1>Bot Engine is Running...</h1>"

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    pts, refs = 10, 0
    
    init_fb()
    try:
        u = db.reference(f'users/{uid}').get()
        if u:
            pts = u.get('pts', 10)
            refs = u.get('refs', 0)
    except: pass

    return render_template_string("""
    <!DOCTYPE html>
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background: #0f172a; color: white; font-family: sans-serif; text-align: center; padding: 15px; margin: 0; }
        .card { background: linear-gradient(145deg, #1e293b, #0f172a); border-radius: 20px; padding: 20px; border: 1px solid #334155; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        .pts { font-size: 40px; color: #fbbf24; font-weight: bold; margin: 5px 0; }
        .task-box { background: #161b22; border-radius: 15px; padding: 15px; text-align: left; border: 1px solid #30363d; margin-top: 15px; }
        .btn-task { display: flex; justify-content: space-between; align-items: center; background: #21262d; padding: 12px; border-radius: 10px; margin-bottom: 10px; text-decoration: none; color: white; border: 1px solid #30363d; font-size: 14px; }
        .go { background: #238636; padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: bold; }
        .section-title { color: #58a6ff; font-size: 14px; font-weight: bold; margin-bottom: 10px; display: block; }
    </style></head>
    <body>
        <div class="card">
            <p style="margin:0; color:#94a3b8; font-size:14px;">Total Earning</p>
            <div class="pts">{{pts}} pts</div>
            <p style="margin:0; font-size:12px; color:#10b981;">User ID: {{uid}} | Refs: {{refs}}</p>
        </div>

        <div class="task-box">
            <span class="section-title">🎯 DAILY EARNING TASKS</span>
            <a href="{{yt}}" class="btn-task"><span>🔴 Subscribe YouTube</span> <span class="go">GO +5</span></a>
            <a href="{{insta}}" class="btn-task"><span>🟣 Instagram Follow</span> <span class="go">GO +5</span></a>
            <a href="{{fb}}" class="btn-task"><span>🔵 Facebook Page</span> <span class="go">GO +5</span></a>
            <a href="https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b" class="btn-task"><span>📺 Watch Video Ad</span> <span class="go">GO +10</span></a>
        </div>

        <div class="task-box" style="border-left: 4px solid #fbbf24; background: #121d2f;">
            <b style="color:#fbbf24;">💰 PROFIT TRICK</b>
            <p style="font-size:13px; color:#cbd5e1; line-height:1.4;">Hamare social media profiles ke videos ko doston ke sath share karein. Share karne par aapko direct cashback aur points milenge!</p>
        </div>
        
        <p style="font-size:10px; color:#484f58; margin-top:20px;">EarnPro v3.1 Official Dashboard</p>
    </body></html>
    """, pts=pts, refs=refs, name=name, uid=uid, yt=YT, insta=INSTA, fb=FB)
