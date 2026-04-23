import os
import json
import telebot
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db
from openai import OpenAI

# --- CONFIGURATION ---
BOT_TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
FB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"
DEEPSEEK_KEY = "sk-783d645ce9e84eb8b954786a016561ea"

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
ai_client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

# --- FIREBASE INITIALIZATION (FIXED) ---
if not firebase_admin._apps:
    # Vercel Environment Variable se config uthayega
    fb_config = os.getenv("FIREBASE_SERVICE_ACCOUNT")
    
    if fb_config:
        try:
            cred_dict = json.loads(fb_config)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})
        except Exception as e:
            print(f"Firebase Init Error: {e}")
    else:
        # Agar local run kar rahe ho
        try:
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})
        except:
            print("Warning: No Firebase config found!")

# --- BOT LOGIC ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    name = message.from_user.first_name
    
    # User data fetch or create
    user_ref = db.reference(f'users/{user_id}')
    user_data = user_ref.get()
    
    if not user_data:
        user_data = {"points": 100, "plan": "Free", "name": name}
        user_ref.set(user_data)
    
    caption = (f"🚀 *Welcome, {name}!*\n\n"
               f"💰 *Balance:* {user_data.get('points', 0)} Points\n"
               f"🏆 *Plan:* {user_data.get('plan', 'Free')}\n\n"
               "Earn points by completing tasks and use them for AI Chat!")
    
    markup = telebot.types.InlineKeyboardMarkup()
    # Dashboard URL ko apni Vercel URL se replace karein
    markup.row(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", url=f"https://{request.host}/dashboard"))
    markup.add(telebot.types.InlineKeyboardButton("💎 Upgrade", callback_data="up"),
               telebot.types.InlineKeyboardButton("🤖 AI Chat", callback_data="ai"))
    
    bot.send_photo(message.chat.id, 
                   "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg", 
                   caption=caption, parse_mode="Markdown", reply_markup=markup)

# AI Chat Handler
@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    user_id = str(message.from_user.id)
    user_ref = db.reference(f'users/{user_id}')
    user = user_ref.get()

    if not user: return

    # Point deduction logic
    if user['plan'] == "Free":
        if user['points'] < 10:
            bot.reply_to(message, "❌ Points khatam! Task complete karke points earn karein.")
            return
        user_ref.update({"points": user['points'] - 10})

    try:
        response = ai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": message.text}]
        )
        bot.reply_to(message, response.choices[0].message.content)
    except:
        bot.reply_to(message, "⚠️ AI Service busy hai, thodi der baad try karein.")

# --- VERCEL ROUTES ---
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
    return "Bot is running..."

@app.route('/dashboard')
def dashboard():
    # Templates folder se dashboard serve karega
    return app.send_static_file('dashboard.html')
