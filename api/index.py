import os
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template_string
from telegram import Update, Bot, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

app = Flask(__name__)

# --- CONFIGURATION ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = "5802852969"  # Aapki Telegram ID (Screenshot se li gayi)
bot = Bot(token=TOKEN)

WELCOME_IMG = "https://i.ibb.co/zWJHms9p/image.jpg"
YT = "https://www.youtube.com/@USSoccerPulse"
FB = "https://www.facebook.com/61574378159053"
INSTA = "https://www.instagram.com/digital_rockstar_m"

# --- FIREBASE INITIALIZATION ---
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
        except Exception as e:
            print(f"Firebase Error: {e}")
            return False
    return True

# --- BOT WEBHOOK ---
@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == "POST":
        try:
            update = Update.de_json(request.get_json(force=True), bot)
            if update.message and update.message.text:
                chat_id = str(update.message.chat_id)
                user_name = update.effective_user.first_name
                
                init_fb()
                # Create user if not exists
                user_ref = db.reference(f'users/{chat_id}')
                if not user_ref.get():
                    user_ref.set({"name": user_name, "pts": 10, "refs": 0})

                dash_url = f"https://{request.host}/dashboard?id={chat_id}&name={user_name}"
                kb = ReplyKeyboardMarkup([[KeyboardButton("📊 Open Dashboard", web_app=WebAppInfo(url=dash_url))]], resize_keyboard=True)
                
                bot.send_photo(
                    chat_id, WELCOME_IMG, 
                    caption=f"🔥 *Assalam-o-Alaikum {user_name}!*\n\nAapka earning dashboard taiyar hai. Tasks poore karein aur points ko UPI mein withdraw karein!",
                    parse_mode="Markdown", reply_markup=kb
                )
            return "ok", 200
        except: return "ok", 200
    return "<h1>Bot is Active & Running!</h1>"

# --- SMART DASHBOARD ---
@app.route('/dashboard', methods=['GET'])
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    init_fb()

    # Success message logic
    status_msg = ""
    if request.args.get('submit') == '1':
        phone = request.args.get('phone')
        upi = request.args.get('upi')
        
        # Save to Firebase Withdrawals
        db.reference(f'withdrawals/{uid}').set({
            "name": name,
            "phone": phone,
            "upi": upi,
            "status": "Pending"
        })
        
        # Send Admin Alert
        try:
            bot.send_message(ADMIN_ID, f"💰 *NEW WITHDRAWAL*\n\n👤 User: {name}\n📱 Phone: {phone}\n💳 UPI: {upi}\n🆔 ID: {uid}", parse_mode="Markdown")
        except: pass
        status_msg = "✅ Details Submitted Successfully!"

    # Fetch Points
    user_data = db.reference(f'users/{uid}').get() or {"pts": 10, "refs": 0}
    pts = user_data.get('pts', 10)

    return render_template_string("""
    <!DOCTYPE html>
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background: #0b0e14; color: white; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; padding: 15px; margin: 0; }
        .card { background: linear-gradient(145deg, #161b22, #0d1117); border-radius: 20px; padding: 25px; border: 1px solid #30363d; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        .pts { font-size: 50px; color: #fbbf24; font-weight: bold; margin: 10px 0; text-shadow: 0 0 15px rgba(251, 191, 36, 0.3); }
        .task-box { background: #161b22; border-radius: 15px; padding: 15px; text-align: left; border: 1px solid #30363d; margin-top: 15px; }
        .btn-task { display: flex; justify-content: space-between; align-items: center; background: #21262d; padding: 12px; border-radius: 10px; margin-bottom: 10px; text-decoration: none; color: white; border: 1px solid #30363d; transition: 0.3s; }
        .btn-task:active { transform: scale(0.98); background: #30363d; }
        .go { background: #238636; padding: 6px 15px; border-radius: 8px; font-size: 13px; font-weight: bold; box-shadow: 0 0 10px rgba(35, 134, 54, 0.4); }
        .btn-main { background: #fbbf24; color: #000; padding: 15px; border-radius: 12px; display: block; text-decoration: none; font-weight: bold; margin-top: 15px; border: none; width: 100%; font-size: 16px; cursor: pointer; }
        input { width: 100%; padding: 14px; margin: 10px 0; border-radius: 10px; border: 1px solid #30363d; background: #0b0e14; color: white; box-sizing: border-box; font-size: 15px; }
        .form-panel { display: none; margin-top: 20px; background: #0d1117; padding: 20px; border-radius: 15px; border: 1px solid #fbbf24; animation: fadeIn 0.5s; }
        @keyframes fadeIn { from {opacity:0;} to {opacity:1;} }
        .success { color: #238636; background: rgba(35, 134, 54, 0.1); padding: 10px; border-radius: 10px; margin: 10px 0; font-weight: bold; }
    </style></head>
    <body>
        <div class="card">
            <p style="margin:0; color:#8b949e; font-size:14px; letter-spacing:1px;">MY TOTAL BALANCE</p>
            <div class="pts">{{pts}} pts</div>
            <button class="btn-main" onclick="document.getElementById('w-panel').style.display='block'">💰 CLAIM WITHDRAW</button>
        </div>

        {% if msg %}<div class="success">{{msg}}</div>{% endif %}

        <div id="w-panel" class="form-panel">
            <h3 style="margin-top:0; color:#fbbf24;">Withdrawal Form</h3>
            <form method="GET">
                <input type="hidden" name="id" value="{{uid}}">
                <input type="hidden" name="name" value="{{name}}">
                <input type="hidden" name="submit" value="1">
                <input type="number" name="phone" placeholder="WhatsApp Number" required>
                <input type="text" name="upi" placeholder="UPI ID (e.g. user@ybl)" required>
                <button type="submit" class="btn-main" style="background:#238636; color:white;">Submit to Admin</button>
            </form>
        </div>

        <div class="task-box">
            <b style="color:#58a6ff; font-size:14px;">🎯 DAILY HIGH PAYING TASKS</b><br><br>
            <a href="{{yt}}" class="btn-task"><span>🔴 Subscribe YouTube</span> <span class="go">GO +5</span></a>
            <a href="{{insta}}" class="btn-task"><span>🟣 Follow Instagram</span> <span class="go">GO +5</span></a>
            <a href="{{fb}}" class="btn-task"><span>🔵 Facebook Page</span> <span class="go">GO +5</span></a>
            <a href="https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b" class="btn-task"><span>📺 Watch & Earn</span> <span class="go">GO +10</span></a>
        </div>

        <div class="task-box" style="border-left: 4px solid #fbbf24; background: rgba(251,191,36,0.05);">
            <b style="color:#fbbf24;">🚀 EARNING TIP</b>
            <p style="font-size:13px; color:#8b949e; line-height:1.5; margin:5px 0;">Videos aur profiles ko doston ke sath share karein. Har valid visit par aapko bonus points milenge jo direct wallet mein add honge!</p>
        </div>
        
        <p style="font-size:11px; color:#30363d; margin-top:25px;">EarnPro v4.0 Ultimate Dashboard</p>
    </body></html>
    """, pts=pts, uid=uid, name=name, yt=YT, insta=INSTA, fb=FB, msg=status_msg)
