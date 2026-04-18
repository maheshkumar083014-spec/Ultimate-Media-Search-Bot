import os, firebase_admin, logging
from firebase_admin import credentials, db
from flask import Flask, request, render_template
from telegram import Update, Bot, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

# Firebase initialization function with safety
def init_firebase():
    if not firebase_admin._apps:
        try:
            # Vercel environment variables se data uthana
            raw_key = os.getenv("FIREBASE_PRIVATE_KEY")
            if raw_key:
                p_key = raw_key.replace('\\n', '\n').strip('"').strip("'")
                cred_dict = {
                    "type": "service_account",
                    "project_id": "ultimatemediasearch",
                    "private_key": p_key,
                    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
                })
        except Exception as e:
            print(f"Firebase Error: {e}")

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == "POST":
        try:
            # 1. Message receive karna
            update = Update.de_json(request.get_json(force=True), bot)
            if update.message:
                chat_id = update.message.chat_id
                
                # 2. Firebase ko background mein connect karna
                init_firebase()
                
                # 3. Simple Test Message (Sabse pehle ye jayega)
                bot.send_message(chat_id=chat_id, text="🚀 Bot active ho gaya hai!")
                
                # Dashboard Button
                dash_url = f"https://{request.host}/dashboard?id={chat_id}"
                menu = ReplyKeyboardMarkup([[KeyboardButton("📊 Dashboard", web_app=WebAppInfo(url=dash_url))]], resize_keyboard=True)
                bot.send_message(chat_id=chat_id, text="Niche button par click karein:", reply_markup=menu)
                
            return "ok", 200
        except Exception as e:
            print(f"Webhook Error: {e}")
            return "error", 500
    return "Bot is Running"

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', 'Unknown')
    init_firebase()
    try:
        u_data = db.reference(f'users/{uid}').get() or {"pts": 0}
    except:
        u_data = {"pts": 0}
    return render_template('dashboard.html', pts=u_data.get('pts', 0), uid=uid)
