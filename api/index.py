import os
import time
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template_string
from telegram import Update, Bot, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

app = Flask(__name__)

# --- CONFIG ---
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
ADMIN_ID = "8678211883"
bot = Bot(token=TOKEN)

WELCOME_IMG = "https://i.ibb.co/zWJHms9p/image.jpg"
YT_LINK = "https://www.youtube.com/@USSoccerPulse"
INSTA_LINK = "https://www.instagram.com/digital_rockstar_m"
FB_LINK = "https://www.facebook.com/profile.php?id=61574378159053"
MOTIVATION_LINK = "https://t.me/Motivation_Quotes_Hindi" # Aapka motivation channel

def init_fb():
    if not firebase_admin._apps:
        try:
            key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n').strip().strip('"').strip("'")
            cred_dict = {
                "type": "service_account",
                "project_id": "ultimatemediasearch",
                "private_key_id": "571ab3737559ec758db4a017796d2134ae468163",
                "private_key": key,
                "client_email": "firebase-adminsdk-fbsvc@ultimatemediasearch.iam.gserviceaccount.com",
                "client_id": "107810087265546309339",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40ultimatemediasearch.iam.gserviceaccount.com"
            }
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'})
        except: return False
    return True

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == "POST":
        try:
            data = request.get_json(force=True)
            update = Update.de_json(data, bot)
            if update.message and update.message.text:
                uid, u_name = str(update.message.chat_id), update.effective_user.first_name
                init_fb()
                user_ref = db.reference(f'users/{uid}')
                if not user_ref.get():
                    user_ref.set({"name": u_name, "pts": 10, "refs": 0, "last_ad": 0})

                dash_url = f"https://ultimate-media-search-bot.vercel.app/dashboard?id={uid}&name={u_name}"
                kb = ReplyKeyboardMarkup([[KeyboardButton("🚀 My Earning Dashboard", web_app=WebAppInfo(url=dash_url))]], resize_keyboard=True)
                
                # Enhanced Welcome Message
                welcome_msg = (
                    f"🎊 *Congratulations {u_name}!* 🎊\n\n"
                    f"🔥 *Aapka Digital Earning Safar Shuru Ho Chuka Hai!*\n\n"
                    f"💰 Humne aapko *10 Bonus Points* diye hain.\n"
                    f"📈 Rozana tasks pure karein aur unlimited paise kamayein.\n\n"
                    f"👇 *Niche button par click karke Dashboard kholein!*"
                )
                bot.send_photo(uid, WELCOME_IMG, caption=welcome_msg, parse_mode="Markdown", reply_markup=kb)
            return "ok", 200
        except: return "ok", 200
    return "Bot Running", 200

