import os
import telebot
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db
from openai import OpenAI

# Credentials
BOT_TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
DEEPSEEK_KEY = "sk-783d645ce9e84eb8b954786a016561ea"
DB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)
client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

# Firebase Initialization (Fixed for Vercel)
if not firebase_admin._apps:
    firebase_admin.initialize_app(options={'databaseURL': DB_URL})

@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    name = message.from_user.first_name
    ref = db.reference(f'users/{user_id}')
    user_data = ref.get()
    
    if not user_data:
        user_data = {'points': 100, 'plan': 'Free', 'name': name}
        ref.set(user_data)

    welcome_img = "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg"
    caption = (f"👋 *Welcome, {name}!*\n\n"
               f"💰 *Balance:* {user_data.get('points', 0)} Points\n"
               f"🚀 *Plan:* {user_data.get('plan', 'Free')}\n\n"
               "Earn by tasks or chat with DeepSeek AI!")
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", url="https://ultimate-media-search-bot.vercel.app/dashboard"))
    markup.add(telebot.types.InlineKeyboardButton("🤖 AI Chat", callback_data="ai_chat"))
    bot.send_photo(message.chat.id, welcome_img, caption=caption, parse_mode="Markdown", reply_markup=markup)

@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return 'Forbidden', 403

@app.route('/')
def home(): return "Bot is Online!"

@app.route('/dashboard')
def dashboard(): return app.send_static_file('dashboard.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
