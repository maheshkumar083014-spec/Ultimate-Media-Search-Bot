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
FB_LINK = "https://www.facebook.com/profile.php?id=61574378159053"

# --- FIXED FIREBASE INIT ---
def init_fb():
    if not firebase_admin._apps:
        try:
            raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n').strip().strip('"').strip("'")
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": "ultimatemediasearch",
                "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": raw_key,
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
            })
            # DIRECT DATABASE URL (No more env dependency for URL)
            firebase_admin.initialize_app(cred, {'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'})
        except Exception as e:
            print(f"Firebase Error: {e}")

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == "POST":
        try:
            data = request.get_json(force=True)
            update = Update.de_json(data, bot)
            if update.message and update.message.text:
                uid = str(update.message.chat_id)
                u_name = update.effective_user.first_name
                text = update.message.text

                init_fb()
                user_ref = db.reference(f'users/{uid}')
                user_data = user_ref.get()

                # Referral Security
                if text.startswith('/start') and len(text) > 7:
                    ref_by = text.split()[1]
                    if not user_data and ref_by != uid:
                        r_ref = db.reference(f'users/{ref_by}')
                        r_data = r_ref.get() or {"pts": 0, "refs": 0}
                        r_ref.update({"pts": r_data.get('pts', 0) + 10, "refs": r_data.get('refs', 0) + 1})
                
                if not user_data:
                    user_ref.set({"name": u_name, "pts": 10, "refs": 0, "last_ad": 0})

                # DASHBOARD BUTTON
                dash_url = f"https://{request.host}/dashboard?id={uid}&name={u_name}"
                kb = ReplyKeyboardMarkup([[KeyboardButton("📊 My Dashboard", web_app=WebAppInfo(url=dash_url))]], resize_keyboard=True)
                
                hook_msg = (f"✨ *Assalam-o-Alaikum, {u_name}!* ✨\n\n"
                           f"🚀 *'Manzil unhi ko milti hai, jin ke sapno mein jaan hoti hai.'*\n\n"
                           f"Aapka safar shuru ho chuka hai! Rozana tasks pure karein aur points earn karein.\n\n"
                           f"👇 *Niche button dabayein aur dashboard check karein:*")
                
                bot.send_photo(uid, WELCOME_IMG, caption=hook_msg, parse_mode="Markdown", reply_markup=kb)
            return "ok", 200
        except: return "ok", 200
    return "Bot Engine Working"

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    init_fb()
    
    u_ref = db.reference(f'users/{uid}')
    u_data = u_ref.get() or {"pts": 0, "refs": 0, "last_ad": 0}
    
    msg = ""
    # Security: Ad Logic
    if request.args.get('ad') == '1':
        now = time.time()
        if now - u_data.get('last_ad', 0) > 86400:
            u_ref.update({"pts": u_data['pts'] + 15, "last_ad": now})
            msg = "✅ Success! 15 pts added."
            u_data = u_ref.get()
        else:
            msg = "🕒 Security: Once every 24h only!"

    if request.args.get('submit') == '1':
        phone, upi = request.args.get('phone'), request.args.get('upi')
        db.reference(f'withdrawals/{uid}').set({"name": name, "phone": phone, "upi": upi, "pts": u_data['pts']})
        bot.send_message(ADMIN_ID, f"💰 *NEW CLAIM*\nID: {uid}\nUPI: {upi}\nPhone: {phone}")
        msg = "✅ Claim Sent!"

    return render_template_string("""
    <!DOCTYPE html>
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background: #0f172a; color: white; font-family: sans-serif; text-align: center; padding: 15px; }
        .card { background: #1e293b; border-radius: 15px; padding: 20px; border: 1px solid #334155; margin-bottom: 15px; }
        .pts { font-size: 35px; color: #fbbf24; font-weight: bold; }
        .btn { background: #fbbf24; color: black; padding: 12px; border-radius: 10px; width: 100%; border: none; font-weight: bold; cursor: pointer; margin-top:10px; }
        .task { background: #161b22; padding: 12px; border-radius: 10px; margin-top: 10px; display: flex; justify-content: space-between; align-items: center; text-decoration: none; color: white; border: 1px solid #30363d; }
    </style></head>
    <body>
        <div class="card">
            <p style="margin:0; opacity:0.7;">Wallet Balance</p>
            <div class="pts">{{pts}} pts</div>
            <p>Referrals: {{refs}}</p>
            <button class="btn" onclick="document.getElementById('wbox').style.display='block'">💳 WITHDRAW</button>
        </div>
        {% if msg %}<p style="color:#fbbf24;">{{msg}}</p>{% endif %}
        <div id="wbox" style="display:none;" class="card">
            <form method="GET">
                <input type="hidden" name="id" value="{{uid}}"><input type="hidden" name="name" value="{{name}}"><input type="hidden" name="submit" value="1">
                <input type="text" name="phone" placeholder="Phone" style="width:90%; padding:10px; margin:5px;" required><br>
                <input type="text" name="upi" placeholder="UPI ID" style="width:90%; padding:10px; margin:5px;" required><br>
                <button type="submit" class="btn" style="background:#22c55e; color:white;">Submit</button>
            </form>
        </div>
        <div style="text-align:left;">
            <p style="color:#58a6ff;"><b>TASKS:</b></p>
            <a href="{{yt}}" target="_blank" class="task"><span>YouTube</span> <b style="color:#22c55e;">GO</b></a>
            <a href="{{insta}}" target="_blank" class="task"><span>Instagram</span> <b style="color:#22c55e;">GO</b></a>
            <a href="{{fb}}" target="_blank" class="task"><span>Facebook</span> <b style="color:#22c55e;">GO</b></a>
            <div class="task" onclick="startAd()" style="cursor:pointer;">
                <span id="adStatus">Watch Ad (30s)</span> <b style="color:#fbbf24;">START</b>
            </div>
        </div>
        <script>
            function startAd() {
                let s = 30; let btn = document.getElementById('adStatus');
                let t = setInterval(() => {
                    btn.innerHTML = "Security: " + s + "s"; s--;
                    if(s<0){ clearInterval(t); window.location.href="/dashboard?id={{uid}}&name={{name}}&ad=1"; }
                }, 1000);
            }
        </script>
    </body></html>
    """, pts=u_data['pts'], refs=u_data['refs'], uid=uid, name=name, yt=YT_LINK, insta=INSTA_LINK, fb=FB_LINK, msg=msg)
