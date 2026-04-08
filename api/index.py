import os
import json
import uuid
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template_string
from telegram import Update, Bot, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

app = Flask(__name__)

TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
bot = Bot(token=TOKEN)

PROFILE_PHOTO_URL = "https://i.ibb.co/39V9V4Y3/image.jpg"
YT_LINK = "https://www.youtube.com/@USSoccerPulse"
FB_LINK = "https://www.facebook.com/profile.php?id=61574378159053"
DASHBOARD_BASE_URL = "https://ultimate-media-search-bot.vercel.app"

def init_fb():
    if not firebase_admin._apps:
        cred_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
        if not cred_json:
            return False
        try:
            # FIX: eval ki jagah json.loads use kiya
            cred_dict = json.loads(cred_json) 
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
            })
        except Exception as e:
            print(f"Firebase Init Error: {e}")
            return False
    return True

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == "POST":
        try:
            # Webhook handling
            data = request.get_json(force=True)
            update = Update.de_json(data, bot)
            
            if update.message:
                chat_id = str(update.message.chat_id)
                u_name = update.message.from_user.first_name

                if init_fb():
                    user_ref = db.reference(f'users/{chat_id}')
                    u_data = user_ref.get()
                    if not u_data:
                        user_ref.set({
                            "name": u_name, "pts": 10, 
                            "coupon": str(uuid.uuid4())[:8]
                        })
                    
                    dash_url = f"{DASHBOARD_BASE_URL}/dashboard?id={chat_id}&name={u_name}"
                    kb = InlineKeyboardMarkup([[
                        InlineKeyboardButton("🚀 Open Dashboard", web_app=WebAppInfo(url=dash_url))
                    ]])
                    
                    bot.send_photo(
                        chat_id=chat_id,
                        photo=PROFILE_PHOTO_URL,
                        caption=f"✨ *Welcome {u_name}!* ✨\n\nEarning shuru karein!",
                        parse_mode="Markdown",
                        reply_markup=kb
                    )
        except Exception as e:
            print(f"Error: {e}")
    return "OK", 200

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    init_fb()
    u_ref = db.reference(f'users/{uid}')
    u_data = u_ref.get() or {"pts": 0, "coupon": "..."}
    
    # ... (Baaki UI code wahi rakhein jo aapke paas hai)
    return render_template_string("...", pts=u_data.get('pts', 0), ...)

if __name__ == "__main__":
    app.run(debug=True)
