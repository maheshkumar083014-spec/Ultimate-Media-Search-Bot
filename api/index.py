import os
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template
from telegram import Update, Bot, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

app = Flask(__name__)

# Config
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
SMART_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"

def init_firebase():
    if not firebase_admin._apps:
        try:
            # Environment variables se key uthana aur format sahi karna
            p_key = os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n').strip('"').strip("'")
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": "ultimatemediasearch",
                "private_key": p_key,
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "token_uri": "https://oauth2.googleapis.com/token",
            })
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
            })
        except Exception as e:
            print(f"Firebase Init Error: {e}")

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == "POST":
        try:
            data = request.get_json(force=True)
            update = Update.de_json(data, bot)
            
            if update.message:
                chat_id = update.message.chat_id
                user_name = update.message.from_user.first_name
                
                # Dashboard URL (Naya wala)
                dash_url = f"https://ultimate-media-search-bot-t7kj.vercel.app/dashboard?id={chat_id}"
                
                # Keyboard Button with WebApp
                keyboard = [
                    [KeyboardButton("📊 Open Dashboard", web_app=WebAppInfo(url=dash_url))]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                
                bot.send_message(
                    chat_id=chat_id, 
                    text=f"Hello {user_name}! Welcome to Ultimate Media Search Bot.\n\nClick the button below to earn points.",
                    reply_markup=reply_markup
                )
            return "ok", 200
        except Exception as e:
            print(f"Webhook Error: {e}")
            return "error", 500
    return "Bot status: Running"

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', 'Unknown')
    pts = 0
    try:
        init_firebase()
        u_ref = db.reference(f'users/{uid}')
        u_data = u_ref.get()
        if not u_data:
            # Agar naya user hai toh database mein entry bana do
            u_ref.set({"pts": 0, "name": uid})
        else:
            pts = u_data.get('pts', 0)
    except Exception as e:
        print(f"Dashboard DB Error: {e}")
        pts = 0

    return render_template('dashboard.html', pts=pts, uid=uid, ad_link=SMART_LINK)
