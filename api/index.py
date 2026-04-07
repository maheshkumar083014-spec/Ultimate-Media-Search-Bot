import os
import json
import uuid
import asyncio
from flask import Flask, request, render_template_string
from telegram import Update, Bot, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)

# --- CONFIGURATION ---
# Token aur Links
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
bot = Bot(token=TOKEN)

PROFILE_PHOTO_URL = "https://i.ibb.co/39V9V4Y3/image.jpg"
YT_LINK = "https://www.youtube.com/@USSoccerPulse"
FB_LINK = "https://www.facebook.com/profile.php?id=61574378159053"
DASHBOARD_BASE_URL = "https://ultimate-media-search-bot.vercel.app"

# --- FIREBASE SETUP ---
def init_fb():
    if not firebase_admin._apps:
        cred_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
        if cred_json:
            try:
                cred_dict = json.loads(cred_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
                })
                return True
            except Exception as e:
                print(f"Firebase Error: {e}")
                return False
    return True

# --- ASYNC WELCOME MESSAGE ---
async def send_welcome(chat_id, u_name):
    dash_url = f"{DASHBOARD_BASE_URL}/dashboard?id={chat_id}&name={u_name}"
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🚀 Open Dashboard", web_app=WebAppInfo(url=dash_url))
    ]])
    
    try:
        await bot.send_photo(
            chat_id=chat_id,
            photo=PROFILE_PHOTO_URL,
            caption=(
                f"✨ *Welcome {u_name}!* ✨\n\n"
                f"💪 Zindagi mein koshish karne walon ki kabhi haar nahi hoti.\n\n"
                f"📊 Aaj se hi apni earning shuru karein!\n\n"
                f"Niche button par click karke dashboard kholein."
            ),
            parse_mode="Markdown",
            reply_markup=kb
        )
    except Exception as e:
        print(f"Telegram Send Error: {e}")

# --- ROUTES ---
@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == "POST":
        try:
            data = request.get_json(force=True)
            update = Update.de_json(data, bot)
            if update and update.message:
                chat_id = str(update.message.chat_id)
                u_name = update.message.from_user.first_name or "User"
                
                if init_fb():
                    user_ref = db.reference(f'users/{chat_id}')
                    if not user_ref.get():
                        user_ref.set({
                            "name": u_name,
                            "pts": 10,
                            "coupon": str(uuid.uuid4())[:8]
                        })
                
                # Running async function in Flask
                asyncio.run(send_welcome(chat_id, u_name))
        except Exception as e:
            print(f"Webhook Error: {e}")
    return "Bot is Active", 200

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    init_fb()
    
    u_ref = db.reference(f'users/{uid}')
    u_data = u_ref.get() or {"pts": 0, "coupon": "NEW-USER"}
    
    if request.args.get('ad_claim') == '1':
        new_pts = u_data.get('pts', 0) + 10
        u_ref.update({"pts": new_pts})
        return render_template_string(f"<script>alert('10 Points Added!'); window.location.href='/dashboard?id={uid}&name={name}';</script>")

    return render_template_string("""
    <!DOCTYPE html><html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding:15px; margin:0; }
        .profile-img { width:80px; height:80px; border-radius:50%; border:3px solid #fbbf24; margin:10px auto; background:url('{{pic}}') center/cover; }
        .card { background:#1e293b; border-radius:15px; padding:20px; border:1px solid #334155; margin-bottom:15px; }
        .pts { font-size:45px; color:#fbbf24; font-weight:bold; }
        .btn-withdraw { background:#856404; color:white; padding:10px; border-radius:10px; width:100%; border:none; font-weight:bold; margin-top:10px;}
        .task { background:#1e293b; padding:15px; border-radius:12px; margin-bottom:10px; display:flex; justify-content:space-between; text-decoration:none; color:white; border:1px solid #334155; align-items:center;}
        .icon-red { background:red; width:30px; height:30px; border-radius:5px; display:flex; align-items:center; justify-content:center; margin-right:10px;}
    </style></head>
    <body>
        <div class="profile-img"></div>
        <div class="card">
            <p>My Total Points</p><div class="pts">{{pts}}</div>
            <button class="btn-withdraw">💳 WITHDRAW (100 MIN)</button>
            <p style="font-size:12px; margin-top:10px;">🎁 Coupon: <b style="color:#fbbf24;">{{coupon}}</b></p>
        </div>
        <div style="text-align:left;">
            <p style="font-size:12px; color:#94a3b8;">DAILY TASKS</p>
            <a href="{{yt}}" target="_blank" class="task"><div style="display:flex; align-items:center;"><div class="icon-red"><i class="fab fa-youtube"></i></div>YouTube</div><b>+5</b></a>
            <div class="task" style="cursor:pointer;" onclick="location.href='/dashboard?id={{uid}}&name={{name}}&ad_claim=1'"><div style="display:flex; align-items:center;"><div class="icon-red" style="background:#fbbf24; color:black;"><i class="fas fa-play"></i></div>Watch Ad</div><b>+10</b></div>
        </div>
    </body></html>
    """, pts=u_data.get('pts', 0), coupon=u_data.get('coupon', '...'), uid=uid, name=name, yt=YT_LINK, pic=PROFILE_PHOTO_URL)

# Vercel requirements
app = app
