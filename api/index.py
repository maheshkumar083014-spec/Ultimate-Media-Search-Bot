import os
import telebot
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db
from openai import OpenAI

# Configuration
BOT_TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
FB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"
DEEPSEEK_KEY = "sk-783d645ce9e84eb8b954786a016561ea"

# Initialize Apps
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
ai_client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

# Initialize Firebase (Ensure you have a serviceAccountKey.json or use Env Vars)
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    ref = db.reference(f'users/{user_id}')
    user_data = ref.get() or {"points": 0, "plan": "Free", "name": message.from_user.first_name}
    
    caption = (f"🌟 *Welcome, {user_data['name']}!*\n\n"
               f"💰 *Balance:* {user_data['points']} Points\n"
               f"🏆 *Current Plan:* {user_data['plan']}\n\n"
               "Use the buttons below to earn or chat with AI!")
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", url="https://your-vercel-link.vercel.app/dashboard"))
    markup.add(telebot.types.InlineKeyboardButton("💎 Upgrade Premium", callback_data="upgrade"),
               telebot.types.InlineKeyboardButton("🤖 AI Chat", callback_data="ai_chat"))
    
    bot.send_photo(message.chat.id, 
                   "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg", 
                   caption=caption, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def handle_ai_chat(message):
    user_id = str(message.from_user.id)
    user_ref = db.reference(f'users/{user_id}')
    user = user_ref.get()

    # Point Logic
    if user['plan'] == "Free":
        if user['points'] < 10:
            bot.reply_to(message, "❌ Insufficient points! AI costs 10 points per query.")
            return
        user_ref.update({"points": user['points'] - 10})

    # DeepSeek API Call
    response = ai_client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": message.text}]
    )
    bot.reply_to(message, response.choices[0].message.content)

@app.route('/api/index', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return "OK", 200
