import os
import json
import telebot
from flask import Flask, request, render_template
import firebase_admin
from firebase_admin import credentials, db
from openai import OpenAI

# 1. Pehle paths set karein
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
template_path = os.path.join(base_dir, 'templates')

# 2. PHIR 'app' object define karein (Ye zaroori hai!)
app = Flask(__name__, template_folder=template_path)

# 3. Phir baaki configs
BOT_TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
FB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"
DEEPSEEK_KEY = "sk-783d645ce9e84eb8b954786a016561ea"

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
ai_client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

# --- FIREBASE INITIALIZATION ---
if not firebase_admin._apps:
    fb_config = os.getenv("FIREBASE_SERVICE_ACCOUNT")
    if fb_config:
        try:
            cred_dict = json.loads(fb_config)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})
        except Exception as e:
            print(f"Firebase Init Error: {e}")

# --- WEB ROUTES (Ab @app kaam karega) ---
@app.route('/')
def index():
    return "Bot is running perfectly!"

@app.route('/dashboard')
def dashboard():
    try:
        return render_template('dashboard.html')
    except:
        return "Dashboard file not found in templates folder."

@app.route('/api/index', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    return "Forbidden", 403

# --- BOT LOGIC ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    name = message.from_user.first_name
    
    # User data (Silent check)
    user_ref = db.reference(f'users/{user_id}')
    user_data = user_ref.get()
    
    if not user_data:
        user_data = {"points": 100, "plan": "Free", "name": name}
        user_ref.set(user_data)
    
    caption = f"🚀 *Welcome, {name}!*\n💰 *Balance:* {user_data.get('points', 0)} Points"
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", url=f"https://{request.host}/dashboard"))
    
    bot.send_message(message.chat.id, caption, parse_mode="Markdown", reply_markup=markup)

# Vercel ko 'app' dikhana zaroori hai
app = app
