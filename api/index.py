import os
import time
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template_string
from telegram import Update, Bot, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

app = Flask(__name__)

# --- CONFIG (FIXED) ---
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
ADMIN_ID = "8678211883" 
bot = Bot(token=TOKEN)

WELCOME_IMG = "https://i.ibb.co/zWJHms9p/image.jpg"
YT_LINK = "https://www.youtube.com/@USSoccerPulse"
INSTA_LINK = "https://www.instagram.com/digital_rockstar_m"
FB_LINK = "https://www.facebook.com/profile.php?id=61574378159053"

# --- FIREBASE INITIALIZATION ---
def init_fb():
    if not firebase_admin._apps:
        try:
            # Vercel env se key uthana aur format fix karna
            key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n').strip().strip('"').strip("'")
            
            service_account = {
                "type": "service_account",
                "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": key,
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
            }
            
            cred = credentials.Certificate(service_account)
            db_url = f"https://{os.getenv('FIREBASE_PROJECT_ID')}-default-rtdb.asia-southeast1.firebasedatabase.app/"
            firebase_admin.initialize_app(cred, {'databaseURL': db_url})
            return True
        except Exception as e:
            return str(e)
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
                
                # Check Database
                init_fb()
                user_ref = db.reference(f'users/{uid}')
                if not user_ref.get():
                    user_ref.set({"name": u_name, "pts": 10, "refs": 0, "last_ad": 0})

                # Button with full URL
                dash_url = f"https://ultimate-media-search-bot.vercel.app/dashboard?id={uid}&name={u_name}"
                kb = ReplyKeyboardMarkup([[KeyboardButton("📊 My Dashboard", web_app=WebAppInfo(url=dash_url))]], resize_keyboard=True)
                
                msg = f"🌟 *Khushamdeed {u_name}!*\n\nAapka bot ab puri tarah taiyar hai. Dashboard kholiye aur paise kamaiye!"
                bot.send_photo(uid, WELCOME_IMG, caption=msg, parse_mode="Markdown", reply_markup=kb)
            
            return "ok", 200
        except Exception as e:
            # Agar koi error aaye toh wo Telegram pe dikh jaye (Debug mode)
            print(f"Webhook Error: {e}")
            return "ok", 200
    return "<h1>Bot Status: Running</h1>", 200

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    
    conn = init_fb()
    if conn is not True:
        return f"<h3 style='color:red;'>Firebase Error: {conn}</h3><p>Check Vercel Environment Variables!</p>"

    try:
        u_ref = db.reference(f'users/{uid}')
        u_data = u_ref.get() or {"pts": 0, "refs": 0, "last_ad": 0}
        
        msg = ""
        if request.args.get('ad') == '1':
            now = time.time()
            if now - u_data.get('last_ad', 0) > 86400:
                u_ref.update({"pts": u_data['pts'] + 15, "last_ad": now})
                msg = "✅ Points Earned Successfully!"
                u_data = u_ref.get()
            else:
                msg = "🕒 Limit Reached: Try after 24h."

        return render_template_string("""
        <!DOCTYPE html>
        <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { background: #0b0e14; color: white; font-family: sans-serif; text-align: center; padding: 15px; }
            .card { background: #1c2128; border: 1px solid #30363d; border-radius: 15px; padding: 20px; margin-bottom: 15px; }
            .pts { font-size: 40px; color: #fbbf24; font-weight: bold; }
            .task { background: #22272e; padding: 12px; border-radius: 10px; margin-top: 10px; display: flex; justify-content: space-between; align-items: center; text-decoration: none; color: white; border: 1px solid #30363d; }
            .btn-go { background: #238636; color: white; padding: 5px 15px; border-radius: 5px; font-size: 14px; }
        </style></head>
        <body>
            <div class="card">
                <p style="margin:0; opacity:0.7;">Current Balance</p>
                <div class="pts">{{pts}}</div>
                <p>Referrals: {{refs}}</p>
            </div>
            {% if msg %}<p style="color:#fbbf24;">{{msg}}</p>{% endif %}
            <div style="text-align:left;">
                <b style="color:#58a6ff;">🚀 AVAILABLE TASKS</b>
                <a href="{{yt}}" target="_blank" class="task"><span>YouTube</span> <span class="btn-go">GO</span></a>
                <a href="{{insta}}" target="_blank" class="task"><span>Instagram</span> <span class="btn-go">GO</span></a>
                <a href="{{fb}}" target="_blank" class="task"><span>Facebook</span> <span class="btn-go">GO</span></a>
                <div class="task" id="adArea" onclick="runAd()" style="cursor:pointer;">
                    <span id="adText">Watch Ad (30s)</span> <span class="btn-go" style="background:#fbbf24; color:black;">CLAIM</span>
                </div>
            </div>
            <script>
                function runAd() {
                    let s = 30; let t = document.getElementById('adText');
                    document.getElementById('adArea').style.pointerEvents = "none";
                    let timer = setInterval(() => {
                        t.innerHTML = "Verifying: " + s + "s"; s--;
                        if(s < 0) {
                            clearInterval(timer);
                            window.location.href = "/dashboard?id={{uid}}&name={{name}}&ad=1";
                        }
                    }, 1000);
                }
            </script>
        </body></html>
        """, pts=u_data['pts'], refs=u_data['refs'], uid=uid, name=name, yt=YT_LINK, insta=INSTA_LINK, fb=FB_LINK, msg=msg)
    except Exception as e:
        return f"<h3>Database Error: {str(e)}</h3>"
