import os
import json
import uuid
import telebot
import firebase_admin
from flask import Flask, request, render_template_string
from firebase_admin import credentials, db

app = Flask(__name__)

# --- CONFIG ---
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
bot = telebot.TeleBot(TOKEN, threaded=False)
DB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"

# --- FIREBASE INIT ---
def init_fb():
    if not firebase_admin._apps:
        cred_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
        if cred_json:
            try:
                info = json.loads(cred_json)
                cred = credentials.Certificate(info)
                firebase_admin.initialize_app(cred, {'databaseURL': DB_URL})
                return True
            except Exception as e:
                print(f"FB Error: {e}")
        return False
    return True

@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == "POST":
        update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
        if update.message:
            cid = str(update.message.chat.id)
            name = update.message.from_user.first_name or "User"
            
            if init_fb():
                ref = db.reference(f'users/{cid}')
                if not ref.get():
                    ref.set({"name": name, "pts": 10, "coupon": str(uuid.uuid4())[:8]})
            
            markup = telebot.types.InlineKeyboardMarkup()
            url = f"https://ultimate-media-search-bot.vercel.app/dashboard?id={cid}"
            markup.add(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", web_app=telebot.types.WebAppInfo(url=url)))
            
            bot.send_message(cid, f"✅ Welcome {name}!\n\nBot is active and database is connected.", reply_markup=markup)
    return "Bot is Running", 200

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    init_fb()
    u_data = db.reference(f'users/{uid}').get() or {"pts": 0, "coupon": "NEW"}
    return render_template_string("<h1>Dashboard</h1><p>Points: {{pts}}</p>", pts=u_data.get('pts', 0))

# Vercel needs this
app = app
