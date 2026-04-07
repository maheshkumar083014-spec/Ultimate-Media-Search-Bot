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

def init_fb():
    if not firebase_admin._apps:
        try:
            # Cleaning the Private Key (Very Important for Vercel)
            raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n').strip().strip('"').strip("'")
            
            # Structuring the Credentials
            cert_config = {
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
            }
            
            cred = credentials.Certificate(cert_config)
            firebase_admin.initialize_app(cred, {
                'databaseURL': f'https://{os.getenv("FIREBASE_PROJECT_ID")}-default-rtdb.asia-southeast1.firebasedatabase.app/'
            })
            return True
        except Exception as e:
            print(f"Init Error: {e}")
            return False
    return True

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == "POST":
        try:
            data = request.get_json(force=True)
            update = Update.de_json(data, bot)
            if update.message and update.message.text:
                uid = str(update.message.chat_id)
                u_name = update.effective_user.first_name
                
                if init_fb():
                    user_ref = db.reference(f'users/{uid}')
                    if not user_ref.get():
                        user_ref.set({"name": u_name, "pts": 10, "refs": 0, "last_ad": 0})

                dash_url = f"https://{request.host}/dashboard?id={uid}&name={u_name}"
                kb = ReplyKeyboardMarkup([[KeyboardButton("📊 My Dashboard", web_app=WebAppInfo(url=dash_url))]], resize_keyboard=True)
                
                msg = (f"✨ *Assalam-o-Alaikum, {u_name}!* ✨\n\n"
                       f"🚀 *'Hausle buland kar, manzil tere kareeb hai.'*\n\n"
                       f"Dashboard open karein aur apna gift claim karein!")
                
                bot.send_photo(uid, WELCOME_IMG, caption=msg, parse_mode="Markdown", reply_markup=kb)
            return "ok", 200
        except: return "ok", 200
    return "Bot Online", 200

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    
    # Check if Firebase Connected
    if not init_fb():
        return "<h3>⚠️ Configuration Error: Please check your Firebase Keys in Vercel.</h3>"

    try:
        u_ref = db.reference(f'users/{uid}')
        u_data = u_ref.get() or {"pts": 0, "refs": 0, "last_ad": 0}
        
        msg = ""
        # Ad Timer Logic
        if request.args.get('ad') == '1':
            now = time.time()
            if now - u_data.get('last_ad', 0) > 86400:
                u_ref.update({"pts": u_data['pts'] + 15, "last_ad": now})
                msg = "✅ Points Earned!"
                u_data = u_ref.get()
            else:
                msg = "🕒 Wait for 24 hours!"

        return render_template_string("""
        <!DOCTYPE html>
        <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { background: #0b0e14; color: white; font-family: sans-serif; text-align: center; padding: 15px; }
            .card { background: #161b22; border-radius: 20px; padding: 20px; border: 1px solid #30363d; margin-bottom: 15px; }
            .pts { font-size: 40px; color: #fbbf24; font-weight: bold; }
            .btn { background: #fbbf24; color: black; padding: 12px; border-radius: 10px; width: 100%; border: none; font-weight: bold; margin-top: 10px; cursor: pointer; display:block; text-decoration:none;}
            .task { background: #21262d; padding: 12px; border-radius: 10px; margin-top: 10px; display: flex; justify-content: space-between; align-items: center; text-decoration: none; color: white; border: 1px solid #30363d; }
        </style></head>
        <body>
            <div class="card">
                <p style="opacity:0.6;">Wallet Balance</p>
                <div class="pts">{{pts}} pts</div>
                <p>Referrals: <b>{{refs}}</b></p>
                <a href="#" class="btn" onclick="alert('Withdraw logic working!')">💳 CLAIM MONEY</a>
            </div>
            {% if msg %}<p style="color:#fbbf24;">{{msg}}</p>{% endif %}
            <div style="text-align:left;">
                <b>🚀 TASKS</b>
                <a href="{{yt}}" target="_blank" class="task"><span>YouTube Subscribe</span> <b style="color:#238636;">GO</b></a>
                <a href="{{insta}}" target="_blank" class="task"><span>Instagram Follow</span> <b style="color:#238636;">GO</b></a>
                <a href="{{fb}}" target="_blank" class="task"><span>Facebook Page</span> <b style="color:#238636;">GO</b></a>
                <div class="task" onclick="startAd()" style="cursor:pointer;"><span id="adT">Watch Ad (30s)</span> <b style="color:#fbbf24;">START</b></div>
            </div>
            <script>
                function startAd() {
                    let s = 30; let btn = document.getElementById('adT');
                    btn.parentElement.style.pointerEvents = "none";
                    let t = setInterval(() => {
                        btn.innerHTML = "Security Check: " + s + "s"; s--;
                        if(s<0){ clearInterval(t); window.location.href="/dashboard?id={{uid}}&name={{name}}&ad=1"; }
                    }, 1000);
                }
            </script>
        </body></html>
        """, pts=u_data['pts'], refs=u_data['refs'], uid=uid, name=name, yt=YT_LINK, insta=INSTA_LINK, fb=FB_LINK, msg=msg)
    except Exception as e:
        return f"Database Error: {str(e)}"
