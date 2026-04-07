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
                u_data = user_ref.get()
                
                # Check and Create User/Coupon
                if not u_data:
                    user_ref.set({"name": u_name, "pts": 10, "refs": 0, "last_ad": 0, "coupon": str(uuid.uuid4())[:8]})
                elif "coupon" not in u_data:
                    user_ref.update({"coupon": str(uuid.uuid4())[:8]})

                dash_url = f"https://ultimate-media-search-bot.vercel.app/dashboard?id={uid}&name={u_name}"
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Open Earning Dashboard", web_app=WebAppInfo(url=dash_url))]])
                
                motivational_msg = (
                    f"✨ *Hello {u_name}!* ✨\n\n"
                    f"💪 *'Haar tab hoti hai jab maan liya jata hai, jeet tab hoti hai jab thaan liya jata hai.'*\n\n"
                    f"🌟 Aaj ka din aapki kamyabi ki nayi shuruat ho sakta hai. Dashboard kholein aur apna pehla bonus claim karein!\n\n"
                    f"📊 *Niche button par click karein.*"
                )
                bot.send_photo(uid, WELCOME_IMG, caption=motivational_msg, parse_mode="Markdown", reply_markup=kb)
            return "ok", 200
        except: return "ok", 200
    return "Running", 200

@app.route('/dashboard')
def dashboard():
    uid, name = request.args.get('id', '0'), request.args.get('name', 'User')
    init_fb()
    try:
        u_ref = db.reference(f'users/{uid}')
        u_data = u_ref.get() or {}
        
        # Ensure coupon exists for the user
        if u_data and "coupon" not in u_data:
            new_c = str(uuid.uuid4())[:8]
            u_ref.update({"coupon": new_c})
            u_data["coupon"] = new_c

        pts = u_data.get('pts', 0)
        refs = u_data.get('refs', 0)
        last_ad = u_data.get('last_ad', 0)
        user_coupon = u_data.get('coupon', '...GEN...')
        
        msg = ""
        now = time.time()
        
        # Claim Ad
        if request.args.get('claim_ad') == '1':
            if now - last_ad > 86400:
                u_ref.update({"pts": pts + 10, "last_ad": now})
                pts += 10
                msg = "✅ Ad Watch Success! +10 Points."
            else: msg = "🕒 Limit: 1 Ad per day."

        # Apply Friend's Coupon
        if request.args.get('apply_coupon'):
            code = request.args.get('apply_coupon').strip()
            if code == user_coupon:
                msg = "❌ Apna hi coupon use nahi kar sakte!"
            else:
                all_users = db.reference('users').get()
                found = False
                for k, v in all_users.items():
                    if v.get('coupon') == code:
                        # Reward the friend
                        db.reference(f'users/{k}').update({"pts": v.get('pts', 0) + 5, "refs": v.get('refs', 0) + 1})
                        # Reward current user
                        u_ref.update({"pts": pts + 5})
                        pts += 5
                        msg = "🎁 Coupon Applied! +5 Points added to both."
                        bot.send_message(k, f"🎊 Someone used your coupon! You got +5 points.")
                        found = True
                        break
                if not found: msg = "❌ Wrong Coupon Code!"

        # Withdraw
        if request.args.get('submit') == '1' and pts >= 100:
            p, u = request.args.get('phone'), request.args.get('upi')
            db.reference(f'withdrawals/{uid}').set({"phone": p, "upi": u, "pts": pts})
            bot.send_message(ADMIN_ID, f"💰 *NEW WITHDRAW REQUEST*\n👤 {name}\n💎 Points: {pts}\n📞 {p}\n🆔 {u}")
            msg = "✅ Sent! Admin will pay you shortly."

        return render_template_string("""
        <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            body { background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding:10px; margin:0; }
            .card { background: linear-gradient(145deg, #1e293b, #0f172a); border-radius:15px; padding:15px; border:1px solid #334155; margin-bottom:10px; }
            .pts { font-size:40px; color:#fbbf24; font-weight:bold; }
            .btn { background:#fbbf24; color:black; padding:10px; border-radius:10px; width:100%; border:none; font-weight:bold; cursor:pointer; }
            .task { background:#1e293b; padding:12px; border-radius:12px; margin-top:8px; display:flex; justify-content:space-between; align-items:center; text-decoration:none; color:white; border:1px solid #334155; }
            .icon-box { width:30px; height:30px; border-radius:5px; display:flex; align-items:center; justify-content:center; margin-right:10px; font-size:14px; }
            input { width:80%; padding:10px; margin:5px 0; border-radius:8px; border:1px solid #334155; background:#0f172a; color:white; }
            #adCon { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:#000; z-index:1000; padding-top:150px; }
        </style></head>
        <body>
            <div id="adCon"><h2>📺 Ad Loading...</h2><p id="tm">30s</p><p style="color:#334155;">[ Video Ad Placeholder ]</p></div>

            <div class="card">
                <p style="margin:0; opacity:0.7;">My Points</p>
                <div class="pts">{{pts}}</div>
                {% if pts >= 100 %}
                    <button class="btn" onclick="document.getElementById('wbox').style.display='block'">💳 WITHDRAW</button>
                {% else %}
                    <button class="btn" style="opacity:0.5;">🔒 NEED 100 PTS</button>
                {% endif %}
            </div>

            {% if msg %}<p style="color:#fbbf24; background:#1e293b; padding:10px; border-radius:10px;">{{msg}}</p>{% endif %}

            <div class="card">
                <b>🎁 Your Coupon: <span style="color:#fbbf24;">{{user_coupon}}</span></b>
                <p style="font-size:11px; opacity:0.6;">Enter friend's coupon below to get +5 pts</p>
                <input type="text" id="cin" placeholder="Friend's Coupon">
                <button onclick="applyC()" style="background:#22c55e; border:none; color:white; padding:5px 15px; border-radius:5px; cursor:pointer;">Apply</button>
            </div>

            <div id="wbox" style="display:none;" class="card">
                <form method="GET">
                    <input type="hidden" name="id" value="{{uid}}"><input type="hidden" name="name" value="{{name}}"><input type="hidden" name="submit" value="1">
                    <input type="number" name="phone" placeholder="WhatsApp No" required>
                    <input type="text" name="upi" placeholder="UPI ID" required>
                    <button type="submit" class="btn" style="background:#22c55e; color:white;">Submit Details</button>
                </form>
            </div>

            <div style="text-align:left;">
                <p style="font-weight:bold; color:#94a3b8; font-size:13px;">DAILY TASKS</p>
                <a href="{{yt}}" class="task"><div style="display:flex;"><div class="icon-box" style="background:red;"><i class="fab fa-youtube"></i></div>YouTube</div><b>+5</b></a>
                <a href="{{insta}}" class="task"><div style="display:flex;"><div class="icon-box" style="background:orange;"><i class="fab fa-instagram"></i></div>Instagram</div><b>+5</b></a>
                <div class="task" onclick="goAd()" style="cursor:pointer;"><div style="display:flex;"><div class="icon-box" style="background:#fbbf24; color:black;"><i class="fas fa-play"></i></div>Watch Ad (30s)</div><b>+10</b></div>
                
                <a href="https://t.me/share/url?url=https://t.me/UltimateMediaSearchBot?start={{uid}}&text=Join Ultimate Earning Bot! 💰 %0A1. Open Dashboard %0A2. Use my Coupon: {{user_coupon}} %0A3. Get Free 5 Points instantly!" class="task" style="background:#3b82f6;">
                    <div style="display:flex;"><div class="icon-box" style="background:white; color:#3b82f6;"><i class="fas fa-share-alt"></i></div>Share & Earn</div><b>+5</b>
                </a>
            </div>

            <script>
                function goAd(){
                    document.getElementById('adCon').style.display='block';
                    let s=30;
                    let t=setInterval(()=>{
                        document.getElementById('tm').innerHTML = s+"s"; s--;
                        if(s<0){ clearInterval(t); window.location.href="/dashboard?id={{uid}}&name={{name}}&claim_ad=1"; }
                    },1000);
                }
                function applyC(){
                    let c = document.getElementById('cin').value;
                    if(c) window.location.href="/dashboard?id={{uid}}&name={{name}}&apply_coupon="+c;
                }
            </script>
        </body></html>
        """, pts=pts, uid=uid, name=name, yt=YT_LINK, insta=INSTA_LINK, mot=MOTIVATION_LINK, user_coupon=user_coupon, msg=msg)
    except Exception as e: return str(e)
