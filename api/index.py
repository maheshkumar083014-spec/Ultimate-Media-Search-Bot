import os
import json
import asyncio
import traceback
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db
from telegram import Update, Bot

app = Flask(__name__)

# --- CONFIG ---
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
FB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"
bot = Bot(token=TOKEN)

def init_firebase():
    firebase_config_env = os.getenv("FIREBASE_CONFIG_JSON")
    if not firebase_config_env:
        return "ERROR: FIREBASE_CONFIG_JSON missing in Vercel Env Variables"
    
    if not firebase_admin._apps:
        try:
            config_dict = json.loads(firebase_config_env)
            cred = credentials.Certificate(config_dict)
            firebase_admin.initialize_app(cred, {"databaseURL": FB_URL})
            return "Firebase Init Success"
        except Exception as e:
            return f"Firebase Init Failed: {str(e)}"
    return "Firebase already active"

async def debug_handler(update: Update):
    try:
        # Firebase check
        fb_status = init_firebase()
        
        user_name = update.effective_user.first_name
        chat_id = update.effective_chat.id
        
        # Ek simple message bhej kar check karte hain
        await bot.send_message(
            chat_id=chat_id,
            text=f"✅ Bot Connection OK!\n\n👤 User: {user_name}\n🔥 {fb_status}"
        )
        
    except Exception as e:
        # Agar koi bhi error aayega, ye bot par error message bhej dega
        error_msg = traceback.format_exc()
        await bot.send_message(chat_id=update.effective_chat.id, text=f"❌ DEBUG ERROR:\n\n{error_msg}")

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, bot)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if update.message:
            loop.run_until_complete(debug_handler(update))
            
        loop.close()
        return "ok", 200
    except Exception as e:
        return f"Webhook Critical Error: {str(e)}", 500

@app.route("/")
def home():
    fb_status = init_firebase()
    return f"Bot Debug Mode Active. Firebase: {fb_status}"
