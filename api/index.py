import os
import time
import uuid
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template_string
import telebot

app = Flask(__name__)

# --- CONFIG ---
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
bot = telebot.TeleBot(TOKEN, threaded=False)

WELCOME_IMG = "https://i.ibb.co/39V9V4Y3/image.jpg" 
YT_LINK = "https://www.youtube.com/@USSoccerPulse"
INSTA_LINK = "https://www.instagram.com/digital_rockstar_m"
FB_LINK = "https://www.facebook.com/profile.php?id=61574378159053"
AD_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"

def init_fb():
    if not firebase_admin._apps:
        try:
            key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n').strip().strip('"')
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": "ultimatemediasearch",
                "private_key": key,
                "client_email": "firebase-adminsdk-fbsvc@ultimatemediasearch.iam.gserviceaccount.com",
                "token_uri": "https://oauth2.googleapis.com/token",
            })
            firebase_admin.initialize_app(cred, {'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'})
        except: pass

@app.route('/api', methods=['POST'])
def webhook():
    if request.method == 'POST':
        update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
        bot.process_new_updates([update])
        return "!", 200
    return "OK", 200

@bot.message_handler(commands=['start'])
def start(message):
    uid, name = str(message.chat.id), message.from_user.first_name
    init_fb()
    try:
        u_ref = db.reference(f'users/{uid}')
        if not u_ref.get():
            u_ref.set({"name": name, "pts": 10, "coupon": str(uuid.uuid4())[:8], "last_ad": 0})
    except: pass

    kb = telebot.types.InlineKeyboardMarkup()
    dash_url = f"https://{request.host}/dashboard?id={uid}&name={name}"
    kb.add(telebot.types.InlineKeyboardButton("🚀 Open Earning Dashboard", web_app=telebot.types.WebAppInfo(url=dash_url)))
    bot.send_photo(uid, WELCOME_IMG, caption=f"✨ *Hello {name}!*", parse_mode="Markdown", reply_markup=kb)

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    init_fb()
    try:
        u_data = db.reference(f'users/{uid}').get() or {"pts":0, "coupon":"..."}
    except: u_data = {"pts":0, "coupon":"Error"}

    if request.args.get('claim_ad') == '1':
        db.reference(f'users/{uid}').update({"pts": u_data.get('pts', 0) + 10})
        return render_template_string("<script>alert('Points Added!'); window.location.href='/dashboard?id={{uid}}';</script>", uid=uid)

    return render_template_string("""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding:15px; margin:0; }
        .card { background:#1e293b; border-radius:15px; padding:20px; border:1px solid #334155; margin-bottom:15px; }
        .pts { font-size:45px; color:#fbbf24; font-weight:bold; }
        .task { background:#1e293b; padding:15px; border-radius:12px; margin-bottom:10px; display:flex; justify-content:space-between; text-decoration:none; color:white; border:1px solid #334155; align-items:center; }
    </style></head>
    <body>
        <div class="card">
            <p>My Points</p><div class="pts">{{pts}}</div>
            <p>Coupon: <b style="color:#fbbf24;">{{cp}}</b></p>
        </div>
        <div style="text-align:left;">
            <a href="{{yt}}" class="task"><span>YouTube</span><b>+5</b></a>
            <a href="{{insta}}" class="task"><span>Instagram</span><b>+5</b></a>
            <div class="task" onclick="location.href='/dashboard?id={{uid}}&claim_ad=1'"><span>Watch Ad</span><b>+10</b></div>
        </div>
    </body></html>
    """, pts=u_data.get('pts',0), cp=u_data.get('coupon','...'), uid=uid, yt=YT_LINK, insta=INSTA_LINK)

@app.route('/')
def home(): return "Active"
