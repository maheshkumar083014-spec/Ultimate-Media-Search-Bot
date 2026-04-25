import os
import json
import telebot
from flask import Flask, request, render_template_string
import firebase_admin
from firebase_admin import credentials, db

# --- 1. Vercel Environment Variables Se Data Lena ---
TOKEN = os.environ.get('BOT_TOKEN')
DB_URL = os.environ.get('FIREBASE_DB_URL')
# Firebase ki poori JSON string variables se uthayega
SERVICE_ACCOUNT_JSON = os.environ.get('FIREBASE_SERVICE_ACCOUNT')

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# --- 2. Firebase Bina File Ke Connect Karna ---
if not firebase_admin._apps:
    try:
        # JSON string ko dictionary mein badal kar use karna
        info = json.loads(SERVICE_ACCOUNT_JSON)
        cred = credentials.Certificate(info)
        firebase_admin.initialize_app(cred, {'databaseURL': DB_URL})
        print("✅ Firebase Connected Successfully!")
    except Exception as e:
        print(f"❌ Firebase Setup Error: {e}")

# --- 3. Bot Logic ---

@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    # Firebase mein user check karein
    user_ref = db.reference(f'users/{user_id}').get()
    
    if not user_ref:
        db.reference(f'users/{user_id}').set({
            "username": message.from_user.username,
            "points": 0,
            "status": "free"
        })

    welcome_text = (
        "✨ *Welcome to Ultimate Media Search Bot V3*\n\n"
        "Aapka account successfully sync ho gaya hai.\n"
        "Ab aap earning aur media search shuru kar sakte hain!"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")

# --- 4. Webhook Route (Vercel Ke Liye) ---

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route('/')
def index():
    return "<h1>Bot Status: ONLINE ✅</h1><p>Vercel Environment variables are working.</p>"

# Web Dashboard (Short Version)
@app.route('/dashboard/<user_id>')
def dashboard(user_id):
    user_data = db.reference(f'users/{user_id}').get()
    if not user_data:
        return "User Not Found", 404
    return f"<h2>User: {user_data['username']}</h2><p>Points: {user_data['points']}</p>"

if __name__ == "__main__":
    app.run(debug=True)
