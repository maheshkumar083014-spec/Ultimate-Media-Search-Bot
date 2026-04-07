import os
import time
import uuid
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template_string
from telegram import Update, Bot, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

app = Flask(__name__)

# --- CONFIGURATION ---
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
bot = Bot(token=TOKEN)

# Links & Assets
WELCOME_IMG = "https://i.ibb.co/39V9V4Y3/image.jpg" 
YT_LINK = "https://www.youtube.com/@USSoccerPulse"
INSTA_LINK = "https://www.instagram.com/digital_rockstar_m"
FB_LINK = "https://www.facebook.com/profile.php?id=61574378159053"
AD_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"

# --- FIREBASE SETUP ---
def init_fb():
    if not firebase_admin._apps:
        try:
            # Private key formatting for Vercel/Environment
            raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "")
            if not raw_key:
                # Agar Env Variable nahi hai toh ye fallback key use karega (Lekin Env best hai)
                return False
            
            clean_key = raw_key.replace('\\n', '\n').strip().strip('"').strip("'")
            
            cred_dict = {
                "type": "service_account",
                "project_id": "ultimatemediasearch",
                "private_key": clean_key,
                "client_email": "firebase-adminsdk-fbsvc@ultimatemediasearch.iam.gserviceaccount.com",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'})
        except Exception as e:
            print(f"Firebase Init Error: {e}")
            return False
    return True

# --- BOT WEBHOOK HANDLER ---
@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == "POST":
        try:
            data = request.get_json(force=True)
            if "message" in data:
                msg_obj = data["message"]
                chat_id = str(msg_obj["chat"]["id"])
                u_name = msg_obj["from"].get("first_name", "User")
                
                init_fb()
                user_ref = db.reference(f'users/{chat_id}')
                user_data = user_ref.get()

                # Naya user check aur coupon generate
                if not user_data:
                    user_ref.set({
                        "name": u_name,
                        "pts": 10,
                        "coupon": str(uuid.uuid4())[:8],
                        "last_ad": 0
                    })
                
                # Dashboard Button
                dash_url = f"https://ultimate-media-search-bot.vercel.app/dashboard?id={chat_id}&name={u_name}"
                kb = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🚀 Open Earning Dashboard", web_app=WebAppInfo(url=dash_url))
                ]])
                
                welcome_text = (
                    f"✨ *Hello {u_name}!* ✨\n\n"
                    f"💪 *'Zindagi mein koshish karne walon ki kabhi haar nahi hoti.'*\n\n"
                    f"🌟 Aaj se hi apni earning shuru karein!\n\n"
                    f"📊 *Niche button par click karke dashboard kholein.*"
                )
                
                bot.send_photo(chat_id, WELCOME_IMG, caption=welcome_text, parse_mode="Markdown", reply_markup=kb)
        except Exception as e:
            print(f"Webhook Error: {e}")
            
    return "Bot is running", 200

