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

# --- FIREBASE SAFE INIT ---
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

# --- WEBHOOK ROUTES ---
@app.route('/api', methods=['POST', 'GET'])
def webhook():
    if request.method == 'POST':
        update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
        bot.process_new_updates([update])
        return "!", 200
    return "Bot Running", 200

@bot.message_handler(commands=['start'])
def welcome(message):
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
    
    caption = f"✨ *Hello {name}!* ✨\n\n'Zindagi mein koshish karne walon ki kabhi haar nahi hoti.'\n\n📊 Niche button par click karke earning shuru karein!"
    bot.send_photo(uid, WELCOME_IMG, caption=caption, parse_mode="Markdown", reply_markup=kb)

# --- DASHBOARD (SAB KUCH ISMEIN HAI) ---
@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    init_fb()
    try:
        u_ref = db.reference(f'users/{uid}')
        u_data = u_ref.get() or {"pts":0, "coupon":"...", "last_ad":0}
    except: u_data = {"pts":0, "coupon":"Error", "last_ad":0}

    # Ad Claim Logic
    if request.args.get('claim_ad') == '1':
        db.reference(f'users/{uid}').update({"pts": u_data.get('pts', 0) + 10, "last_ad": time.time()})
        return render_template_string("<script>alert('10 Points Added!'); window.location.href='/dashboard?id={{uid}}&name={{name}}';</script>", uid=uid, name=name)

    return render_template_string("""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding:15px; margin:0; }
        .card { background:linear-gradient(145deg, #1e293b, #0f172a); border-radius:15px; padding:20px; border:1px solid #334155; margin-bottom:15px; }
        .pts { font-size:45px; color:#fbbf24; font-weight:bold; }
        .task { background:#1e293b; padding:15px; border-radius:12px; margin-bottom:10px; display:flex; justify-content:space-between; text-decoration:none; color:white; border:1px solid #334155; align-items:center;}
        .icon-box { width:35px; height:35px; border-radius:8px; display:flex; align-items:center; justify-content:center; margin-right:12px; }
        .btn-withdraw { background:#fbbf24; color:black; padding:10px; border-radius:10px; width:100%; border:none; font-weight:bold; }
    </style></head>
    <body>
        <div class="card">
            <p style="opacity:0.7;">My Points</p>
            <div class="pts">{{pts}}</div>
            <button class="btn-withdraw">💳 WITHDRAW (100 MIN)</button>
            <p style="font-size:13px; margin-top:10px;">🎁 Coupon: <b style="color:#fbbf24;">{{coupon}}</b></p>
        </div>
        <div style="text-align:left;">
            <p style="font-size:12px; color:#94a3b8; font-weight:bold;">DAILY TASKS</p>
            <a href="{{yt}}" target="_blank" class="task"><div style="display:flex; align-items:center;"><div class="icon-box" style="background:red;"><i class="fab fa-youtube"></i></div>YouTube</div><b>+5</b></a>
            <a href="{{insta}}" target="_blank" class="task"><div style="display:flex; align-items:center;"><div class="icon-box" style="background:#e1306c;"><i class="fab fa-instagram"></i></div>Instagram</div><b>+5</b></a>
            <a href="{{fb}}" target="_blank" class="task"><div style="display:flex; align-items:center;"><div class="icon-box" style="background:#1877f2;"><i class="fab fa-facebook-f"></i></div>Facebook</div><b>+5</b></a>
            <div class="task" onclick="watchAd()" style="cursor:pointer;"><div style="display:flex; align-items:center;"><div class="icon-box" style="background:#fbbf24; color:black;"><i class="fas fa-play"></i></div>Watch Ad (30s)</div><b id="adStatus">+10</b></div>
            <a href="https://t.me/share/url?url=https://t.me/UltimateMediaSearchBot?start={{uid}}&text=Use my coupon: {{coupon}}" class="task" style="background:rgba(59,130,246,0.1); border-color:#3b82f6;"><div style="display:flex; align-items:center;"><div class="icon-box" style="background:#3b82f6;"><i class="fas fa-share-alt"></i></div>Share & Earn</div><b>+5</b></a>
        </div>
        <script>
            function watchAd(){
                window.open("{{ad_link}}", "_blank");
                let s=30;
                let t = setInterval(()=>{
                    s--; document.getElementById('adStatus').innerHTML = s+"s";
                    if(s<=0){ clearInterval(t); window.location.href="/dashboard?id={{uid}}&name={{name}}&claim_ad=1"; }
                },1000);
            }
        </script>
    </body></html>
    """, pts=u_data.get('pts',0), coupon=u_data.get('coupon','...'), uid=uid, name=name, yt=YT_LINK, insta=INSTA_LINK, fb=FB_LINK, ad_link=AD_LINK)

@app.route('/')
def home(): return "Bot Active"
