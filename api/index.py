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

# Aapki nayi photo yahan add kar di hai
WELCOME_IMG = "https://i.ibb.co/39V9V4Y3/image.jpg" 

YT_LINK = "https://www.youtube.com/@USSoccerPulse"
INSTA_LINK = "https://www.instagram.com/digital_rockstar_m"
FB_LINK = "https://www.facebook.com/profile.php?id=61574378159053"
AD_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"

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
                
                if not u_data:
                    user_ref.set({"name": u_name, "pts": 10, "refs": 0, "last_ad": 0, "coupon": str(uuid.uuid4())[:8]})
                elif "coupon" not in u_data:
                    user_ref.update({"coupon": str(uuid.uuid4())[:8]})

                dash_url = f"https://ultimate-media-search-bot.vercel.app/dashboard?id={uid}&name={u_name}"
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Open Earning Dashboard", web_app=WebAppInfo(url=dash_url))]])
                
                msg = (f"✨ *Hello {u_name}!* ✨\n\n"
                       f"💪 *'Zindagi mein koshish karne walon ki kabhi haar nahi hoti.'*\n\n"
                       f"🌟 Aaj se hi apni earning shuru karein!\n\n"
                       f"📊 *Niche button par click karein.*")
                
                bot.send_photo(uid, WELCOME_IMG, caption=msg, parse_mode="Markdown", reply_markup=kb)
            return "ok", 200
        except: return "ok", 200
    return "Bot Active", 200

@app.route('/dashboard')
def dashboard():
    uid, name = request.args.get('id', '0'), request.args.get('name', 'User')
    init_fb()
    try:
        u_ref = db.reference(f'users/{uid}')
        u_data = u_ref.get() or {}
        pts, last_ad = u_data.get('pts', 0), u_data.get('last_ad', 0)
        user_coupon = u_data.get('coupon', '...')
        
        msg = ""
        now = time.time()
        
        if request.args.get('claim_ad') == '1':
            if now - last_ad > 3600:
                u_ref.update({"pts": pts + 10, "last_ad": now})
                pts += 10
                msg = "✅ Ad Success! +10 Points."
            else: msg = "🕒 Please wait before watching next ad."

        if request.args.get('apply_coupon'):
            code = request.args.get('apply_coupon').strip()
            all_users = db.reference('users').get()
            for k, v in all_users.items():
                if v.get('coupon') == code and k != uid:
                    db.reference(f'users/{k}').update({"pts": v.get('pts', 0) + 5, "refs": v.get('refs', 0) + 1})
                    u_ref.update({"pts": pts + 5})
                    pts += 5
                    msg = "🎁 Coupon Applied! +5 Pts."
                    break

        return render_template_string("""
        <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            body { background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding:10px; margin:0; }
            .card { background: linear-gradient(145deg, #1e293b, #0f172a); border-radius:15px; padding:15px; border:1px solid #334155; margin-bottom:10px; }
            .pts { font-size:40px; color:#fbbf24; font-weight:bold; }
            .btn { background:#fbbf24; color:black; padding:10px; border-radius:10px; width:100%; border:none; font-weight:bold; cursor:pointer; }
            .task { background:#1e293b; padding:12px; border-radius:12px; margin-top:8px; display:flex; justify-content:space-between; align-items:center; text-decoration:none; color:white; border:1px solid #334155; }
            .icon-box { width:30px; height:30px; border-radius:5px; display:flex; align-items:center; justify-content:center; margin-right:10px; }
            input { width:70%; padding:8px; border-radius:5px; border:1px solid #334155; background:#0f172a; color:white; }
        </style></head>
        <body>
            <div class="card">
                <p style="margin:0; opacity:0.7;">My Points</p>
                <div class="pts">{{pts}}</div>
                <button class="btn" style="opacity:{{'1' if pts>=100 else '0.5'}}">💳 WITHDRAW (100 MIN)</button>
            </div>

            {% if msg %}<p style="color:#fbbf24;">{{msg}}</p>{% endif %}

            <div class="card">
                <b>🎁 Coupon: <span style="color:#fbbf24;">{{user_coupon}}</span></b><br><br>
                <input type="text" id="cin" placeholder="Enter Friend's Coupon">
                <button onclick="window.location.href='/dashboard?id={{uid}}&name={{name}}&apply_coupon='+document.getElementById('cin').value" style="background:#22c55e; border:none; color:white; padding:8px 12px; border-radius:5px;">Apply</button>
            </div>

            <div style="text-align:left;">
                <p style="font-weight:bold; color:#94a3b8; font-size:12px;">DAILY TASKS</p>
                <a href="{{yt}}" class="task"><div style="display:flex;"><div class="icon-box" style="background:red;"><i class="fab fa-youtube"></i></div>YouTube</div><b>+5</b></a>
                <a href="{{insta}}" class="task"><div style="display:flex;"><div class="icon-box" style="background:orange;"><i class="fab fa-instagram"></i></div>Instagram</div><b>+5</b></a>
                <a href="{{fb}}" class="task"><div style="display:flex;"><div class="icon-box" style="background:#0668E1;"><i class="fab fa-facebook-f"></i></div>Facebook</div><b>+5</b></a>
                
                <div class="task" onclick="watchAd()" style="cursor:pointer;"><div style="display:flex;"><div class="icon-box" style="background:#fbbf24; color:black;"><i class="fas fa-play"></i></div>Watch Ad (30s)</div><b id="adStatus">+10</b></div>
                
                <a href="https://t.me/share/url?url=https://t.me/UltimateMediaSearchBot?start={{uid}}&text=Use my coupon: {{user_coupon}} for +5 bonus!" class="task" style="background:#3b82f6;"><div style="display:flex;"><div class="icon-box" style="background:white; color:#3b82f6;"><i class="fas fa-share-alt"></i></div>Share & Earn</div><b>+5</b></a>
            </div>

            <script>
                function watchAd(){
                    window.open("{{ad_link}}", "_blank");
                    let s=30;
                    document.getElementById('adStatus').innerHTML = "Wait "+s+"s";
                    let t = setInterval(()=>{
                        s--; document.getElementById('adStatus').innerHTML = "Wait "+s+"s";
                        if(s<=0){ 
                            clearInterval(t); 
                            window.location.href="/dashboard?id={{uid}}&name={{name}}&claim_ad=1";
                        }
                    },1000);
                }
            </script>
        </body></html>
        """, pts=pts, uid=uid, name=name, yt=YT_LINK, insta=INSTA_LINK, fb=FB_LINK, ad_link=AD_LINK, user_coupon=user_coupon, msg=msg)
    except Exception as e: return str(e)
