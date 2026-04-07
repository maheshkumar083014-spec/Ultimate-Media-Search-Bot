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
    return "Bot Online", 200

@bot.message_handler(commands=['start'])
def start(message):
    uid, name = str(message.chat.id), message.from_user.first_name
    init_fb()
    try:
        u_ref = db.reference(f'users/{uid}')
        user = u_ref.get()
        if not user:
            u_ref.set({"name": name, "pts": 10, "coupon": str(uuid.uuid4())[:8]})
    except: pass

    kb = telebot.types.InlineKeyboardMarkup()
    # Direct Vercel App Link
    dash_url = f"https://ultimate-media-search-bot.vercel.app/dashboard?id={uid}&name={name}"
    kb.add(telebot.types.InlineKeyboardButton("🚀 Open Earning Dashboard", web_app=telebot.types.WebAppInfo(url=dash_url)))
    
    caption = f"✨ *Welcome {name}!* ✨\n\nAapka account activate ho gaya hai.\n\n🎁 *Signup Bonus:* 10 Points\n\nNiche dashboard se earning shuru karein!"
    bot.send_photo(uid, WELCOME_IMG, caption=caption, parse_mode="Markdown", reply_markup=kb)

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    init_fb()
    try:
        u_data = db.reference(f'users/{uid}').get() or {"pts":0, "coupon":"..."}
    except: u_data = {"pts":0, "coupon":"Error"}

    if request.args.get('claim_ad') == '1':
        db.reference(f'users/{uid}').update({"pts": u_data.get('pts', 0) + 10})
        return render_template_string("<script>alert('Points Claimed!'); window.location.href='/dashboard?id={{uid}}&name={{name}}';</script>", uid=uid, name=name)

    return render_template_string("""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding:15px; margin:0; }
        .card { background:rgba(30, 41, 59, 0.7); border-radius:20px; padding:25px; border:1px solid #334155; margin-bottom:20px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3); }
        .pts { font-size:50px; color:#fbbf24; font-weight:bold; margin-bottom:10px; }
        .btn-withdraw { background:#856404; color:#facc15; padding:12px; border-radius:12px; width:100%; border:none; font-weight:bold; font-size:16px; cursor:pointer; margin-bottom:15px; }
        .coupon-box { background:rgba(15, 23, 42, 0.5); padding:10px; border-radius:10px; border:1px dashed #fbbf24; font-size:14px; }
        .task-list { text-align:left; }
        .task { background:#1e293b; padding:16px; border-radius:15px; margin-bottom:12px; display:flex; justify-content:space-between; text-decoration:none; color:white; border:1px solid #334155; align-items:center; }
        .icon-text { display:flex; align-items:center; gap:12px; }
        .icon-wrap { width:35px; height:35px; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:18px; }
        .share-btn { background: #2563eb; border: none; }
    </style></head>
    <body>
        <div class="card">
            <p style="opacity:0.8; margin:0;">My Points</p>
            <div class="pts">{{pts}}</div>
            <button class="btn-withdraw">💳 WITHDRAW (100 MIN)</button>
            <div class="coupon-box">🎁 Coupon: <span style="color:#fbbf24; font-weight:bold;">{{coupon}}</span></div>
        </div>
        <div class="task-list">
            <p style="font-size:12px; color:#94a3b8; font-weight:bold; margin-bottom:10px;">DAILY TASKS</p>
            <a href="{{yt}}" class="task"><div class="icon-text"><div class="icon-wrap" style="background:#ef4444;"><i class="fab fa-youtube"></i></div>YouTube</div><b>+5</b></a>
            <a href="{{insta}}" class="task"><div class="icon-text"><div class="icon-wrap" style="background:#ec4899;"><i class="fab fa-instagram"></i></div>Instagram</div><b>+5</b></a>
            <a href="{{fb}}" class="task"><div class="icon-text"><div class="icon-wrap" style="background:#3b82f6;"><i class="fab fa-facebook"></i></div>Facebook</div><b>+5</b></a>
            <div class="task" onclick="watchAd()" style="cursor:pointer;"><div class="icon-text"><div class="icon-wrap" style="background:#f59e0b;"><i class="fas fa-play"></i></div>Watch Ad (30s)</div><b id="adStatus">+10</b></div>
            <a href="https://t.me/share/url?url=https://t.me/UltimateMediaSearchBot?start={{uid}}" class="task share-btn"><div class="icon-text"><div class="icon-wrap" style="background:#ffffff20;"><i class="fas fa-share-alt"></i></div>Share & Earn</div><b>+5</b></a>
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
def home(): return "Active"
