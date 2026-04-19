import os
import json
import logging
import time
from flask import Flask, request, render_template, jsonify
import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, db

# ---------- Setup ----------
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Telegram Bot Token (fallback to hardcoded if env var missing)
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw")
bot = telebot.TeleBot(TOKEN, threaded=False)

# Firebase Admin SDK – Service Account from environment variable
firebase_cred_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY")
if firebase_cred_json:
    cred = credentials.Certificate(json.loads(firebase_cred_json))
else:
    # ⚠️ Fallback dummy credentials – will not work in production!
    # You MUST set FIREBASE_SERVICE_ACCOUNT_KEY on Vercel.
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": "ultimatemediasearch",
        "private_key_id": "dummy",
        "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
        "client_email": "firebase-adminsdk@ultimatemediasearch.iam.gserviceaccount.com",
        "client_id": "dummy",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk%40ultimatemediasearch.iam.gserviceaccount.com"
    })
    logging.warning("⚠️ Using dummy Firebase credentials. Set FIREBASE_SERVICE_ACCOUNT_KEY env var!")

firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

# ---------- Flask Routes ----------
@app.route('/')
def home():
    return "Ultimate Media Search Bot is running."

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return 'Bad request', 400

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id')
    name = request.args.get('name', 'User')
    if not uid:
        return "Missing user ID", 400
    return render_template('dashboard.html', uid=uid, name=name)

# ---------- Point Claim APIs (with Firebase Transactions) ----------
@app.route('/api/claim_ad', methods=['POST'])
def claim_ad():
    data = request.json or {}
    uid = data.get('uid')
    if not uid:
        return jsonify({'error': 'Missing uid'}), 400

    ref = db.reference(f'/users/{uid}')

    def transaction_update(current):
        if current is None:
            current = {'points': 0, 'tasks': {}}
        tasks = current.get('tasks', {})
        now = int(time.time())
        last_claim = tasks.get('ad_last_claim', 0)
        # 24-hour cooldown (86400 seconds)
        if now - last_claim < 86400:
            return current  # abort transaction – no change
        current['points'] = current.get('points', 0) + 25
        tasks['ad_last_claim'] = now
        current['tasks'] = tasks
        return current

    try:
        new_data = ref.transaction(transaction_update)
        return jsonify({'success': True, 'points': new_data.get('points', 0)})
    except Exception as e:
        logging.error(f"Ad claim transaction failed: {e}")
        return jsonify({'error': 'Transaction failed'}), 500

@app.route('/api/claim_social', methods=['POST'])
def claim_social():
    data = request.json or {}
    uid = data.get('uid')
    platform = data.get('platform')
    if not uid or platform not in ['youtube', 'instagram']:
        return jsonify({'error': 'Invalid request'}), 400

    ref = db.reference(f'/users/{uid}')

    def transaction_update(current):
        if current is None:
            current = {'points': 0, 'tasks': {}}
        tasks = current.get('tasks', {})
        task_key = f'{platform}_claimed'
        if tasks.get(task_key):
            return current  # already claimed
        current['points'] = current.get('points', 0) + 100
        tasks[task_key] = True
        current['tasks'] = tasks
        return current

    try:
        new_data = ref.transaction(transaction_update)
        return jsonify({'success': True, 'points': new_data.get('points', 0)})
    except Exception as e:
        logging.error(f"Social claim transaction failed: {e}")
        return jsonify({'error': 'Transaction failed'}), 500

@app.route('/api/get_points')
def get_points():
    uid = request.args.get('uid')
    if not uid:
        return jsonify({'error': 'Missing uid'}), 400
    data = db.reference(f'/users/{uid}').get()
    points = data.get('points', 0) if data else 0
    return jsonify({'points': points})

# ---------- Telegram Bot Handlers ----------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    uid = str(user.id)
    name = user.first_name

    # Save user info to Firebase (non‑critical, fire‑and‑forget)
    ref = db.reference(f'/users/{uid}')
    ref.update({
        'name': name,
        'username': user.username,
        'joined': {'.sv': 'timestamp'}
    })

    dashboard_url = f"https://ultimate-media-search-bot-t7kj.vercel.app/dashboard?id={uid}&name={name}"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🚀 Open Dashboard", url=dashboard_url))
    bot.send_message(
        message.chat.id,
        f"👋 Welcome, {name}!\n\nEarn points by watching ads and following our social channels.\n100 points = $1.00",
        reply_markup=markup
    )

# ---------- Local Development ----------
if __name__ == '__main__':
    bot.remove_webhook()
    bot.polling(none_stop=True)
