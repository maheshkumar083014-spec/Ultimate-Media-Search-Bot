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

# Links
WELCOME_IMG = "https://i.ibb.co/39V9V4Y3/image.jpg" 
YT_LINK = "https://www.youtube.com/@USSoccerPulse"
INSTA_LINK = "https://www.instagram.com/digital_rockstar_m"
FB_LINK = "https://www.facebook.com/profile.php?id=61574378159053"
AD_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"

# --- FIREBASE INITIALIZATION ---
def get_firebase():
    if not firebase_admin._apps:
        # Key ko handle karne ka sabse safe tarika
        key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n').strip().strip('"').strip("'")
        if key:
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": "ultimatemediasearch",
                "private_key": key,
                "client_email": "firebase-adminsdk-fbsvc@ultimatemediasearch.iam.gserviceaccount.com",
                "token_uri": "https://oauth2.googleapis.com/token",
            })
            firebase_admin.initialize_app(cred, {'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'})
    return True

# --- BOT ROUTES ---
@app.route('/api', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200
    return "Forbidden", 403

@bot.message_handler(commands=['start'])
def handle_start(message):
    uid = str(message.chat.id)
    name = message.from_user.first_name
    
    try:
        get_firebase()
        u_ref = db.reference(f'users/{uid}')
        if not u_ref.get():
            u_ref.set({"name": name, "pts": 10, "coupon": str(uuid.uuid4())[:8], "last_ad": 0})
    except Exception as e:
        print(f"DB Error: {e}")

    # Dashboard Button
    markup = telebot.types.InlineKeyboardMarkup()
    dash_url = f"https://ultimate-media-search-bot.vercel.app/dashboard?id={uid}&name={name}"
    markup.add(telebot.types.InlineKeyboardButton("🚀 Open Earning Dashboard", web_app=telebot.types.WebAppInfo(url=dash_url)))
    
    caption = f"✨ *Hello {name}!* ✨\n\n'Zindagi mein koshish karne walon ki kabhi haar nahi hoti.'\n\n📊 Niche button par click karke earning shuru karein!"
    bot.send_photo(uid, WELCOME_IMG, caption=caption, parse_mode="Markdown", reply_markup=markup)

# --- DASHBOARD ROUTES ---
@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    
    try:
        get_firebase()
        u_ref = db.reference(f'users/{uid}')
        data = u_ref.get() or {"pts": 0, "coupon": "...", "last_ad": 0}
    except:
        data = {"pts": 0, "coupon": "Error", "last_ad": 0}

    # Ad claim logic
    if request.args.get('claim_ad') == '1':
        new_pts = data.get('pts', 0) + 10
        db.reference(f'users/{uid}').update({"pts": new_pts, "last_ad": time.time()})
        return render_template_string("<script>alert('10 Points Added!'); window.location.href='/dashboard?id={{uid}}&name={{name}}';</script>", uid=uid, name=name)

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
            <div class="task" onclick="watchAd()" style="cursor:pointer;"><span><i class="fas fa-play" style="color:#fbbf24;"></i> Watch Ad</span><b id="adStatus">+10</b></div>
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
    """, pts=data.get('pts',0), coupon=data.get('coupon','...'), uid=uid, name=name, yt=YT_LINK, insta=INSTA_LINK, fb=FB_LINK, ad_link=AD_LINK)

@app.route('/')
def index():
    return "Bot is Active", 200
