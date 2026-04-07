import os
import json
import uuid
import asyncio
from flask import Flask, request, render_template_string
from telegram import Update, Bot, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)

# Config - Environment Variables se uthayega
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw")
bot = Bot(token=TOKEN)
PROFILE_PHOTO_URL = "https://i.ibb.co/39V9V4Y3/image.jpg"
DASHBOARD_BASE_URL = "https://ultimate-media-search-bot.vercel.app"

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
            except: return False
    return True

async def send_start_msg(chat_id, u_name):
    dash_url = f"{DASHBOARD_BASE_URL}/dashboard?id={chat_id}&name={u_name}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Open Dashboard", web_app=WebAppInfo(url=dash_url))]])
    try:
        await bot.send_photo(
            chat_id=chat_id,
            photo=PROFILE_PHOTO_URL,
            caption=f"✨ *Welcome {u_name}!* ✨\n\n💪 Zindagi mein koshish karne walon ki kabhi haar nahi hoti.\n\n📊 Aaj se hi apni earning shuru karein!",
            parse_mode="Markdown",
            reply_markup=kb
        )
    except Exception as e:
        print(f"Photo Error: {e}")

@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == "POST":
        try:
            data = request.get_json(force=True)
            update = Update.de_json(data, bot)
            if update.message:
                chat_id = str(update.message.chat_id)
                u_name = update.message.from_user.first_name
                if init_fb():
                    db.reference(f'users/{chat_id}').update({"name": u_name})
                # Vercel supports running async like this
                asyncio.run(send_start_msg(chat_id, u_name))
        except Exception as e: print(f"Webhook Error: {e}")
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
        return f"<script>alert('10 Points Added!'); window.location.href='/dashboard?id={uid}&name={name}';</script>"

    return render_template_string("""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding:15px; margin:0; }
        .card { background:#1e293b; border-radius:15px; padding:20px; border:1px solid #334155; margin-bottom:15px; }
        .pts { font-size:45px; color:#fbbf24; font-weight:bold; }
        .task { background:#1e293b; padding:15px; border-radius:12px; margin-bottom:10px; display:flex; justify-content:space-between; text-decoration:none; color:white; border:1px solid #334155; align-items:center;}
    </style></head><body>
        <div style="width:100px; height:100px; border-radius:50%; border:2px solid #fbbf24; margin:20px auto; background:url('{{pic}}') center/cover;"></div>
        <div class="card"><p>My Points</p><div class="pts">{{pts}}</div><button style="background:#856404; color:white; width:100%; border:none; padding:10px; border-radius:5px;">WITHDRAW</button></div>
        <div style="text-align:left;"><p>TASKS</p>
            <div class="task" onclick="location.href='/dashboard?id={{uid}}&name={{name}}&ad_claim=1'"><div>Watch Ad</div><b>+10</b></div>
        </div>
    </body></html>
    """, pts=u_data.get('pts', 0), uid=uid, name=name, pic=PROFILE_PHOTO_URL)

# Vercel needs this
app = app
