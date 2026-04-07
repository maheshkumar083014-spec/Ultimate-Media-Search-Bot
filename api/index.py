import os
import time
import uuid
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template_string
from telegram import Update, Bot, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

app = Flask(__name__)

# --- CONFIG ---
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
ADMIN_ID = "8678211883"
bot = Bot(token=TOKEN)

WELCOME_IMG = "https://i.ibb.co/zWJHms9p/image.jpg"
YT_LINK = "https://www.youtube.com/@USSoccerPulse"
INSTA_LINK = "https://www.instagram.com/digital_rockstar_m"
FB_LINK = "https://www.facebook.com/profile.php?id=61574378159053"
MOTIVATION_LINK = "https://t.me/Motivation_Quotes_Hindi"

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
                    user_ref.set({"name": u_name, "pts": 10, "refs": 0, "last_ad": 0, "coupon": str(uuid.uuid4())[:8]})

                dash_url = f"https://ultimate-media-search-bot.vercel.app/dashboard?id={uid}&name={u_name}"
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Open Earning Dashboard", web_app=WebAppInfo(url=dash_url))]])
                
                motivational_msg = (
                    f"✨ *Hello {u_name}!* ✨\n\n"
                    f"💪 *'Zindagi mein koshish karne walon ki kabhi haar nahi hoti.'*\n\n"
                    f"🌟 Aaj se hi apni earning shuru karein aur khud ko sabit karein!\n\n"
                    f"💰 *Aapko 10 Welcome Points mil chuke hain!*\n"
                    f"📊 Niche button se dashboard check karein."
                )
                bot.send_photo(uid, WELCOME_IMG, caption=motivational_msg, parse_mode="Markdown", reply_markup=kb)
            return "ok", 200
        except: return "ok", 200
    return "Active", 200

