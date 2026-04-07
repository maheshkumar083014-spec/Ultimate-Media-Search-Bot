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
            # Fixing the common Newline issue in Private Keys
            raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n').strip().strip('"').strip("'")
            cert_dict = {
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
            }
            cred = credentials.Certificate(cert_dict)
            firebase_admin.initialize_app(cred, {'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'})
        except Exception as e:
            return str(e)
    return None

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == "POST":
        try:
            data = request.get_json(force=True)
            update = Update.de_json(data, bot)
            if update.message and update.message.text:
                uid = str(update.message.chat_id)
                u_name = update.effective_user.first_name
                
                init_fb()
                user_ref = db.reference(f'users/{uid}')
                if not user_ref.get():
                    user_ref.set({"name": u_name, "pts": 10, "refs": 0, "last_ad": 0})

                dash_url = f"https://{request.host}/dashboard?id={uid}&name={u_name}"
                kb = ReplyKeyboardMarkup([[KeyboardButton("📊 Open Dashboard", web_app=WebAppInfo(url=dash_url))]], resize_keyboard=True)
                
                msg = f"✨ *Welcome {u_name}!*\n\n🚀 'Success is not final, failure is not fatal: it is the courage to continue that counts.'\n\nAbhi dashboard open karein aur earning shuru karein!"
                bot.send_photo(uid, WELCOME_IMG, caption=msg, parse_mode="Markdown", reply_markup=kb)
            return "ok", 200
        except Exception as e:
            return str(e), 200
    return "<h1>Bot is Online</h1>", 200

@app.route('/dashboard')
def dashboard():
    try:
        uid = request.args.get('id', '0')
        name = request.args.get('name', 'User')
        err = init_fb()
        if err: return f"Firebase Error: {err}"

        u_ref = db.reference(f'users/{uid}')
        u_data = u_ref.get() or {"pts": 0, "refs": 0, "last_ad": 0}
        
        msg = ""
        if request.args.get('ad') == '1':
            now = time.time()
            if now - u_data.get('last_ad', 0) > 86400:
                u_ref.update({"pts": u_data['pts'] + 15, "last_ad": now})
                msg = "✅ 15 Points Added!"
                u_data = u_ref.get()
            else:
                msg = "🕒 Try again after 24 hours!"

        return render_template_string("""
        <!DOCTYPE html>
        <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { background: #0f172a; color: white; font-family: sans-serif; text-align: center; padding: 10px; }
            .card { background: #1e293b; border-radius: 15px; padding: 20px; border: 1px solid #334155; margin-bottom: 10px; }
            .btn { background: #fbbf24; color: black; padding: 12px; border-radius: 8px; width: 100%; border: none; font-weight: bold; cursor: pointer; margin-top:10px; display:block; text-decoration:none; }
            .task { background: #161b22; padding: 12px; border-radius: 10px; margin-top: 10px; display: flex; justify-content: space-between; align-items: center; text-decoration: none; color: white; border: 1px solid #30363d; }
        </style></head>
        <body>
            <div class="card">
                <p>Balance</p><h1 style="color:#fbbf24; margin:0;">{{pts}} pts</h1>
                <p>Referrals: {{refs}}</p>
            </div>
            <p style="color:#fbbf24;">{{msg}}</p>
            <div style="text-align:left;">
                <a href="{{yt}}" class="task"><span>YouTube</span> <b>GO</b></a>
                <a href="{{insta}}" class="task"><span>Instagram</span> <b>GO</b></a>
                <a href="{{fb}}" class="task"><span>Facebook</span> <b>GO</b></a>
                <div class="task" onclick="startAd()" style="cursor:pointer;"><span id="adT">Watch Ad (30s)</span> <b>START</b></div>
            </div>
            <script>
                function startAd() {
                    let s = 30; let btn = document.getElementById('adT');
                    let t = setInterval(() => {
                        btn.innerHTML = "Wait: " + s + "s"; s--;
                        if(s<0){ clearInterval(t); window.location.href="/dashboard?id={{uid}}&name={{name}}&ad=1"; }
                    }, 1000);
                }
            </script>
        </body></html>
        """, pts=u_data['pts'], refs=u_data['refs'], uid=uid, name=name, yt=YT_LINK, insta=INSTA_LINK, fb=FB_LINK, msg=msg)
    except Exception as e:
        return f"App Error: {str(e)}"
