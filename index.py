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

# Assets
PIC = "https://i.ibb.co/39V9V4Y3/image.jpg"
YT = "https://www.youtube.com/@USSoccerPulse"
INSTA = "https://www.instagram.com/digital_rockstar_m"
AD_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"
BASE_URL = "https://ultimate-media-search-bot.vercel.app"

def init_fb():
    if not firebase_admin._apps:
        cred_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
        if cred_json:
            try:
                info = json.loads(cred_json)
                cred = credentials.Certificate(info)
                firebase_admin.initialize_app(cred, {'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'})
                return True
            except Exception as e:
                print(f"Firebase Error: {e}")
                return False
    return True

@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == "POST":
        try:
            update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
            if update.message:
                cid = str(update.message.chat.id)
                u_name = update.message.from_user.first_name or "User"
                
                if init_fb():
                    ref = db.reference(f'users/{cid}')
                    if not ref.get():
                        ref.set({"name": u_name, "pts": 10, "coupon": str(uuid.uuid4())[:8]})
                
                btn = telebot.types.InlineKeyboardMarkup()
                url = f"{BASE_URL}/dashboard?id={cid}"
                btn.add(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", web_app=telebot.types.WebAppInfo(url=url)))
                
                msg = f"✨ *Welcome {u_name}!*\n\n💪 Zindagi mein koshish karne walon ki kabhi haar nahi hoti.\n\n💰 10 Bonus Points Credit Ho Gaye Hain!"
                bot.send_photo(cid, PIC, caption=msg, parse_mode="Markdown", reply_markup=btn)
        except Exception as e:
            print(f"Webhook Error: {e}")
    return "Bot is Running", 200

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    init_fb()
    u_ref = db.reference(f'users/{uid}')
    u_data = u_ref.get() or {"pts": 0, "coupon": "NEW"}
    
    if request.args.get('claim') == 'ad':
        current_pts = u_data.get('pts', 0)
        u_ref.update({"pts": current_pts + 10})
        return f"<script>alert('10 Pts Added!'); window.location.href='{AD_LINK}';</script>"

    return render_template_string("""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding:20px; }
        .card { background:#1e293b; border-radius:20px; padding:25px; border:1px solid #334155; margin-bottom:20px; }
        .pts { font-size:50px; color:#fbbf24; font-weight:bold; margin:10px 0; }
        .task { background:#1e293b; padding:15px; border-radius:12px; margin-bottom:12px; display:flex; justify-content:space-between; border:1px solid #334155; text-decoration:none; color:white; align-items:center; }
        .btn-w { background:#fbbf24; color:black; width:100%; padding:15px; border-radius:12px; border:none; font-weight:bold; font-size:16px; }
    </style></head><body>
        <div style="width:85px; height:85px; border-radius:50%; margin:auto; background:url('{{pic}}') center/cover; border:3px solid #fbbf24;"></div>
        <div class="card"><p style="color:#94a3b8; margin:0;">Total Balance</p><div class="pts">{{pts}}</div><p style="font-size:12px; margin:0;">Coupon: {{coupon}}</p></div>
        <div style="text-align:left;"><p style="color:#94a3b8; font-size:14px;">TASKS</p>
            <a href="/dashboard?id={{uid}}&claim=ad" class="task"><div>📺 Watch Video Ad</div><b>+10</b></a>
            <a href="{{yt}}" class="task"><div><i class="fab fa-youtube"></i> YouTube</div><b>+5</b></a>
            <a href="{{insta}}" class="task"><div><i class="fab fa-instagram"></i> Instagram</div><b>+5</b></a>
        </div><br>
        <button class="btn-w" onclick="alert('Min withdrawal: 1000 Points')">WITHDRAW POINTS</button>
    </body></html>
    """, pts=u_data.get('pts', 0), uid=uid, pic=PIC, yt=YT, insta=INSTA, coupon=u_data.get('coupon', '...'))

if __name__ == "__main__":
    app.run(debug=True)
