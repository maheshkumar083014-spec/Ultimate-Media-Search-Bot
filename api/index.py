import os
import json
import uuid
from flask import Flask, request, render_template_string
import telebot # Humne library thodi change ki hai fast response ke liye
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)

# --- CONFIG ---
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
bot = telebot.TeleBot(TOKEN, threaded=False)

PROFILE_PHOTO_URL = "https://i.ibb.co/39V9V4Y3/image.jpg"
DASHBOARD_BASE_URL = "https://ultimate-media-search-bot.vercel.app"

# --- FIREBASE ---
def init_fb():
    if not firebase_admin._apps:
        cred_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
        if cred_json:
            try:
                cred_dict = json.loads(cred_json)
                firebase_admin.initialize_app(credentials.Certificate(cred_dict), {
                    'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
                })
                return True
            except: return False
    return True

# --- BOT LOGIC ---
@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == "POST":
        update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
        if update.message:
            msg = update.message
            chat_id = str(msg.chat.id)
            u_name = msg.from_user.first_name or "User"

            if init_fb():
                u_ref = db.reference(f'users/{chat_id}')
                if not u_ref.get():
                    u_ref.set({"name": u_name, "pts": 10, "coupon": str(uuid.uuid4())[:8]})

            # Welcome Photo and Button
            markup = telebot.types.InlineKeyboardMarkup()
            dash_url = f"{DASHBOARD_BASE_URL}/dashboard?id={chat_id}&name={u_name}"
            markup.add(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", web_app=telebot.types.WebAppInfo(url=dash_url)))
            
            bot.send_photo(
                chat_id, 
                PROFILE_PHOTO_URL, 
                caption=f"✨ *Welcome {u_name}!* ✨\n\nAbhi earning shuru karein!", 
                parse_mode="Markdown", 
                reply_markup=markup
            )
    return "OK", 200

# --- DASHBOARD ---
@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    init_fb()
    u_ref = db.reference(f'users/{uid}')
    u_data = u_ref.get() or {"pts": 0, "coupon": "NEW"}

    if request.args.get('ad_claim') == '1':
        u_ref.update({"pts": u_data.get('pts', 0) + 10})
        return f"<script>alert('10 Points Added!'); window.location.href='/dashboard?id={uid}&name={name}';</script>"

    return render_template_string("""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding:15px; margin:0; }
        .card { background:#1e293b; border-radius:15px; padding:20px; border:1px solid #334155; margin-bottom:15px; }
        .pts { font-size:45px; color:#fbbf24; font-weight:bold; }
        .btn { background:#fbbf24; color:black; padding:12px; border-radius:10px; width:100%; border:none; font-weight:bold; cursor:pointer; }
    </style></head><body>
        <div style="width:80px; height:80px; border-radius:50%; margin:10px auto; background:url('{{pic}}') center/cover; border:2px solid #fbbf24;"></div>
        <div class="card"><p>Points</p><div class="pts">{{pts}}</div></div>
        <button class="btn" onclick="location.href='/dashboard?id={{uid}}&name={{name}}&ad_claim=1'">📺 Watch Ad (+10 Pts)</button>
    </body></html>
    """, pts=u_data.get('pts', 0), uid=uid, name=name, pic=PROFILE_PHOTO_URL)
