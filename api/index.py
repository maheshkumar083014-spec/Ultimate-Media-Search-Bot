import os
import json
import uuid
from flask import Flask, request, render_template_string
import telebot
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)

# --- CONFIG ---
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
bot = telebot.TeleBot(TOKEN, threaded=False)

# Links & Assets
PIC = "https://i.ibb.co/39V9V4Y3/image.jpg"
YT = "https://www.youtube.com/@USSoccerPulse"
INSTA = "https://www.instagram.com/digital_rockstar_m"
AD_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"
BASE_URL = "https://ultimate-media-search-bot.vercel.app"

def init_fb():
    if not firebase_admin._apps:
        cred_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
        if cred_json:
            try:
                cred = credentials.Certificate(json.loads(cred_json))
                firebase_admin.initialize_app(cred, {'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'})
                return True
            except: return False
    return True

@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == "POST":
        update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
        if update.message:
            cid = str(update.message.chat.id)
            name = update.message.from_user.first_name or "User"
            if init_fb():
                ref = db.reference(f'users/{cid}')
                if not ref.get():
                    ref.set({"name": name, "pts": 10, "coupon": str(uuid.uuid4())[:8]})
            
            btn = telebot.types.InlineKeyboardMarkup()
            btn.add(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", web_app=telebot.types.WebAppInfo(url=f"{BASE_URL}/dashboard?id={cid}")))
            bot.send_photo(cid, PIC, caption=f"✨ Welcome {name}!\n\n💪 Zindagi mein koshish karne walon ki kabhi haar nahi hoti.\n\n💰 Earning shuru karein!", parse_mode="Markdown", reply_markup=btn)
    return "OK", 200

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    init_fb()
    u_data = db.reference(f'users/{uid}').get() or {"pts": 0, "coupon": "NEW"}
    
    if request.args.get('claim') == 'ad':
        db.reference(f'users/{uid}').update({"pts": u_data.get('pts', 0) + 10})
        return f"<script>alert('10 Pts Added!'); window.location.href='{AD_LINK}';</script>"

    return render_template_string("""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding:20px; }
        .card { background:#1e293b; border-radius:20px; padding:20px; border:1px solid #334155; margin-bottom:20px; }
        .pts { font-size:45px; color:#fbbf24; font-weight:bold; }
        .task { background:#1e293b; padding:15px; border-radius:12px; margin-bottom:10px; display:flex; justify-content:space-between; border:1px solid #334155; text-decoration:none; color:white; align-items:center; }
    </style></head><body>
        <div style="width:70px; height:70px; border-radius:50%; margin:auto; background:url('{{pic}}') center/cover; border:2px solid #fbbf24;"></div>
        <div class="card"><p>Points</p><div class="pts">{{pts}}</div><p>Coupon: {{coupon}}</p></div>
        <div style="text-align:left;">
            <a href="/dashboard?id={{uid}}&claim=ad" class="task"><div>📺 Watch Ad</div><b>+10</b></a>
            <a href="{{yt}}" class="task"><div><i class="fab fa-youtube"></i> YouTube</div><b>+5</b></a>
            <a href="{{insta}}" class="task"><div><i class="fab fa-instagram"></i> Instagram</div><b>+5</b></a>
        </div><br>
        <button onclick="alert('Min 1000 Pts')" style="background:#fbbf24; width:100%; padding:15px; border-radius:12px; border:none; font-weight:bold;">WITHDRAW</button>
    </body></html>
    """, pts=u_data.get('pts', 0), uid=uid, pic=PIC, yt=YT, insta=INSTA, coupon=u_data.get('coupon', '...'))
