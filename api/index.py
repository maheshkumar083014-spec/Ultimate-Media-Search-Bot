import os
import telebot
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template

# Path fix for Vercel
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
app = Flask(__name__, template_folder=template_dir)

# BOT CONFIG
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
bot = telebot.TeleBot(TOKEN, threaded=False)

def init_firebase():
    if not firebase_admin._apps:
        try:
            # Firebase Env Variables are mandatory on Vercel
            raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n')
            email = os.getenv("FIREBASE_CLIENT_EMAIL")
            if raw_key and email:
                cred = credentials.Certificate({
                    "type": "service_account",
                    "project_id": "ultimatemediasearch",
                    "private_key": raw_key,
                    "client_email": email,
                    "token_uri": "https://oauth2.googleapis.com/token",
                })
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
                })
        except: pass

@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == 'POST':
        try:
            json_str = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_str)
            bot.process_new_updates([update])
        except Exception as e:
            print(f"Webhook Error: {e}")
        return "OK", 200
    return "<h1>Bot is Online 🚀</h1>", 200

@bot.message_handler(commands=['start'])
def start_msg(message):
    uid = message.chat.id
    name = message.from_user.first_name
    # Dynamic URL with user data
    dash_url = f"https://ultimate-media-search-bot-t7kj.vercel.app/dashboard?id={uid}&name={name}"
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", url=dash_url))
    
    welcome_text = (
        f"<b>Hello {name}! 👋</b>\n\n"
        "Welcome to <b>Ultimate Media Earn Bot</b>.\n"
        "Daily tasks poore karein aur cash earn karein.\n\n"
        "👇 Dashboard kholne ke liye niche click karein!"
    )
    bot.send_message(uid, welcome_text, parse_mode="HTML", reply_markup=markup)

@app.route('/dashboard')
def dashboard():
    # Getting real data from URL params
    uid = request.args.get('id', 'Unknown')
    user_name = request.args.get('name', 'Explorer')
    pts = 0
    init_firebase()
    try:
        if firebase_admin._apps:
            u_data = db.reference(f'users/{uid}').get()
            if u_data: pts = u_data.get('pts', 0)
    except: pts = 0
    return render_template('dashboard.html', pts=pts, uid=uid, user_name=user_name)
