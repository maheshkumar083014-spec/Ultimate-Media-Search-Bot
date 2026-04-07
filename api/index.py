import os
import time
import uuid
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template_string
from telegram import Update, Bot, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

app = Flask(__name__)

# --- CONFIGURATION ---
# Aapka Naya Telegram Token
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
bot = Bot(token=TOKEN)

# Aapki Profile Photo Link (Imagebb se)
# Bhai, maine yahan aapki dynamic photo ka link update kar diya hai.
PROFILE_PHOTO_URL = "https://i.ibb.co/39V9V4Y3/image.jpg"

# Social Links aur Ad Link
YT_LINK = "https://www.youtube.com/@USSoccerPulse"
INSTA_LINK = "https://www.instagram.com/digital_rockstar_m"
FB_LINK = "https://www.facebook.com/profile.php?id=61574378159053"
AD_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"

# Vercel Deployment Link (Dashboard ke liye)
DASHBOARD_BASE_URL = "https://ultimate-media-search-bot.vercel.app"

# Firebase Initialization
def init_fb():
    if not firebase_admin._apps:
        # Vercel Environment Variable se Private Key uthana
        cred_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
        if not cred_json:
            print("FIREBASE_SERVICE_ACCOUNT not found in environment variables.")
            return False
        
        try:
            # JSON string ko dict mein convert karna
            cred_dict = eval(cred_json) 
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
            })
        except Exception as e:
            print(f"Error initializing Firebase: {e}")
            return False
    return True

# --- TELEGRAM BOT LOGIC ---
@app.route('/', methods=['POST'])
def webhook():
    if request.method == "POST":
        try:
            update = Update.de_json(request.get_json(force=True), bot)
            if not update or not update.message: return "!", 200
            
            chat_id = str(update.message.chat_id)
            u_name = update.message.from_user.first_name

            if init_fb():
                user_ref = db.reference(f'users/{chat_id}')
                u_data = user_ref.get()

                if not u_data:
                    # Naya user save karein aur coupon de
                    user_ref.set({
                        "name": u_name,
                        "pts": 10,  # Signup bonus
                        "coupon": str(uuid.uuid4())[:8],
                        "last_ad": 0
                    })
                
                # dashboard link user ke data ke saath
                dash_url = f"{DASHBOARD_BASE_URL}/dashboard?id={chat_id}&name={u_name}"
                
                # --- PHOTO + WELCOME TEXT ---
                kb = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🚀 Open Dashboard", web_app=WebAppInfo(url=dash_url))
                ]])
                
                # Bhai, yahan 'send_photo' use kiya hai photo aur text saath bhejne ke liye.
                bot.send_photo(
                    chat_id=chat_id,
                    photo=PROFILE_PHOTO_URL, # Aapki dynamic image
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
            print(f"Webhook Error: {e}")
            
    return "Bot is running", 200

# --- DASHBOARD UI (No Changes needed here) ---
@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    init_fb()
    
    u_ref = db.reference(f'users/{uid}')
    u_data = u_ref.get() or {"pts": 0, "coupon": "...", "last_ad": 0}
    
    # Points update logic for ads (no changes)
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
        .card { background:#1e293b; border-radius:15px; padding:20px; border:1px solid #334155; margin-bottom:15px; }
        .pts { font-size:45px; color:#fbbf24; font-weight:bold; }
        .btn-withdraw { background:#856404; color:#facc15; padding:10px; border-radius:10px; width:100%; border:none; font-weight:bold; font-size:16px; margin-top:10px;}
        .task { background:#1e293b; padding:15px; border-radius:12px; margin-bottom:10px; display:flex; justify-content:space-between; text-decoration:none; color:white; border:1px solid #334155; align-items:center;}
        .icon-box { width:35px; height:35px; border-radius:8px; display:flex; align-items:center; justify-content:center; }
    </style></head>
    <body>
        <div class="card">
            <p>My Points</p><div class="pts">{{pts}}</div>
            <button class="btn-withdraw">💳 WITHDRAW (100 MIN)</button>
            <p style="font-size:13px;">🎁 Coupon: <b style="color:#fbbf24;">{{coupon}}</b></p>
        </div>
        <div style="text-align:left;">
            <p style="font-size:12px; color:#94a3b8; font-weight:bold;">DAILY TASKS</p>
            <a href="{{yt}}" target="_blank" class="task"><div style="display:flex; align-items:center;"><div class="icon-box" style="background:red;"><i class="fab fa-youtube"></i></div>YouTube</div><b>+5</b></a>
            <a href="{{fb}}" target="_blank" class="task"><div style="display:flex; align-items:center;"><div class="icon-box" style="background:#1877f2;"><i class="fab fa-facebook-f"></i></div>Facebook</div><b>+5</b></a>
            <div class="task" onclick="location.href='/dashboard?id={{uid}}&name={{name}}&ad_claim=1'"><div style="display:flex; align-items:center;"><div class="icon-box" style="background:#fbbf24; color:black;"><i class="fas fa-play"></i></div>Watch Ad</div><b>+10</b></div>
        </div>
    </body></html>
    """, pts=u_data.get('pts', 0), coupon=u_data.get('coupon', '...'), uid=uid, name=name, yt=YT_LINK, fb=FB_LINK)

if __name__ == "__main__":
    app.run(debug=True)
