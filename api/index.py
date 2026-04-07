import os
import json
import uuid
from flask import Flask, request, render_template_string
import telebot
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)

# --- CONFIG ---
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
bot = telebot.TeleBot(TOKEN, threaded=False)

# Links
PROFILE_PHOTO_URL = "https://i.ibb.co/39V9V4Y3/image.jpg"
YT_LINK = "https://www.youtube.com/@USSoccerPulse"
INSTA_LINK = "https://www.instagram.com/digital_rockstar_m"
FB_LINK = "https://www.facebook.com/profile.php?id=61574378159053"
AD_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"
DASHBOARD_BASE_URL = "https://ultimate-media-search-bot.vercel.app"

# Motivation
MOTIVATION = "💪 Zindagi mein koshish karne walon ki kabhi haar nahi hoti. Aaj ki mehnat kal ka sukoon hai!"

def init_fb():
    if not firebase_admin._apps:
        cred_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
        if not cred_json:
            return False
        try:
            cred_dict = json.loads(cred_json)
            firebase_admin.initialize_app(credentials.Certificate(cred_dict), {
                'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
            })
        except:
            return False
    return True

@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == "POST":
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        if update.message:
            chat_id = str(update.message.chat.id)
            u_name = update.message.from_user.first_name or "User"

            if init_fb():
                u_ref = db.reference(f'users/{chat_id}')
                if not u_ref.get():
                    u_ref.set({"name": u_name, "pts": 10, "coupon": str(uuid.uuid4())[:8]})

            markup = telebot.types.InlineKeyboardMarkup()
            dash_url = f"{DASHBOARD_BASE_URL}/dashboard?id={chat_id}&name={u_name}"
            markup.add(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", web_app=telebot.types.WebAppInfo(url=dash_url)))
            
            caption = f"✨ *Welcome {u_name}!* ✨\n\n{MOTIVATION}\n\n💰 *Earning:* 10 Pts Bonus mil gaya!"
            bot.send_photo(chat_id, PROFILE_PHOTO_URL, caption=caption, parse_mode="Markdown", reply_markup=markup)
    return "OK", 200

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    init_fb()
    u_ref = db.reference(f'users/{uid}')
    u_data = u_ref.get() or {"pts": 0, "coupon": "NEW"}

    if request.args.get('claim') == 'ad':
        u_ref.update({"pts": u_data.get('pts', 0) + 10})
        return f"<script>alert('10 Points Added!'); window.location.href='{AD_LINK}';</script>"

    return render_template_string("""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding:15px; margin:0; }
        .card { background:#1e293b; border-radius:15px; padding:20px; border:1px solid #334155; margin-bottom:15px; }
        .pts { font-size:45px; color:#fbbf24; font-weight:bold; }
        .task { background:#1e293b; padding:12px; border-radius:10px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center; border:1px solid #334155; text-decoration:none; color:white; }
        .btn-withdraw { background:#fbbf24; color:black; padding:12px; border-radius:10px; width:100%; border:none; font-weight:bold; cursor:pointer; }
    </style></head><body>
        <div style="width:70px; height:70px; border-radius:50%; border:2px solid #fbbf24; margin:10px auto; background:url('{{pic}}') center/cover;"></div>
        <div class="card"><p>Wallet Balance</p><div class="pts">{{pts}}</div><p>Coupon: {{coupon}}</p></div>
        <div style="text-align:left;"><p>TASKS</p>
            <a href="/dashboard?id={{uid}}&claim=ad" class="task"><div>📺 Watch Ad</div><b>+10</b></a>
            <a href="{{yt}}" class="task"><div><i class="fab fa-youtube"></i> YouTube</div><b>+5</b></a>
            <a href="{{insta}}" class="task"><div><i class="fab fa-instagram"></i> Instagram</div><b>+5</b></a>
        </div><br>
        <button class="btn-withdraw" onclick="alert('Min withdraw 1000 pts')">WITHDRAW</button>
    </body></html>
    """, pts=u_data.get('pts', 0), uid=uid, name=name, pic=PROFILE_PHOTO_URL, yt=YT_LINK, insta=INSTA_LINK, coupon=u_data.get('coupon', '...'))

if __name__ == "__main__":
    app.run(debug=True)
