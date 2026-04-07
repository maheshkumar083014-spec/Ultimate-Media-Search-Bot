import os
import json
import uuid
from flask import Flask, request, render_template_string
import telebot
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)

# --- CONFIGURATION (SECURE) ---
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
bot = telebot.TeleBot(TOKEN, threaded=False)

# Links & Assets
PROFILE_PHOTO_URL = "https://i.ibb.co/39V9V4Y3/image.jpg"
YT_LINK = "https://www.youtube.com/@USSoccerPulse"
INSTA_LINK = "https://www.instagram.com/digital_rockstar_m"
FB_LINK = "https://www.facebook.com/profile.php?id=61574378159053"
AD_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"
DASHBOARD_BASE_URL = "https://ultimate-media-search-bot.vercel.app"

# Motivation Quotes Logic
MOTIVATION = "💪 Zindagi mein koshish karne walon ki kabhi haar nahi hoti. Aaj ki mehnat kal ka sukoon hai!"

# --- FIREBASE INITIALIZATION ---
def init_fb():
    if not firebase_admin._apps:
        cred_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
        if cred_json:
            try:
                cred_dict = json.loads(cred_json)
                firebase_admin.initialize_app(credentials.Certificate(cred_dict), {
                    'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
                })
                return True
            except: return False
    return True

# --- BOT WEBHOOK HANDLER ---
@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == "POST":
        update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
        if update.message:
            msg = update.message
            chat_id = str(msg.chat.id)
            u_name = msg.from_user.first_name or "User"

            # 1. User Data Security Check & Signup
            if init_fb():
                user_ref = db.reference(f'users/{chat_id}')
                if not user_ref.get():
                    user_ref.set({
                        "name": u_name,
                        "pts": 10, # Welcome Bonus
                        "coupon": str(uuid.uuid4())[:8],
                        "joined": True
                    })

            # 2. Welcome Message with Photo & Motivation
            markup = telebot.types.InlineKeyboardMarkup()
            dash_url = f"{DASHBOARD_BASE_URL}/dashboard?id={chat_id}&name={u_name}"
            markup.add(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", web_app=telebot.types.WebAppInfo(url=dash_url)))
            
            welcome_text = (
                f"✨ *Welcome {u_name}!* ✨\n\n"
                f"{MOTIVATION}\n\n"
                f"📊 *Earning:* Ads dekhein aur social tasks poore karein.\n"
                f"💰 *Bonus:* Aapko 10 points mil chuke hain!"
            )
            
            try:
                bot.send_photo(chat_id, PROFILE_PHOTO_URL, caption=welcome_text, parse_mode="Markdown", reply_markup=markup)
            except:
                bot.send_message(chat_id, welcome_text, parse_mode="Markdown", reply_markup=markup)
                
    return "Bot is Running", 200

# --- DASHBOARD UI & MONETIZATION LOGIC ---
@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    init_fb()
    u_ref = db.reference(f'users/{uid}')
    u_data = u_ref.get() or {"pts": 0, "coupon": "NEW"}

    # Points Increment Logic (Secure)
    if request.args.get('claim') == 'ad':
        current_pts = u_data.get('pts', 0)
        u_ref.update({"pts": current_pts + 10})
        return f"<script>alert('10 Points Added for Watching Ad!'); window.location.href='{AD_LINK}';</script>"

    return render_template_string("""
    <!DOCTYPE html><html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding:15px; margin:0; }
        .card { background:#1e293b; border-radius:15px; padding:20px; border:1px solid #334155; margin-bottom:15px; }
        .pts { font-size:45px; color:#fbbf24; font-weight:bold; }
        .btn-main { background:#fbbf24; color:black; padding:12px; border-radius:10px; width:100%; border:none; font-weight:bold; margin-top:10px; cursor:pointer; text-decoration:none; display:block; }
        .task { background:#1e293b; padding:12px; border-radius:10px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center; border:1px solid #334155; text-decoration:none; color:white; }
        .icon { width:30px; height:30px; border-radius:5px; display:flex; align-items:center; justify-content:center; }
    </style></head>
    <body>
        <div style="width:70px; height:70px; border-radius:50%; border:2px solid #fbbf24; margin:10px auto; background:url('{{pic}}') center/cover;"></div>
        <div class="card">
            <p style="color:#94a3b8;">Wallet Balance</p>
            <div class="pts">{{pts}}</div>
            <p style="font-size:12px;">ID: {{uid}} | Coupon: {{coupon}}</p>
        </div>
        <div style="text-align:left;">
            <p style="font-size:12px; color:#94a3b8;">EARN MORE POINTS</p>
            <a href="/dashboard?id={{uid}}&claim=ad" class="task">
                <div style="display:flex; align-items:center;"><div class="icon" style="background:#fbbf24; color:black;"><i class="fas fa-play"></i></div>&nbsp; Watch Video Ad</div>
                <b style="color:#fbbf24;">+10</b>
            </a>
            <a href="{{yt}}" target="_blank" class="task">
                <div style="display:flex; align-items:center;"><div class="icon" style="background:#ef4444;"><i class="fab fa-youtube"></i></div>&nbsp; YouTube Subscribe</div>
                <b>+5</b>
            </a>
            <a href="{{insta}}" target="_blank" class="task">
                <div style="display:flex; align-items:center;"><div class="icon" style="background:#e1306c;"><i class="fab fa-instagram"></i></div>&nbsp; Follow Instagram</div>
                <b>+5</b>
            </a>
        </div>
        <button class="btn-main" onclick="alert('Min withdraw 1000 points')">💳 WITHDRAW NOW</button>
    </body></html>
    """, pts=u_data.get('pts', 0), uid=uid, name=name, pic=PROFILE_PHOTO_URL, yt=YT_LINK, insta=INSTA_LINK, coupon=u_data.get('coupon', '...'))

app = app
