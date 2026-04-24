import telebot
from flask import Flask, request, jsonify, redirect
import firebase_admin
from firebase_admin import credentials, db
import os

# ===== CONFIG =====
BOT_TOKEN = "YOUR_BOT_TOKEN"
WEBHOOK_URL = "https://your-vercel-url.vercel.app/api/index"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ===== FIREBASE INIT =====
if not firebase_admin._apps:
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": "ultimatemediasearch",
        "private_key_id": "YOUR_PRIVATE_KEY_ID",
        "private_key": "YOUR_PRIVATE_KEY".replace("\\n", "\n"),
        "client_email": "YOUR_CLIENT_EMAIL",
        "client_id": "YOUR_CLIENT_ID",
        "token_uri": "https://oauth2.googleapis.com/token"
    })

    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"
    })

# ===== START COMMAND (MATCHES YOUR DASHBOARD uid PARAM) =====
@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    name = message.from_user.first_name or "User"

    ref = db.reference(f'users/{uid}')
    user = ref.get()

    if not user:
        ref.set({
            "name": name,
            "points": 0,
            "plan": "Free",
            "joined": {".sv": "timestamp"},
            "tasks_completed": {}
        })

    # IMPORTANT: dashboard expects ?uid=
    dashboard_url = f"https://your-vercel-url.vercel.app/dashboard?uid={uid}"

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("🚀 Open Dashboard", url=dashboard_url)
    )

    bot.send_message(
        message.chat.id,
        f"👋 Welcome {name}!\n\n💰 Complete tasks & earn points!",
        reply_markup=markup
    )

# ===== UPGRADE COMMAND =====
@bot.message_handler(commands=['upgrade'])
def upgrade(message):
    bot.send_message(
        message.chat.id,
        "💎 Upgrade Plan\n\nSend ₹100 to UPI and contact admin.\nAfter payment you will get:\n\n• 2x Earnings\n• Unlimited AI\n• Promote Button"
    )

# ===== WEBHOOK HANDLER =====
@app.route('/api/index', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return jsonify({"status": "ok"})
    return "Invalid", 403

# ===== HEALTH CHECK =====
@app.route('/api/index', methods=['GET'])
def home():
    return "Bot Running ✅"

# ===== SET WEBHOOK =====
@app.route('/api/set_webhook')
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    return "Webhook Set ✅"

# ===== OPTIONAL: AI CHAT API =====
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get("message", "")

    # Demo response (you can connect OpenAI later)
    return jsonify({
        "reply": f"🤖 You said: {message}"
    })

# ===== VERCEL ENTRY =====
def handler(request):
    return app(request.environ, lambda status, headers: None)
