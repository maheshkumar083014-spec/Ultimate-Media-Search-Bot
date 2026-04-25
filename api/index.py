import os
import telebot
from flask import Flask, request, render_template_string
import firebase_admin
from firebase_admin import credentials, db

# --- Configuration ---
TOKEN = "8701635891:AAFmgU89KRhd2dhE-PqRY-mBmGy_SxQEGOg"
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# Firebase Initialization
# Note: In production, use a serviceAccountKey.json file or Environment Variables
firebase_config = {
    "databaseURL": "https://earn-bot-2026-default-rtdb.firebaseio.com/"
}

if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json") # Ensure this file exists
    firebase_admin.initialize_app(cred, firebase_config)

# Social Links
SOCIAL_LINKS = {
    "YouTube": "https://youtube.com/@USSoccerPulse",
    "Instagram": "https://instagram.com/digital_rockstar_m",
    "Facebook": "https://facebook.com/OfficialProfile"
}

# --- Bot Logic ---

@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    ref = db.reference(f'users/{user_id}')
    
    # Initialize user if not exists
    if not ref.get():
        ref.set({
            "username": message.from_user.username,
            "points": 0,
            "status": "free",
            "verified": False
        })

    markup = telebot.types.InlineKeyboardMarkup()
    for name, link in SOCIAL_LINKS.items():
        markup.add(telebot.types.InlineKeyboardButton(text=f"Join {name}", url=link))
    
    markup.add(telebot.types.InlineKeyboardButton(text="✅ Verify Membership", callback_data="verify"))
    
    bot.send_photo(
        message.chat.id, 
        "https://i.ibb.co/h1m0cc1W/6a74f155-a6b7-499f-ad34-c1a3989433e0.jpg",
        caption="Welcome to UltimateMediaSearchBot V3! Complete the verification below to start earning.",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify_user(call):
    user_id = str(call.from_user.id)
    db.reference(f'users/{user_id}').update({"verified": True})
    bot.answer_callback_query(call.id, "Verification Successful!")
    bot.send_message(call.message.chat.id, "🎉 Access Granted! Use /dashboard to see your stats.")

# --- Flask Routes ---

@app.route('/')
def index():
    return "Bot is Running."

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route('/dashboard/<user_id>')
def dashboard(user_id):
    user_data = db.reference(f'users/{user_id}').get()
    if not user_data: return "User not found", 404
    
    # Simple render for brevity; use external templates for full HTML
    return f"<h1>Welcome {user_data.get('username')}</h1><p>Points: {user_data.get('points')}</p>"

if __name__ == "__main__":
    app.run(debug=True)
