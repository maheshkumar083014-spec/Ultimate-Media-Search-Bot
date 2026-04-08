import os
import logging
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

import config
from src import bot_logic
from database import init_firebase

config.setup_logging()
app = Flask(__name__)
init_firebase()

TOKEN = config.get_telegram_token()
bot = Bot(token=TOKEN)
application = ApplicationBuilder().token(TOKEN).build()

# All handlers
application.add_handler(CommandHandler("start", bot_logic.start))
application.add_handler
