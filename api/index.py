import os
import telebot
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db
from openai import OpenAI

# Configuration
BOT_TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
DEEPSEEK_KEY = "sk-783d645ce9e84eb8b954786a016561ea"
DB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)
client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

# Firebase Init
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_credentials.json") # Add your JSON file or use default
    firebase_admin.initialize_app(cred, {'databaseURL': DB_URL})

@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    ref = db.reference(f'users/{user_id}')
    user_data = ref.get()
    
    if not user_data:
        user_data = {'points': 0, 'plan': 'Free', 'name': message.from_user.first_name}
        ref.set(user_data)

    welcome_img = "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg"
    caption = (f"👋 *Welcome, {user_data['name']}!*\n\n"
               f"💰 *Balance:* {user_data['points']} Points\n"
               f"🚀 *Plan:* {user_data['plan']}\n\n"
               "Earn points by completing tasks and chatting with AI!")
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", url="https://your-vercel-app.vercel.app"))
    markup.add(telebot.types.InlineKeyboardButton("🤖 AI Chat", callback_data="ai_chat"))
    bot.send_photo(message.chat.id, welcome_img, caption=caption, parse_mode="Markdown", reply_markup=markup)

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200

@app.route('/')
def index():
    return "Bot is Running!"

if __name__ == "__main__":
    app.run(debug=True)
