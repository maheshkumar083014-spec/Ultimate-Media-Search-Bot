import os
import json
import telebot
from flask import Flask, request, render_template
import firebase_admin
from firebase_admin import credentials, db
from openai import OpenAI

# --- PATH CONFIGURATION (ROOT FIX) ---
# Ye logic Vercel ke dynamic root path ko handle karega
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
template_path = os.path.join(base_dir, 'templates')

# --- CONFIGURATION ---
BOT_TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
FB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"
DEEPSEEK_KEY = "sk-783d645ce9e84eb8b954786a016561ea"

# Flask initialization with absolute template path
app = Flask(__name__, template_folder=template_path)
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
    else:
        try:
            # Local environment ke liye path
            local_cred_path = os.path.join(base_dir, "serviceAccountKey.json")
            cred = credentials.Certificate(local_cred_path)
            firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})
        except:
            print("Warning: No Firebase config found!")

# --- TELEGRAM BOT LOGIC ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    name = message.from_user.first_name
    
    user_ref = db.reference(f'users/{user_id}')
    user_data = user_ref.get()
    
    if not user_data:
        user_data = {"points": 100, "plan": "Free", "name": name}
        user_ref.set(user_data)
    
    caption = (f"🚀 *Welcome, {name}!*\n\n"
               f"💰 *Balance:* {user_data.get('points', 0)} Points\n"
               f"🏆 *Plan:* {user_data.get('plan', 'Free')}\n\n"
               "Earn points and chat with AI!")
    
    markup = telebot.types.InlineKeyboardMarkup()
    dashboard_url = f"https://{request.host}/dashboard"
    markup.row(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", url=dashboard_url))
    markup.add(telebot.types.InlineKeyboardButton("💎 Upgrade", callback_data="up"),
               telebot.types.InlineKeyboardButton("🤖 AI Chat", callback_data="ai"))
    
    bot.send_photo(message.chat.id, 
                   "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg", 
                   caption=caption, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def handle_ai(message):
    user_id = str(message.from_user.id)
    user_ref = db.reference(f'users/{user_id}')
    user = user_ref.get()

    if not user: return

    if user.get('plan') == "Free":
        if user.get('points', 0) < 10:
            bot.reply_to(message, "❌ Insufficient points!")
            return
        user_ref.update({"points": user['points'] - 10})

    try:
        response = ai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": message.text}]
        )
        bot.reply_to(message, response.choices[0].message.content)
    except:
        bot.reply_to(message, "⚠️ AI Service busy.")

# --- WEB ROUTES ---
@app.route('/api/index', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    return "Forbidden", 403

@app.route('/')
def index():
    return "Bot is running perfectly!"

@app.route('/dashboard')
def dashboard():
    try:
        return render_template('dashboard.html')
    except Exception as e:
        return f"Error: dashboard.html not found. Path: {template_path}"

app = app
