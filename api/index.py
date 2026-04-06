import os
import telebot
from flask import Flask, request

# Security: Token ko environment variable se fetch karega
TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN, threaded=False)

app = Flask(__name__)

# Aapki Welcome Image
WELCOME_IMAGE_URL = "https://ibb.co/zWJHms9p"

# /start command handler
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name
    
    welcome_text = (
        f"✨ *Hello {user_name}!*\n\n"
        "Welcome to *Ultimate-Media-Search-Bot* 🚀\n\n"
        "Main aapke liye Movies, Music aur Files dhoond sakta hoon.\n"
        "Niche diye gaye button par click karke search shuru karein!"
    )

    # Professional Inline Buttons
    markup = telebot.types.InlineKeyboardMarkup()
    btn_search = telebot.types.InlineKeyboardButton("🔍 Search Media", switch_inline_query_current_chat="")
    btn_dev = telebot.types.InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/YourUsername") # Yahan apna username dalein
    markup.add(btn_search)
    markup.add(btn_dev)

    try:
        # Photo ke sath welcome message
        bot.send_photo(
            message.chat.id, 
            WELCOME_IMAGE_URL, 
            caption=welcome_text, 
            parse_mode='Markdown', 
            reply_markup=markup
        )
    except Exception as e:
        # Agar photo link me error aye to message chala jayega
        bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown', reply_markup=markup)

# Webhook handling (Vercel ke liye zaroori)
@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Forbidden', 403

@app.route('/', methods=['GET'])
def index():
    return "Bot is alive and running!", 200
