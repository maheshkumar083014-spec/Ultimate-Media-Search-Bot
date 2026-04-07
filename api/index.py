import os
import time
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template_string
from telegram import Update, Bot, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

app = Flask(__name__)

# --- BOT CONFIG ---
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
ADMIN_ID = "8678211883" 
bot = Bot(token=TOKEN)

WELCOME_IMG = "https://i.ibb.co/zWJHms9p/image.jpg"
YT_LINK = "https://www.youtube.com/@USSoccerPulse"
INSTA_LINK = "https://www.instagram.com/digital_rockstar_m"
FB_LINK = "https://www.facebook.com/profile.php?id=61574378159053"

def init_fb():
    if not firebase_admin._apps:
        try:
            # Formatting Private Key to handle Vercel's newline issue
            p_key = os.getenv("FIREBASE_PRIVATE_KEY", "")
            if "\\n" in p_key:
                p_key = p_key.replace("\\n", "\n")
            
            # Manual dictionary construction to avoid hidden character issues
            service_account_info = {
                "type": "service_account",
                "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": p_key.strip().strip('"').strip("'"),
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
            }
            
            cred = credentials.Certificate(service_account_info)
            # Hardcoded Database URL for your specific project
            db_url = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"
            firebase_admin.initialize_app(cred, {'databaseURL': db_url})
            return True
        except Exception as e:
            print(f"Firebase Init Error: {e}")
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
                
                init_fb() # Start Firebase
                user_ref = db.reference(f'users/{uid}')
                if not user_ref.get():
                    user_ref.set({"name": u_name, "pts": 10, "refs": 0, "last_ad": 0})

                dash_url = f"https://{request.host}/dashboard?id={uid}&name={u_name}"
                kb = ReplyKeyboardMarkup([[KeyboardButton("📊 Open Dashboard", web_app=WebAppInfo(url=dash_url))]], resize_keyboard=True)
                
                msg = f"🌟 *Aadab {u_name}!*\n\nAapka account active ho gaya hai. Dashboard se earning shuru karein!"
                bot.send_photo(uid, WELCOME_IMG, caption=msg, parse_mode="Markdown", reply_markup=kb)
            return "ok", 200
        except Exception as e:
            return str(e), 200
    return "<h1>Bot Engine is Running</h1>", 200

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    
    if not init_fb():
        return "<h3>❌ Configuration Error: Firebase keys mismatch. Check Vercel Env Vars.</h3>"

    try:
        u_ref = db.reference(f'users/{uid}')
        u_data = u_ref.get() or {"pts": 0, "refs": 0, "last_ad": 0}
        
        msg = ""
        if request.args.get('ad') == '1':
            now = time.time()
            if now - u_data.get('last_ad', 0) > 86400:
                u_ref.update({"pts": u_data['pts'] + 15, "last_ad": now})
                msg = "✅ Bonus: +15 Points added!"
                u_data = u_ref.get()
            else:
                msg = "🕒 Security: Only 1 Ad allowed per 24 hours."

        return render_template_string("""
        <!DOCTYPE html>
        <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { background: #0d1117; color: white; font-family: -apple-system, sans-serif; text-align: center; padding: 15px; }
            .card { background: #161b22; border: 1px solid #30363d; border-radius: 15px; padding: 25px; margin-bottom: 20px; }
            .pts { font-size: 45px; color: #f2bc1b; font-weight: bold; margin: 10px 0; }
            .btn { background: #f2bc1b; color: black; padding: 14px; border-radius: 10px; width: 100%; border: none; font-weight: bold; cursor: pointer; text-decoration: none; display: block; margin-top: 10px; }
            .task { background: #21262d; border: 1px solid #30363d; padding: 15px; border-radius: 12px; margin-top: 10px; display: flex; justify-content: space-between; align-items: center; color: white; text-decoration: none; }
            .badge { background: #238636; padding: 4px 10px; border-radius: 5px; font-size: 12px; }
        </style></head>
        <body>
            <div class="card">
                <p style="margin:0; opacity:0.7;">Current Balance</p>
                <div class="pts">{{pts}}</div>
                <p>Total Referrals: {{refs}}</p>
                <a href="#" class="btn" onclick="alert('Minimum withdrawal: 1000 pts')">💰 WITHDRAWAL</a>
            </div>
            {% if msg %}<p style="color:#f2bc1b;">{{msg}}</p>{% endif %}
            <div style="text-align:left;">
                <p style="color:#8b949e; font-weight:bold; margin-left:5px;">EARNING TASKS</p>
                <a href="{{yt}}" target="_blank" class="task"><span>Subscribe YouTube</span> <span class="badge">OPEN</span></a>
                <a href="{{insta}}" target="_blank" class="task"><span>Follow Instagram</span> <span class="badge">OPEN</span></a>
                <a href="{{fb}}" target="_blank" class="task"><span>Like Facebook</span> <span class="badge">OPEN</span></a>
                <div class="task" id="adBox" onclick="startTimer()" style="cursor:pointer;">
                    <span id="timerText">Watch Video (30s)</span> <span class="badge" style="background:#f2bc1b; color:black;">START</span>
                </div>
            </div>
            <script>
                function startTimer() {
                    let s = 30; let text = document.getElementById('timerText');
                    document.getElementById('adBox').style.pointerEvents = "none";
                    let t = setInterval(() => {
                        text.innerHTML = "Processing: " + s + "s"; s--;
                        if(s < 0) {
                            clearInterval(t);
                            window.location.href = "/dashboard?id={{uid}}&name={{name}}&ad=1";
                        }
                    }, 1000);
                }
            </script>
        </body></html>
        """, pts=u_data['pts'], refs=u_data['refs'], uid=uid, name=name, yt=YT_LINK, insta=INSTA_LINK, fb=FB_LINK, msg=msg)
    except Exception as e:
        return f"<h3>Database Error:</h3><p>{str(e)}</p>"
