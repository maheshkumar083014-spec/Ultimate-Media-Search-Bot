import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# Logging setup (Galti dhundne ke liye)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Assalam-o-Alaikum! Main Ultimate Media Search Bot hoon. Kaise madad karun?")

if __name__ == '__main__':
    # Yahan hum baad mein apna Token daalenge
    application = ApplicationBuilder().token('YOUR_BOT_TOKEN_HERE').build()
    
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)
    
    application.run_polling()