# --- DASHBOARD UI ---
@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    init_fb()
    
    u_ref = db.reference(f'users/{uid}')
    u_data = u_ref.get() or {"pts": 0, "coupon": "...", "last_ad": 0}
    
    # Ad Points Claim Logic
    if request.args.get('claim_ad') == '1':
        now = time.time()
        last_ad = u_data.get('last_ad', 0)
        # 10 minute cooldown for testing, change 600 to 3600 for 1 hour
        if now - last_ad > 600: 
            u_ref.update({"pts": u_data.get('pts', 0) + 10, "last_ad": now})
            return render_template_string("<script>alert('Points Added Successfully!'); window.location.href='/dashboard?id={{uid}}&name={{name}}';</script>", uid=uid, name=name)
        else:
            return render_template_string("<script>alert('Please wait before watching next ad!'); window.location.href='/dashboard?id={{uid}}&name={{name}}';</script>", uid=uid, name=name)

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            body { background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding:15px; margin:0; }
            .card { background: linear-gradient(145deg, #1e293b, #0f172a); border-radius:20px; padding:20px; border:1px solid #334155; margin-bottom:15px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
            .pts { font-size:48px; color:#fbbf24; font-weight:bold; margin:10px 0; }
            .btn-withdraw { background:#fbbf24; color:#000; padding:12px; border-radius:12px; width:100%; border:none; font-weight:bold; cursor:pointer; font-size:16px; }
            .task-container { text-align:left; }
            .task-label { font-size:12px; color:#94a3b8; font-weight:bold; margin-bottom:10px; display:block; }
            .task { background:#1e293b; padding:15px; border-radius:15px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center; text-decoration:none; color:white; border:1px solid #334155; transition: 0.3s; }
            .task:active { transform: scale(0.98); background: #334155; }
            .icon-box { width:35px; height:35px; border-radius:8px; display:flex; align-items:center; justify-content:center; margin-right:12px; }
            .coupon-box { margin-top:10px; font-size:14px; background:#334155; padding:10px; border-radius:10px; }
        </style>
    </head>
    <body>
        <div class="card">
            <p style="margin:0; opacity:0.8;">Total Earnings</p>
            <div class="pts">{{pts}}</div>
            <button class="btn-withdraw" onclick="alert('Minimum 100 points required to withdraw!')">💳 WITHDRAW (100 MIN)</button>
            <div class="coupon-box">🎁 Your Coupon: <b style="color:#fbbf24;">{{coupon}}</b></div>
        </div>

        <div class="task-container">
            <span class="task-label">AVAILABLE TASKS</span>
            
            <a href="{{yt}}" target="_blank" class="task">
                <div style="display:flex; align-items:center;">
                    <div class="icon-box" style="background:#ef4444;"><i class="fab fa-youtube"></i></div>
                    <span>Subscribe YouTube</span>
                </div>
                <b style="color:#fbbf24;">+5</b>
            </a>

            <a href="{{insta}}" target="_blank" class="task">
                <div style="display:flex; align-items:center;">
                    <div class="icon-box" style="background:#f43f5e;"><i class="fab fa-instagram"></i></div>
                    <span>Follow Instagram</span>
                </div>
                <b style="color:#fbbf24;">+5</b>
            </a>

            <a href="{{fb}}" target="_blank" class="task">
                <div style="display:flex; align-items:center;">
                    <div class="icon-box" style="background:#3b82f6;"><i class="fab fa-facebook-f"></i></div>
                    <span>Follow Facebook</span>
                </div>
                <b style="color:#fbbf24;">+5</b>
            </a>

            <div class="task" onclick="watchAd()" style="cursor:pointer;">
                <div style="display:flex; align-items:center;">
                    <div class="icon-box" style="background:#fbbf24; color:#000;"><i class="fas fa-play"></i></div>
                    <span id="adText">Watch Video Ad (30s)</span>
                </div>
                <b id="adStatus" style="color:#fbbf24;">+10</b>
            </div>

            <a href="https://t.me/share/url?url=https://t.me/UltimateMediaSearchBot?start={{uid}}&text=Join and earn! Use my coupon: {{coupon}}" class="task" style="background:rgba(59,130,246,0.1); border-color:#3b82f6;">
                <div style="display:flex; align-items:center;">
                    <div class="icon-box" style="background:#3b82f6;"><i class="fas fa-share-alt"></i></div>
                    <span>Share & Earn</span>
                </div>
                <b style="color:#fbbf24;">+5</b>
            </a>
        </div>

        <script>
            function watchAd(){
                window.open("{{ad_link}}", "_blank");
                let timeLeft = 30;
                const btn = document.getElementById('adStatus');
                const text = document.getElementById('adText');
                
                const timer = setInterval(() => {
                    timeLeft--;
                    btn.innerHTML = timeLeft + "s";
                    text.innerHTML = "Verifying Ad...";
                    if (timeLeft <= 0) {
                        clearInterval(timer);
                        window.location.href = "/dashboard?id={{uid}}&name={{name}}&claim_ad=1";
                    }
                }, 1000);
            }
        </script>
    </body>
    </html>
    """, pts=u_data.get('pts',0), coupon=u_data.get('coupon','...'), uid=uid, name=name, yt=YT_LINK, insta=INSTA_LINK, fb=FB_LINK, ad_link=AD_LINK)

if __name__ == "__main__":
    app.run(debug=True)
