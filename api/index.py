import os
import time
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template_string
from telegram import Update, Bot, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

app = Flask(__name__)

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = "8678211883" 
bot = Bot(token=TOKEN)

WELCOME_IMG = "https://i.ibb.co/zWJHms9p/image.jpg"
YT_LINK = "https://www.youtube.com/@USSoccerPulse"
INSTA_LINK = "https://www.instagram.com/digital_rockstar_m"
FB_LINK = "https://www.facebook.com/profile.php?id=61574378159053" # Updated Fixed Link

def init_fb():
    if not firebase_admin._apps:
        try:
            raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n').strip().strip('"').strip("'")
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": raw_key,
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
            })
            firebase_admin.initialize_app(cred, {'databaseURL': f'https://{os.getenv("FIREBASE_PROJECT_ID")}-default-rtdb.asia-southeast1.firebasedatabase.app/'})
        except: pass

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == "POST":
        try:
            update = Update.de_json(request.get_json(force=True), bot)
            if update.message and update.message.text:
                uid = str(update.message.chat_id)
                u_name = update.effective_user.first_name
                text = update.message.text

                init_fb()
                user_ref = db.reference(f'users/{uid}')
                user_data = user_ref.get()

                # Referral Security Logic
                if text.startswith('/start') and len(text) > 7:
                    ref_by = text.split()[1]
                    if not user_data and ref_by != uid:
                        r_ref = db.reference(f'users/{ref_by}')
                        r_data = r_ref.get() or {"pts": 0, "refs": 0}
                        r_ref.update({"pts": r_data.get('pts', 0) + 10, "refs": r_data.get('refs', 0) + 1})
                
                if not user_data:
                    user_ref.set({"name": u_name, "pts": 10, "refs": 0, "last_ad": 0})

                dash_url = f"https://{request.host}/dashboard?id={uid}&name={u_name}"
                kb = ReplyKeyboardMarkup([[KeyboardButton("📊 Open My Dashboard", web_app=WebAppInfo(url=dash_url))]], resize_keyboard=True)
                
                msg = (f"✨ *Assalam-o-Alaikum, {u_name}!* ✨\n\n"
                       f"🚀 *'Mushkilat se ghabrana nahi, kyunki sitare hamesha andhere mein hi chamakte hain.'*\n\n"
                       f"Aapka earning safar yahan se shuru hota hai. Tasks pure karein aur apne khwabon ko sach karein!\n\n"
                       f"👇 *Niche button dabayein:*")
                
                bot.send_photo(uid, WELCOME_IMG, caption=msg, parse_mode="Markdown", reply_markup=kb)
            return "ok", 200
        except: return "ok", 200
    return "Bot Active"

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    init_fb()
    u_ref = db.reference(f'users/{uid}')
    u_data = u_ref.get() or {"pts": 0, "refs": 0, "last_ad": 0}
    
    msg = ""
    # Security: 24h Ad Timer Validation
    if request.args.get('ad') == '1':
        now = time.time()
        if now - u_data.get('last_ad', 0) > 86400:
            u_ref.update({"pts": u_data['pts'] + 15, "last_ad": now})
            msg = "✅ Success! 15 points added to your wallet."
            u_data = u_ref.get()
        else:
            msg = "🕒 Security Alert: Ad available once every 24 hours!"

    if request.args.get('submit') == '1':
        phone, upi = request.args.get('phone'), request.args.get('upi')
        db.reference(f'withdrawals/{uid}').set({"name": name, "phone": phone, "upi": upi, "pts": u_data['pts']})
        bot.send_message(ADMIN_ID, f"💰 *WITHDRAWAL REQUEST*\n👤 User: {name}\n💳 UPI: {upi}\n📱 Phone: {phone}\n🪙 Pts: {u_data['pts']}")
        msg = "✅ Submission successful! Admin will review it."

    return render_template_string("""
    <!DOCTYPE html>
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background: #0b0e14; color: white; font-family: sans-serif; text-align: center; padding: 15px; }
        .card { background: #161b22; border-radius: 20px; padding: 20px; border: 1px solid #30363d; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
        .pts { font-size: 40px; color: #fbbf24; font-weight: bold; text-shadow: 0 0 10px rgba(251,191,36,0.3); }
        .btn { background: #fbbf24; color: black; padding: 12px; border-radius: 10px; width: 100%; border: none; font-weight: bold; margin-top: 10px; cursor: pointer; text-decoration:none; display:block;}
        .task { background: #21262d; padding: 12px; border-radius: 10px; margin-top: 10px; display: flex; justify-content: space-between; align-items: center; text-decoration: none; color: white; border: 1px solid #30363d; }
        .go-btn { background:#238636; padding:5px 12px; border-radius:6px; font-size:12px; font-weight:bold; }
    </style></head>
    <body>
        <div class="card">
            <p style="color: #8b949e; margin:0;">Available Balance</p>
            <div class="pts">{{pts}} pts</div>
            <p style="font-size:14px;">👥 Referrals: <b>{{refs}}</b></p>
            <button class="btn" onclick="document.getElementById('wbox').style.display='block'">💳 CLAIM WITHDRAW</button>
        </div>

        {% if msg %}<div style="background:rgba(251,191,36,0.1); padding:10px; border-radius:10px; margin:10px 0; color:#fbbf24; font-size:14px;">{{msg}}</div>{% endif %}

        <div id="wbox" style="display:none;" class="card">
            <form method="GET">
                <input type="hidden" name="id" value="{{uid}}"><input type="hidden" name="name" value="{{name}}"><input type="hidden" name="submit" value="1">
                <input type="number" name="phone" placeholder="WhatsApp Number" style="width:100%; padding:12px; margin:5px 0; border-radius:8px; border:1px solid #334155; background:#0b0e14; color:white;" required>
                <input type="text" name="upi" placeholder="Your UPI ID" style="width:100%; padding:12px; margin:5px 0; border-radius:8px; border:1px solid #334155; background:#0b0e14; color:white;" required>
                <button type="submit" class="btn" style="background:#238636; color:white;">Confirm Details</button>
            </form>
        </div>

        <div style="text-align:left; padding:5px;">
            <b style="color:#58a6ff; font-size:14px;">🎯 QUICK EARN TASKS</b>
            <a href="{{yt}}" target="_blank" class="task"><span>🔴 YouTube Subscribe</span> <span class="go-btn">GO +5</span></a>
            <a href="{{insta}}" target="_blank" class="task"><span>🟣 Instagram Follow</span> <span class="go-btn">GO +5</span></a>
            <a href="{{fb}}" target="_blank" class="task"><span>🔵 Facebook Page</span> <span class="go-btn">GO +5</span></a>
            
            <div id="adSection" class="task" style="cursor:pointer;" onclick="startAd()">
                <span>📺 Watch Ad (30s Security)</span>
                <span id="adStatus" style="background:#fbbf24; color:black; padding:5px 12px; border-radius:6px; font-size:12px; font-weight:bold;">WATCH</span>
            </div>
        </div>

        <script>
            function startAd() {
                let btn = document.getElementById('adStatus');
                let sec = 30;
                btn.parentElement.style.pointerEvents = "none";
                btn.style.background = "#444";
                let timer = setInterval(() => {
                    btn.innerHTML = sec + "s";
                    sec--;
                    if(sec < 0) {
                        clearInterval(timer);
                        window.location.href = "/dashboard?id={{uid}}&name={{name}}&ad=1";
                    }
                }, 1000);
            }
        </script>
    </body></html>
    """, pts=u_data['pts'], refs=u_data['refs'], uid=uid, name=name, yt=YT_LINK, insta=INSTA_LINK, fb=FB_LINK, msg=msg)
