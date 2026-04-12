import os
import telebot
import firebase_admin
from firebase_admin import credentials, db
from telebot import types

# ===== CONFIGURATION =====
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw")
FIREBASE_DB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app"

# Firebase init (dummy credentials for demo; set GOOGLE_APPLICATION_CREDENTIALS in Vercel for production)
try:
    firebase_admin.initialize_app(
        credentials.Certificate({
            "type": "service_account",
            "project_id": "ultimatemediasearch",
            "private_key_id": "dummy",
            "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
            "client_email": "firebase-adminsdk@ultimatemediasearch.iam.gserviceaccount.com",
            "client_id": "",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": ""
        }),
        {'databaseURL': FIREBASE_DB_URL}
    )
except ValueError:
    pass

db_ref = db.reference()
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# ===== HELPERS =====
def get_user(tg_id):
    user_ref = db_ref.child(f'users/{tg_id}')
    user = user_ref.get()
    if not user:
        user = {'balance': 0, 'referrals': [], 'referred_by': None}
        user_ref.set(user)
    return user

def update_balance(tg_id, amount):
    db_ref.child(f'users/{tg_id}/balance').transaction(lambda b: (b or 0) + amount)

# ===== COMMANDS =====
@bot.message_handler(commands=['start'])
def start(message):
    tg_id = str(message.from_user.id)
    args = message.text.split()
    referrer = args[1] if len(args) > 1 else None

    user = get_user(tg_id)
    if referrer and referrer != tg_id and not user.get('referred_by'):
        db_ref.child(f'users/{tg_id}/referred_by').set(referrer)
        db_ref.child(f'users/{referrer}/referrals').child(tg_id).set(True)
        update_balance(referrer, 500)
        bot.send_message(referrer, "🎉 New referral! +500 points added.")

    markup = types.InlineKeyboardMarkup()
    webapp = types.WebAppInfo(url=f"https://ultimate-media-search-bot-yawg.vercel.app?tg_id={tg_id}")
    markup.add(types.InlineKeyboardButton("📊 Open Dashboard", web_app=webapp))

    bot.send_message(
        message.chat.id,
        "👋 *Welcome to Ultimate Media Search!*\n\n"
        "📺 Watch ads • 30s = +5 pts\n"
        "🌐 Social tasks = +10 pts\n"
        "👥 Referral = +500 pts",
        parse_mode="Markdown",
        reply_markup=markup
    )

# ===== WEBHOOK HELPERS =====
def set_webhook(url):
    bot.remove_webhook()
    bot.set_webhook(url + "/api/webhook")

def process_update(data):
    bot.process_new_updates([telebot.types.Update.de_json(data)])
