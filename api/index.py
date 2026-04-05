import os
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

app = Flask(__name__)

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

@app.route('/api/index', methods=['POST'])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        # Yahan hum basic start command handle kar rahe hain
        if update.message and update.message.text == "/start":
            bot.send_message(chat_id=update.effective_chat.id, text="Vercel par bot Live hai!")
        return "ok"
    return "done"

@app.route('/')
def index():
    return "Bot is running..."

