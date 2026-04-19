import os
import json
import logging
import time
from flask import Flask, request, render_template, jsonify
import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, db, exceptions

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ---------- Telegram Bot ----------
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw")
bot = telebot.TeleBot(TOKEN, threaded=False)

# ---------- Firebase Initialization (Robust) ----------
firebase_enabled = False
firebase_cred_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY")

if firebase_cred_json:
    try:
        cred_dict = json.loads(firebase_cred_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
        })
        firebase_enabled = True
        logger.info("✅ Firebase initialized successfully.")
    except json.JSONDecodeError as e:
        logger.critical(f"❌ FIREBASE_SERVICE_ACCOUNT_KEY is not valid JSON: {e}")
    except exceptions.FirebaseError as e:
        logger.critical(f"❌ Firebase initialization failed: {e}")
else:
    logger.critical("❌ FIREBASE_SERVICE_ACCOUNT_KEY environment variable not set.")

# ---------- Helper: Safe DB Reference ----------
def get_user_ref(uid):
    if not firebase_enabled:
        raise RuntimeError("Firebase is not configured.")
    return db.reference(f'/users/{uid}')

# ---------- Flask Routes ----------
@app.route('/')
def home():
    return "Ultimate Media Search Bot is live."

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

@app.route('/api/get_points')
def get_points():
    if not firebase_enabled:
        return jsonify({'error': 'Service unavailable'}), 503
    uid = request.args.get('uid')
    if not uid:
        return jsonify({'error': 'Missing uid'}), 400
    try:
        data = get_user_ref(uid).get()
        points = data.get('points', 0) if data else 0
        return jsonify({'points': points})
    except Exception as e:
        logger.error(f"Error fetching points: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/get_user_data')
def get_user_data():
    if not firebase_enabled:
        return jsonify({'error': 'Service unavailable'}), 503
    uid = request.args.get('uid')
    if not uid:
        return jsonify({'error': 'Missing uid'}), 400
    try:
        data = get_user_ref(uid).get()
        return jsonify(data if data else {})
    except Exception as e:
        logger.error(f"Error fetching user data: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/claim_ad', methods=['POST'])
def claim_ad():
    if not firebase_enabled:
        return jsonify({'error': 'Service unavailable'}), 503
    data = request.json or {}
    uid = data.get('uid')
    if not uid:
        return jsonify({'error': 'Missing uid'}), 400

    ref = get_user_ref(uid)

    def transaction_update(current):
        if current is None:
            current = {'points': 0, 'tasks': {}}
        tasks = current.get('tasks', {})
        now = int(time.time())
        last_claim = tasks.get('ad_last_claim', 0)
        # 24-hour cooldown
        if now - last_claim < 86400:
            return current  # abort
        current['points'] = current.get('points', 0) + 25
        tasks['ad_last_claim'] = now
        current['tasks'] = tasks
        return current

    try:
        new_data = ref.transaction(transaction_update)
        return jsonify({'success': True, 'points': new_data.get('points', 0)})
    except Exception as e:
        logger.error(f"Ad claim transaction failed: {e}")
        return jsonify({'error': 'Transaction failed'}), 500

@app.route('/api/claim_social', methods=['POST'])
def claim_social():
    if not firebase_enabled:
        return jsonify({'error': 'Service unavailable'}), 503
    data = request.json or {}
    uid = data.get('uid')
    platform = data.get('platform')
    if not uid or platform not in ['youtube', 'instagram']:
        return jsonify({'error': 'Invalid request'}), 400

    ref = get_user_ref(uid)

    def transaction_update(current):
        if current is None:
            current = {'points': 0, 'tasks': {}}
        tasks = current.get('tasks', {})
        task_key = f'{platform}_claimed'
        if tasks.get(task_key):
            return current
        current['points'] = current.get('points', 0) + 100
        tasks[task_key] = True
        current['tasks'] = tasks
        return current

    try:
        new_data = ref.transaction(transaction_update)
        return jsonify({'success': True, 'points': new_data.get('points', 0)})
    except Exception as e:
        logger.error(f"Social claim transaction failed: {e}")
        return jsonify({'error': 'Transaction failed'}), 500

# ---------- Telegram Handlers ----------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    uid = str(user.id)
    name = user.first_name

    if firebase_enabled:
        try:
            ref = get_user_ref(uid)
            ref.update({
                'name': name,
                'username': user.username,
                'joined': {'.sv': 'timestamp'}
            })
        except Exception as e:
            logger.error(f"Failed to save user: {e}")

    dashboard_url = f"https://ultimate-media-search-bot-t7kj.vercel.app/dashboard?id={uid}&name={name}"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🚀 Open Dashboard", url=dashboard_url))
    bot.send_message(
        message.chat.id,
        f"👋 Welcome, {name}!\n\n"
        "💰 Earn points by watching ads and following our social channels.\n"
        "💵 100 points = $1.00",
        reply_markup=markup
    )

# ---------- Local Development (not used on Vercel) ----------
if __name__ == '__main__':
    bot.remove_webhook()
    bot.polling(none_stop=True)