@app.route('/dashboard')
def dashboard():
    uid, name = request.args.get('id', '0'), request.args.get('name', 'User')
    init_fb()
    try:
        u_ref = db.reference(f'users/{uid}')
        u_data = u_ref.get() or {"pts": 0, "refs": 0, "last_ad": 0}
        pts, refs, last_ad = u_data.get('pts', 0), u_data.get('refs', 0), u_data.get('last_ad', 0)
        
        msg = ""
        now = time.time()
        
        # Auto Claim Logic
        if now - last_ad > 86400:
            u_ref.update({"pts": pts + 15, "last_ad": now})
            pts += 15
            msg = "✅ Daily Login Bonus: +15 Points!"

        # Withdraw Request
        if request.args.get('submit') == '1' and pts >= 100:
            phone, upi = request.args.get('phone'), request.args.get('upi')
            db.reference(f'withdrawals/{uid}').set({"name": name, "phone": phone, "upi": upi, "pts": pts})
            bot.send_message(ADMIN_ID, f"💰 *WITHDRAWAL ALERT*\n👤 {name}\n📞 {phone}\n🆔 {upi}\n💎 Points: {pts}")
            msg = "✅ Withdrawal request sent to Admin!"

        return render_template_string("""
        <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            body { background:#0f172a; color:white; font-family:'Segoe UI', sans-serif; text-align:center; padding:15px; margin:0; }
            .card { background: linear-gradient(145deg, #1e293b, #0f172a); border-radius:20px; padding:25px; border:1px solid #334155; margin-bottom:15px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }
            .pts { font-size:50px; color:#fbbf24; font-weight:bold; text-shadow: 0 0 10px rgba(251,191,36,0.3); }
            .btn { background:#fbbf24; color:black; padding:12px; border-radius:12px; width:100%; border:none; font-weight:bold; cursor:pointer; margin-top:15px; font-size:16px; }
            .task { background:#1e293b; padding:15px; border-radius:15px; margin-top:12px; display:flex; justify-content:space-between; align-items:center; text-decoration:none; color:white; border:1px solid #334155; transition: 0.3s; }
            .task:active { transform: scale(0.98); background: #334155; }
            .icon-box { width:40px; height:40px; border-radius:10px; display:flex; align-items:center; justify-content:center; margin-right:10px; }
            input { width:90%; padding:12px; margin:8px 0; border-radius:10px; border:1px solid #334155; background:#0f172a; color:white; }
            .lock-msg { color:#ef4444; font-size:12px; margin-top:5px; }
        </style></head>
        <body>
            <div class="card">
                <p style="margin:0; opacity:0.8;">My Total Balance</p>
                <div class="pts">{{pts}}</div>
                <p style="font-size:14px;">Referrals: <span style="color:#fbbf24;">{{refs}}</span></p>
                
                {% if pts >= 100 %}
                    <button class="btn" onclick="document.getElementById('wbox').style.display='block'">💰 WITHDRAW NOW</button>
                {% else %}
                    <button class="btn" style="opacity:0.5; cursor:not-allowed;">🔒 WITHDRAW (Need 100 Pts)</button>
                    <div class="lock-msg">Aapko 100 points chahiye withdraw karne ke liye.</div>
                {% endif %}
            </div>

            <div id="wbox" style="display:none;" class="card">
                <h3>Withdrawal Details</h3>
                <form method="GET">
                    <input type="hidden" name="id" value="{{uid}}"><input type="hidden" name="name" value="{{name}}"><input type="hidden" name="submit" value="1">
                    <input type="number" name="phone" placeholder="WhatsApp Number" required>
                    <input type="text" name="upi" placeholder="UPI ID (PhonePe/GPay)" required>
                    <button type="submit" class="btn" style="background:#22c55e; color:white;">Submit Request</button>
                </form>
            </div>

            {% if msg %}<div class="card" style="padding:10px; border-color:#fbbf24;">{{msg}}</div>{% endif %}

            <div style="text-align:left;">
                <p style="font-weight:bold; margin-left:5px; color:#94a3b8;">DAILY TASKS</p>
                
                <a href="{{yt}}" target="_blank" class="task">
                    <div style="display:flex; align-items:center;">
                        <div class="icon-box" style="background:#ef4444;"><i class="fab fa-youtube"></i></div>
                        <span>Subscribe YouTube</span>
                    </div>
                    <b style="color:#22c55e;">+5</b>
                </a>

                <a href="{{insta}}" target="_blank" class="task">
                    <div style="display:flex; align-items:center;">
                        <div class="icon-box" style="background:linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888);"><i class="fab fa-instagram"></i></div>
                        <span>Follow Instagram</span>
                    </div>
                    <b style="color:#22c55e;">+5</b>
                </a>

                <a href="{{fb}}" target="_blank" class="task">
                    <div style="display:flex; align-items:center;">
                        <div class="icon-box" style="background:#0668E1;"><i class="fab fa-facebook-f"></i></div>
                        <span>Like Facebook Page</span>
                    </div>
                    <b style="color:#22c55e;">+5</b>
                </a>

                <a href="{{mot}}" target="_blank" class="task">
                    <div style="display:flex; align-items:center;">
                        <div class="icon-box" style="background:#3b82f6;"><i class="fas fa-quote-left"></i></div>
                        <span>Daily Motivation</span>
                    </div>
                    <b style="color:#fbbf24;">FREE</b>
                </a>
                
                <div class="task" onclick="startAd()" style="cursor:pointer;">
                    <div style="display:flex; align-items:center;">
                        <div class="icon-box" style="background:#fbbf24; color:black;"><i class="fas fa-play"></i></div>
                        <span id="atText">Watch Ad (30s)</span>
                    </div>
                    <b style="color:#fbbf24;">START</b>
                </div>
            </div>

            <script>
                function startAd(){
                    let s=30; let b=document.getElementById('atText');
                    let t=setInterval(()=>{
                        b.innerHTML="Verifying: "+s+"s"; s--;
                        if(s<0){ clearInterval(t); window.location.href="/dashboard?id={{uid}}&name={{name}}&claim_ad=1"; }
                    },1000);
                }
            </script>
        </body></html>
        """, pts=pts, refs=refs, uid=uid, name=name, yt=YT_LINK, insta=INSTA_LINK, fb=FB_LINK, mot=MOTIVATION_LINK, msg=msg)
    except Exception as e: return str(e)
