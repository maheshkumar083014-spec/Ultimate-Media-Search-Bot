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

# --- FIREBASE FIXED INIT ---
def init_fb():
    if not firebase_admin._apps:
        try:
            # Vercel se key uthana aur format theek karna
            raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "")
            
            # Ye line saari formatting problems solve kar degi
            key = raw_key.replace('\\n', '\n').strip().strip('"').strip("'")
            
            if not key:
                print("Error: FIREBASE_PRIVATE_KEY is empty in Vercel Settings!")
                return False

            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": "ultimatemediasearch",
                "private_key": key,
                "client_email": "firebase-adminsdk-fbsvc@ultimatemediasearch.iam.gserviceaccount.com",
                "token_uri": "https://oauth2.googleapis.com/token",
            })
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
            })
            return True
        except Exception as e:
            print(f"Firebase Fatal Error: {e}")
            return False
    return True

@app.route('/api', methods=['POST', 'GET'])
def webhook():
    if request.method == 'POST':
        try:
            json_str = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_str)
            bot.process_new_updates([update])
        except: pass
        return "!", 200
    return "Bot is Running", 200

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
    dash_url = f"https://ultimate-media-search-bot.vercel.app/dashboard?id={uid}&name={name}"
    kb.add(telebot.types.InlineKeyboardButton("🚀 Open Earning Dashboard", web_app=telebot.types.WebAppInfo(url=dash_url)))
    
    bot.send_photo(uid, WELCOME_IMG, caption=f"✨ *Hello {name}!*\n\nAaj ki earning shuru karein!", parse_mode="Markdown", reply_markup=kb)

@app.route('/dashboard')
def dashboard():
    uid, name = request.args.get('id', '0'), request.args.get('name', 'User')
    init_fb()
    
    # Points fetch karne ki koshish
    try:
        u_data = db.reference(f'users/{uid}').get()
        pts = u_data.get('pts', 0) if u_data else 0
        cp = u_data.get('coupon', '...') if u_data else "..."
    except:
        pts, cp = "Error", "Firebase Key Issue"

    if request.args.get('claim_ad') == '1':
        try:
            db.reference(f'users/{uid}').update({"pts": (pts if isinstance(pts, int) else 0) + 10})
            return render_template_string("<script>alert('Points Added!'); window.location.href='/dashboard?id={{uid}}&name={{name}}';</script>", uid=uid, name=name)
        except: pass

    return render_template_string("""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding:15px; margin:0; }
        .card { background:linear-gradient(145deg, #1e293b, #0f172a); border-radius:15px; padding:20px; border:1px solid #334155; margin-bottom:15px; }
        .pts { font-size:45px; color:#fbbf24; font-weight:bold; }
        .task { background:#1e293b; padding:15px; border-radius:12px; margin-bottom:10px; display:flex; justify-content:space-between; text-decoration:none; color:white; border:1px solid #334155; align-items:center;}
    </style></head>
    <body>
        <div class="card">
            <p>My Points</p><div class="pts">{{pts}}</div>
            <p>Coupon: <b style="color:#fbbf24;">{{cp}}</b></p>
        </div>
        <div style="text-align:left;">
            <a href="{{yt}}" target="_blank" class="task"><span><i class="fab fa-youtube" style="color:red;"></i> YouTube</span><b>+5</b></a>
            <a href="{{fb}}" target="_blank" class="task"><span><i class="fab fa-facebook" style="color:#1877f2;"></i> Facebook</span><b>+5</b></a>
            <div class="task" onclick="location.href='/dashboard?id={{uid}}&name={{name}}&claim_ad=1'" style="cursor:pointer;"><span><i class="fas fa-play" style="color:#fbbf24;"></i> Watch Ad</span><b>+10</b></div>
        </div>
    </body></html>
    """, pts=pts, cp=cp, uid=uid, name=name, yt=YT_LINK, fb=FB_LINK)

@app.route('/')
def home(): return "Bot Active"
