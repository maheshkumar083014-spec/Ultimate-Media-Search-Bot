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

# Social Links
YT = "https://www.youtube.com/@USSoccerPulse"
FB = "https://www.facebook.com/61574378159053"
INSTA = "https://www.instagram.com/digital_rockstar_m"

# --- SAFE FIREBASE INIT ---
def init_fb():
    if not firebase_admin._apps:
        try:
            raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n').strip().strip('"').strip("'")
            if not raw_key: return False
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
                
                # Try saving to Firebase but don't stop if it fails
                if init_fb():
                    try:
                        db.reference(f'users/{chat_id}').update({"name": user_name})
                    except: pass

                dash_url = f"https://{request.host}/dashboard?id={chat_id}&name={user_name}"
                kb = ReplyKeyboardMarkup([[KeyboardButton("📊 Dashboard", web_app=WebAppInfo(url=dash_url))]], resize_keyboard=True)
                
                bot.send_photo(
                    chat_id, WELCOME_IMG, 
                    caption=f"🔥 *Welcome {user_name}!*\n\nBot active hai. Niche diye gaye Dashboard button se apni earning aur tasks check karein.",
                    parse_mode="Markdown", reply_markup=kb
                )
            return "ok", 200
        except: return "ok", 200
    return "Bot is Active"

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    
    # Default data agar Firebase na chale
    pts, refs = 10, 0
    if init_fb():
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
        .card { background: linear-gradient(145deg, #1e293b, #0f172a); border-radius: 20px; padding: 20px; border: 1px solid #334155; margin-bottom: 20px; }
        .pts { font-size: 40px; color: #fbbf24; font-weight: bold; }
        .task-box { background: #161b22; border-radius: 15px; padding: 15px; text-align: left; border: 1px solid #30363d; margin-top: 15px; }
        .btn-task { display: flex; justify-content: space-between; align-items: center; background: #21262d; padding: 12px; border-radius: 10px; margin-bottom: 10px; text-decoration: none; color: white; border: 1px solid #30363d; }
        .go { background: #238636; padding: 5px 12px; border-radius: 6px; font-size: 12px; }
    </style></head>
    <body>
        <div class="card">
            <p style="margin:0; color:#94a3b8;">{{name}}'s Balance</p>
            <div class="pts">{{pts}} pts</div>
            <p style="margin:0; font-size:12px;">Referrals: {{refs}}</p>
        </div>
        <div class="task-box">
            <b style="color:#58a6ff;">🎯 DAILY TASKS</b><br><br>
            <a href="{{yt}}" class="btn-task"><span>🔴 YouTube Subscribe</span> <span class="go">GO +5</span></a>
            <a href="{{insta}}" class="btn-task"><span>🟣 Instagram Follow</span> <span class="go">GO +5</span></a>
            <a href="{{fb}}" class="btn-task"><span>🔵 Facebook Page</span> <span class="go">GO +5</span></a>
        </div>
        <div class="task-box" style="border-left: 4px solid #fbbf24;">
            <b style="color:#fbbf24;">💰 EARNING TIP</b>
            <p style="font-size:13px; color:#cbd5e1;">Aap hamari profiles aur videos ko share karke bhi points kama sakte hain. Har valid share par extra bonus milega!</p>
        </div>
    </body></html>
    """, pts=pts, refs=refs, name=name, yt=YT, insta=INSTA, fb=FB)
