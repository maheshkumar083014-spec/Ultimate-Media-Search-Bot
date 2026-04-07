import os
import json
import uuid
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template_string
from telegram import Update, Bot, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

app = Flask(__name__)

# --- CONFIGURATION ---
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
bot = Bot(token=TOKEN)

PROFILE_PHOTO_URL = "https://i.ibb.co/39V9V4Y3/image.jpg"
YT_LINK = "https://www.youtube.com/@USSoccerPulse"
INSTA_LINK = "https://www.instagram.com/digital_rockstar_m"
FB_LINK = "https://www.facebook.com/profile.php?id=61574378159053"
DASHBOARD_BASE_URL = "https://ultimate-media-search-bot.vercel.app"

# --- FIREBASE INIT ---
def init_fb():
    if not firebase_admin._apps:
        cred_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
        if not cred_json:
            print("❌ Error: FIREBASE_SERVICE_ACCOUNT variable missing!")
            return False
        try:
            # eval() ki jagah json.loads() safe hai
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
            })
            return True
        except Exception as e:
            print(f"❌ Firebase Init Error: {e}")
            return False
    return True

# --- BOT LOGIC ---
@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == "POST":
        try:
            update = Update.de_json(request.get_json(force=True), bot)
            if not update or not update.message:
                return "OK", 200
            
            chat_id = str(update.message.chat_id)
            u_name = update.message.from_user.first_name or "User"

            if init_fb():
                user_ref = db.reference(f'users/{chat_id}')
                u_data = user_ref.get()

                if not u_data:
                    user_ref.set({
                        "name": u_name,
                        "pts": 10,
                        "coupon": str(uuid.uuid4())[:8],
                        "last_ad": 0
                    })
                
                dash_url = f"{DASHBOARD_BASE_URL}/dashboard?id={chat_id}&name={u_name}"
                kb = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🚀 Open Dashboard", web_app=WebAppInfo(url=dash_url))
                ]])
                
                # Photo send logic
                bot.send_photo(
                    chat_id=chat_id,
                    photo=PROFILE_PHOTO_URL,
                    caption=(
                        f"✨ *Welcome {u_name}!* ✨\n\n"
                        f"💪 Zindagi mein koshish karne walon ki kabhi haar nahi hoti.\n\n"
                        f"📊 Aaj se hi apni earning shuru karein!"
                    ),
                    parse_mode="Markdown",
                    reply_markup=kb
                )
        except Exception as e:
            print(f"⚠️ Webhook Error: {e}")
            
    return "Bot is Active", 200

# --- DASHBOARD ---
@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    
    if not init_fb():
        return "Database Connection Error", 500

    u_ref = db.reference(f'users/{uid}')
    u_data = u_ref.get() or {"pts": 0, "coupon": "N/A"}
    
    if request.args.get('ad_claim') == '1':
        new_pts = u_data.get('pts', 0) + 10
        u_ref.update({"pts": new_pts})
        # Success alert ke baad wapas dashboard pe
        return render_template_string("<script>alert('10 Points Added!'); window.location.href='/dashboard?id={{uid}}&name={{name}}';</script>", uid=uid, name=name)

    return render_template_string("""
    <!DOCTYPE html><html><head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background:#0f172a; color:white; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align:center; padding:15px; margin:0; }
        .card { background:#1e293b; border-radius:15px; padding:20px; border:1px solid #334155; margin-bottom:15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        .pts { font-size:48px; color:#fbbf24; font-weight:bold; margin: 10px 0; }
        .btn-withdraw { background:#b45309; color:white; padding:12px; border-radius:10px; width:100%; border:none; font-weight:bold; cursor:pointer; }
        .task { background:#1e293b; padding:15px; border-radius:12px; margin-bottom:10px; display:flex; justify-content:space-between; text-decoration:none; color:white; border:1px solid #334155; align-items:center;}
        .icon-box { width:35px; height:35px; border-radius:8px; display:flex; align-items:center; justify-content:center; margin-right:10px; }
    </style></head>
    <body>
        <div class="card">
            <p style="margin:0; color:#94a3b8;">Current Balance</p>
            <div class="pts">{{pts}}</div>
            <button class="btn-withdraw" onclick="alert('Need 100 points to withdraw!')">💳 WITHDRAW FUNDS</button>
            <p style="font-size:13px; margin-top:15px;">🎁 Promo Code: <span style="color:#fbbf24; font-weight:bold;">{{coupon}}</span></p>
        </div>
        <div style="text-align:left;">
            <p style="font-size:12px; color:#94a3b8; font-weight:bold; letter-spacing:1px;">AVAILABLE TASKS</p>
            <a href="{{yt}}" target="_blank" class="task"><div style="display:flex; align-items:center;"><div class="icon-box" style="background:#ef4444;"><i class="fab fa-youtube"></i></div>YouTube Subscribe</div><b>+5</b></a>
            <a href="{{fb}}" target="_blank" class="task"><div style="display:flex; align-items:center;"><div class="icon-box" style="background:#3b82f6;"><i class="fab fa-facebook-f"></i></div>Follow Facebook</div><b>+5</b></a>
            <div class="task" style="cursor:pointer;" onclick="location.href='/dashboard?id={{uid}}&name={{name}}&ad_claim=1'"><div style="display:flex; align-items:center;"><div class="icon-box" style="background:#fbbf24; color:black;"><i class="fas fa-play"></i></div>Watch Video Ad</div><b>+10</b></div>
        </div>
    </body></html>
    """, pts=u_data.get('pts', 0), coupon=u_data.get('coupon', '...'), uid=uid, name=name, yt=YT_LINK, fb=FB_LINK)

if __name__ == "__main__":
    # Local testing ke liye port 5000
    app.run(host='0.0.0.0', port=5000)
