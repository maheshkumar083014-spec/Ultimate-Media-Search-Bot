import os
import time
import uuid
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template_string
import telebot # Humne simple 'pyTelegramBotAPI' use kiya hai fast response ke liye

app = Flask(__name__)

# --- CONFIG ---
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
bot = telebot.TeleBot(TOKEN, threaded=False)

WELCOME_IMG = "https://i.ibb.co/39V9V4Y3/image.jpg" 
YT_LINK = "https://www.youtube.com/@USSoccerPulse"
INSTA_LINK = "https://www.instagram.com/digital_rockstar_m"
FB_LINK = "https://www.facebook.com/profile.php?id=61574378159053"
AD_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"

# --- FIREBASE ---
def init_fb():
    if not firebase_admin._apps:
        try:
            # TRY CATCH lagaya hai taaki agar key na mile toh bot crash na ho
            key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n').strip().strip('"').strip("'")
            if not key: return False
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": "ultimatemediasearch",
                "private_key": key,
                "client_email": "firebase-adminsdk-fbsvc@ultimatemediasearch.iam.gserviceaccount.com",
                "token_uri": "https://oauth2.googleapis.com/token",
            })
            firebase_admin.initialize_app(cred, {'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'})
            return True
        except: return False
    return True

# --- BOT HANDLERS ---
@app.route('/api', methods=['POST']) # Path change kiya /api par
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200
    return "Error", 403

@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.chat.id)
    name = message.from_user.first_name
    
    init_fb()
    try:
        user_ref = db.reference(f'users/{uid}')
        if not user_ref.get():
            user_ref.set({"name": name, "pts": 10, "coupon": str(uuid.uuid4())[:8], "last_ad": 0})
    except: pass

    # WEB APP BUTTON
    markup = telebot.types.InlineKeyboardMarkup()
    dash_url = f"https://ultimate-media-search-bot.vercel.app/dashboard?id={uid}&name={name}"
    markup.add(telebot.types.InlineKeyboardButton("🚀 Open Earning Dashboard", web_app=telebot.types.WebAppInfo(url=dash_url)))
    
    caption = f"✨ *Hello {name}!* ✨\n\n💪 'Zindagi mein koshish karne walon ki kabhi haar nahi hoti.'\n\n📊 Niche button par click karke earning shuru karein!"
    bot.send_photo(uid, WELCOME_IMG, caption=caption, parse_mode="Markdown", reply_markup=markup)

# --- DASHBOARD ---
@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    init_fb()
    try:
        u_ref = db.reference(f'users/{uid}')
        u_data = u_ref.get() or {"pts":0, "coupon":"..."}
    except: u_data = {"pts":0, "coupon":"Error"}

    if request.args.get('claim_ad') == '1':
        db.reference(f'users/{uid}').update({"pts": u_data.get('pts', 0) + 10, "last_ad": time.time()})
        return render_template_string("<script>alert('Points Added!'); window.location.href='/dashboard?id={{uid}}';</script>", uid=uid)

    return render_template_string("""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding:15px; margin:0; }
        .card { background:#1e293b; border-radius:15px; padding:20px; border:1px solid #334155; margin-bottom:15px; }
        .pts { font-size:45px; color:#fbbf24; font-weight:bold; }
        .task { background:#1e293b; padding:15px; border-radius:12px; margin-bottom:10px; display:flex; justify-content:space-between; text-decoration:none; color:white; border:1px solid #334155; }
    </style></head>
    <body>
        <div class="card">
            <p>My Points</p><div class="pts">{{pts}}</div>
            <p>Coupon: <b style="color:#fbbf24;">{{coupon}}</b></p>
        </div>
        <div style="text-align:left;">
            <a href="{{yt}}" class="task"><span><i class="fab fa-youtube" style="color:red;"></i> YouTube</span><b>+5</b></a>
            <a href="{{insta}}" class="task"><span><i class="fab fa-instagram" style="color:#e1306c;"></i> Instagram</span><b>+5</b></a>
            <a href="{{fb}}" class="task"><span><i class="fab fa-facebook" style="color:#1877f2;"></i> Facebook</span><b>+5</b></a>
            <div class="task" onclick="watchAd()" style="cursor:pointer;"><span><i class="fas fa-play" style="color:#fbbf24;"></i> Watch Ad (30s)</span><b id="adStatus">+10</b></div>
        </div>
        <script>
            function watchAd(){
                window.open("{{ad_link}}", "_blank");
                let s=30;
                let t = setInterval(()=>{
                    s--; document.getElementById('adStatus').innerHTML = s+"s";
                    if(s<=0){ clearInterval(t); window.location.href="/dashboard?id={{uid}}&claim_ad=1"; }
                },1000);
            }
        </script>
    </body></html>
    """, pts=u_data.get('pts',0), coupon=u_data.get('coupon','...'), uid=uid, yt=YT_LINK, insta=INSTA_LINK, fb=FB_LINK, ad_link=AD_LINK)

@app.route('/')
def index(): return "Bot is Active"