@app.route('/dashboard')
def dashboard():
    uid, name = request.args.get('id', '0'), request.args.get('name', 'User')
    init_fb()
    try:
        u_ref = db.reference(f'users/{uid}')
        u_data = u_ref.get() or {"pts": 0, "refs": 0, "last_ad": 0}
        pts, refs, last_ad = u_data.get('pts', 0), u_data.get('refs', 0), u_data.get('last_ad', 0)
        user_coupon = u_data.get('coupon', 'N/A')
        
        msg = ""
        now = time.time()
        
        # 1. Ad Claim Logic (After 30s)
        if request.args.get('claim_ad') == '1':
            if now - last_ad > 86400: # Daily limit
                u_ref.update({"pts": pts + 10, "last_ad": now})
                pts += 10
                msg = "✅ Ad Watch Success! +10 Points."
            else:
                msg = "🕒 Next Ad available in 24 hours."

        # 2. Coupon/Referral Logic
        if request.args.get('apply_coupon'):
            code = request.args.get('apply_coupon')
            all_users = db.reference('users').get()
            found = False
            for k, v in all_users.items():
                if v.get('coupon') == code and k != uid:
                    # Give points to both
                    db.reference(f'users/{k}').update({"pts": v.get('pts', 0) + 5})
                    u_ref.update({"pts": pts + 5})
                    pts += 5
                    msg = "🎁 Coupon Applied! +5 Points for both."
                    found = True
                    break
            if not found: msg = "❌ Invalid Coupon Code!"

        # 3. Withdraw
        if request.args.get('submit') == '1' and pts >= 100:
            phone, upi = request.args.get('phone'), request.args.get('upi')
            db.reference(f'withdrawals/{uid}').set({"phone": phone, "upi": upi, "pts": pts})
            bot.send_message(ADMIN_ID, f"💰 *NEW WITHDRAW*\n👤 {name}\n💎 Pts: {pts}")
            msg = "✅ Claim Request Sent!"

        return render_template_string("""
        <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            body { background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding:10px; margin:0; }
            .card { background: linear-gradient(145deg, #1e293b, #0f172a); border-radius:15px; padding:20px; border:1px solid #334155; margin-bottom:10px; }
            .pts { font-size:40px; color:#fbbf24; font-weight:bold; }
            .btn { background:#fbbf24; color:black; padding:10px; border-radius:10px; width:100%; border:none; font-weight:bold; cursor:pointer; }
            .task { background:#1e293b; padding:12px; border-radius:12px; margin-top:8px; display:flex; justify-content:space-between; align-items:center; text-decoration:none; color:white; border:1px solid #334155; }
            .icon-box { width:30px; height:30px; border-radius:5px; display:flex; align-items:center; justify-content:center; margin-right:10px; }
            input { width:85%; padding:10px; margin:5px 0; border-radius:8px; border:1px solid #334155; background:#0f172a; color:white; }
            #adContainer { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:black; z-index:999; padding-top:100px; }
        </style></head>
        <body>
            <div id="adContainer">
                <h2>📺 Watching Ad...</h2>
                <p id="timer">30s</p>
                <div style="background:#334155; width:300px; height:250px; margin:auto;">AD SPACE</div>
            </div>

            <div class="card">
                <p style="opacity:0.8;">Total Balance</p>
                <div class="pts">{{pts}}</div>
                <p>Referrals: {{refs}}</p>
                {% if pts >= 100 %}
                    <button class="btn" onclick="document.getElementById('wbox').style.display='block'">💰 CLAIM NOW</button>
                {% else %}
                    <button class="btn" style="opacity:0.5;">🔒 CLAIM (Min 100 Pts)</button>
                {% endif %}
            </div>

            {% if msg %}<div class="card" style="border-color:#fbbf24;">{{msg}}</div>{% endif %}

            <div class="card">
                <b>🎁 Referral Coupon: <span style="color:#fbbf24;">{{user_coupon}}</span></b><br>
                <input type="text" id="cinput" placeholder="Enter Friend's Coupon">
                <button class="btn" onclick="applyC()" style="width:auto; padding:5px 15px;">Apply</button>
            </div>

            <div style="text-align:left;">
                <p style="font-weight:bold; color:#94a3b8; margin-left:5px;">EARNING TASKS</p>
                <a href="{{yt}}" class="task"><div style="display:flex;"><div class="icon-box" style="background:red;"><i class="fab fa-youtube"></i></div>YouTube</div><b>+5</b></a>
                <a href="{{insta}}" class="task"><div style="display:flex;"><div class="icon-box" style="background:orange;"><i class="fab fa-instagram"></i></div>Instagram</div><b>+5</b></a>
                <div class="task" onclick="showAd()" style="cursor:pointer;"><div style="display:flex;"><div class="icon-box" style="background:#fbbf24; color:black;"><i class="fas fa-play"></i></div>Watch Ad (30s)</div><b>+10</b></div>
                <a href="https://t.me/share/url?url=https://t.me/UltimateMediaSearchBot?start={{uid}}&text=Join and earn! Use my coupon: {{user_coupon}}" class="task" style="background:#3b82f6;"><div style="display:flex;"><div class="icon-box" style="background:white; color:#3b82f6;"><i class="fas fa-share-alt"></i></div>Share & Earn</div><b>+5</b></a>
                <a href="{{mot}}" class="task"><div style="display:flex;"><div class="icon-box" style="background:#22c55e;"><i class="fas fa-quote-left"></i></div>Motivation</div><b>FREE</b></a>
            </div>

            <script>
                function showAd(){
                    document.getElementById('adContainer').style.display='block';
                    let s=30;
                    let t=setInterval(()=>{
                        document.getElementById('timer').innerHTML = s+"s"; s--;
                        if(s<0){ 
                            clearInterval(t); 
                            window.location.href="/dashboard?id={{uid}}&name={{name}}&claim_ad=1"; 
                        }
                    },1000);
                }
                function applyC(){
                    let c = document.getElementById('cinput').value;
                    if(c) window.location.href="/dashboard?id={{uid}}&name={{name}}&apply_coupon="+c;
                }
            </script>
        </body></html>
        """, pts=pts, refs=refs, uid=uid, name=name, yt=YT_LINK, insta=INSTA_LINK, mot=MOTIVATION_LINK, user_coupon=user_coupon, msg=msg)
    except Exception as e: return str(e)
