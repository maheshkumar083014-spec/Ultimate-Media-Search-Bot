import os
import json
import time
import secrets
import logging
import flask
from flask import Flask, request, render_template, redirect, url_for
import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, db
import requests  # 👈 used for DeepSeek API

# ------------------------------------------------------------
# Logging & Configuration
# ------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables (set in Vercel)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
FIREBASE_DB_URL = os.environ.get("FIREBASE_DB_URL")
FIREBASE_SERVICE_ACCOUNT = os.environ.get("FIREBASE_SERVICE_ACCOUNT")  # JSON string
WELCOME_IMAGE_URL = os.environ.get("WELCOME_IMAGE_URL")
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "change_me_strong_secret")
UPI_ID = os.environ.get("UPI_ID", "8543083014@mbk")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")  # Telegram chat ID for alerts
VERCEL_URL = os.environ.get("VERCEL_URL")  # provided by Vercel

# ------------------------------------------------------------
# Firebase Admin Initialization
# ------------------------------------------------------------
try:
    cred_json = json.loads(FIREBASE_SERVICE_ACCOUNT)
    cred = credentials.Certificate(cred_json)
    firebase_admin.initialize_app(cred, {
        'databaseURL': FIREBASE_DB_URL
    })
    logger.info("Firebase Admin initialized successfully.")
except Exception as e:
    logger.error(f"Firebase initialization failed: {e}")
    raise e

# Database references
users_ref = db.reference('users')
payments_ref = db.reference('payments')
tasks_ref = db.reference('tasks')
auth_tokens_ref = db.reference('auth_tokens')

# ------------------------------------------------------------
# Telegram Bot Setup
# ------------------------------------------------------------
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# ------------------------------------------------------------
# Flask App Setup
# ------------------------------------------------------------
app = Flask(__name__, template_folder='../templates')

# ------------------------------------------------------------
# Webhook route for Telegram
# ------------------------------------------------------------
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'ok', 200
    else:
        return flask.abort(403)

@app.route('/')
def index():
    return "UltimateMediaSearchBot is running. <a href='/admin?key=...'>Admin</a>", 200

# ------------------------------------------------------------
# Bot Command: /start
# ------------------------------------------------------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_ref = users_ref.child(str(user_id))

    if not user_ref.get():
        # New user registration
        args = message.text.split()
        referrer_code = args[1] if len(args) > 1 else None
        referrer_id = None
        if referrer_code:
            all_users = users_ref.get()
            if all_users:
                for uid, data in all_users.items():
                    if data.get('referral_code') == referrer_code:
                        referrer_id = uid
                        break
        user_data = {
            "username": message.from_user.username or "",
            "first_name": message.from_user.first_name,
            "referral_code": secrets.token_hex(4),
            "referrer_id": referrer_id,
            "balance": 0,
            "plan": None,
            "role": "user",
            "verified_platforms": {"youtube": False, "instagram": False, "facebook": False},
            "tasks_completed": 0,
            "created_at": {".sv": "timestamp"}
        }
        user_ref.set(user_data)
        logger.info(f"New user registered: {user_id}")

    caption = (
        "🎉 Welcome to UltimateMediaSearchBot!\n\n"
        "Earn money by completing simple tasks and referring friends.\n"
        "📌 Verify your accounts to start earning.\n"
        "📈 Upgrade to Pro for 2x earnings.\n"
        "🤝 Refer & earn 10% lifetime commission.\n\n"
        "Use the buttons below to navigate."
    )
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("📊 Dashboard", callback_data="dashboard"))
    markup.row(
        types.InlineKeyboardButton("➕ Verify Accounts", callback_data="verify"),
        types.InlineKeyboardButton("💎 Upgrade Plan", callback_data="plans")
    )
    markup.row(types.InlineKeyboardButton("🔗 Referral Link", callback_data="referral"))
    markup.row(types.InlineKeyboardButton("❓ Help", callback_data="help"))
    bot.send_photo(message.chat.id, photo=WELCOME_IMAGE_URL, caption=caption, reply_markup=markup)

# ------------------------------------------------------------
# Bot Command: /help  (uses requests – no openai library)
# ------------------------------------------------------------
@bot.message_handler(commands=['help'])
def help_command(message):
    query = message.text.replace('/help', '', 1).strip()
    if not query:
        bot.reply_to(message, "Please describe your issue after /help, e.g.: `/help How to withdraw?`", parse_mode='Markdown')
        return

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a support assistant for UltimateMediaSearchBot, a Telegram earning bot."},
            {"role": "user", "content": query}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(
            f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        answer = data["choices"][0]["message"]["content"]
        bot.reply_to(message, answer, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"DeepSeek API error: {e}")
        bot.reply_to(message, "Sorry, I'm having trouble answering right now. Please try again later.")

# ------------------------------------------------------------
# Bot Command: /dashboard
# ------------------------------------------------------------
@bot.message_handler(commands=['dashboard'])
def generate_dashboard(message):
    user_id = message.from_user.id
    token = secrets.token_urlsafe(32)
    auth_tokens_ref.child(token).set({
        "user_id": user_id,
        "expires_at": int(time.time()) + 3600  # 1 hour
    })
    dashboard_url = f"https://{VERCEL_URL}/dashboard?token={token}"
    bot.reply_to(message, f"🔐 Your personal dashboard: {dashboard_url}\n⏳ Link valid for 1 hour.")

# ------------------------------------------------------------
# Inline Callback Handler
# ------------------------------------------------------------
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    data = call.data
    user_id = call.from_user.id

    if data == "dashboard":
        generate_dashboard(call.message)
        bot.answer_callback_query(call.id)
    elif data == "verify":
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("✅ I've Joined All", callback_data="confirm_verify"))
        platforms = [
            "📺 YouTube: @USSoccerPulse",
            "📸 Instagram: @digital_rockstar_m",
            "📘 Facebook: Official Profile"
        ]
        msg = "🔗 Please join all mandatory platforms:\n\n" + "\n".join(platforms) + "\n\nThen press the button below."
        bot.send_message(call.message.chat.id, msg, reply_markup=markup, disable_web_page_preview=True)
        bot.answer_callback_query(call.id)
    elif data == "confirm_verify":
        users_ref.child(str(user_id)).update({
            "verified_platforms": {"youtube": True, "instagram": True, "facebook": True}
        })
        bot.send_message(call.message.chat.id, "✅ All platforms verified! You can now access all tasks.")
        bot.answer_callback_query(call.id)
    elif data == "plans":
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("Pro Earner - ₹100", callback_data="buy_100"))
        markup.row(types.InlineKeyboardButton("Advertiser - ₹500", callback_data="buy_500"))
        bot.send_message(call.message.chat.id, "Choose your plan:", reply_markup=markup)
        bot.answer_callback_query(call.id)
    elif data.startswith("buy_"):
        plan_amount = 100 if data == "buy_100" else 500
        payment_data = {
            "user_id": user_id,
            "amount": plan_amount,
            "status": "pending_screenshot",
            "timestamp": {".sv": "timestamp"}
        }
        if plan_amount == 100:
            payment_data["plan"] = "pro"
        else:
            payment_data["role_update"] = "advertiser"
        payments_ref.push(payment_data)
        bot.send_message(call.message.chat.id,
                         f"💰 Plan Price: ₹{plan_amount}\n\n📲 UPI ID: `{UPI_ID}`\n\n"
                         "📸 After payment, send the screenshot here.\nYour payment will be verified shortly.",
                         parse_mode='Markdown')
        bot.answer_callback_query(call.id)
    elif data == "referral":
        user_data = users_ref.child(str(user_id)).get()
        if user_data:
            ref_code = user_data.get('referral_code', 'N/A')
            link = f"https://t.me/{bot.get_me().username}?start={ref_code}"
            bot.send_message(call.message.chat.id,
                             f"🔗 Your referral link:\n{link}\n\nShare it to earn 10% lifetime commission on your referrals' task earnings.")
        bot.answer_callback_query(call.id)
    elif data == "help":
        bot.send_message(call.message.chat.id, "Type /help followed by your question, e.g. `/help How to withdraw?`")
        bot.answer_callback_query(call.id)

# ------------------------------------------------------------
# Handle Payment Screenshot Submission
# ------------------------------------------------------------
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    user_payments = payments_ref.order_by_child('user_id').equal_to(user_id).get()
    if user_payments:
        for pay_id, pay_data in user_payments.items():
            if pay_data.get('status') == 'pending_screenshot':
                payments_ref.child(pay_id).update({
                    "screenshot_file_id": message.photo[-1].file_id,
                    "status": "pending"
                })
                bot.reply_to(message, "✅ Screenshot received! Your payment is pending admin verification.")
                if ADMIN_CHAT_ID:
                    bot.send_message(ADMIN_CHAT_ID,
                                     f"🆕 New payment from user {user_id} for ₹{pay_data.get('amount')}.\nID: {pay_id}")
                return
    bot.reply_to(message, "No pending payment found. Please start a plan purchase first.")

# ------------------------------------------------------------
# Web Dashboard Route (User Stats)
# ------------------------------------------------------------
@app.route('/dashboard')
def user_dashboard():
    token = request.args.get('token')
    if not token:
        return redirect(url_for('index'))
    token_data = auth_tokens_ref.child(token).get()
    if not token_data:
        return "Invalid or expired token.", 401
    if token_data.get('expires_at', 0) < time.time():
        auth_tokens_ref.child(token).delete()
        return "Token expired.", 401
    user_id = token_data['user_id']
    user = users_ref.child(str(user_id)).get()
    if not user:
        return "User not found.", 404
    return render_template('dashboard.html',
                           user=user,
                           user_id=user_id,
                           balance=user.get('balance', 0),
                           plan=user.get('plan'),
                           role=user.get('role', 'user'),
                           tasks_completed=user.get('tasks_completed', 0))

# ------------------------------------------------------------
# Admin Panel
# ------------------------------------------------------------
@app.route('/admin')
def admin_panel():
    key = request.args.get('key', '')
    if key != ADMIN_SECRET:
        return "Unauthorized", 401
    all_payments = payments_ref.get() or {}
    pending_payments = {pid: p for pid, p in all_payments.items() if p.get('status') == 'pending'}
    all_tasks = tasks_ref.get() or {}
    return render_template('admin.html',
                           pending_payments=pending_payments,
                           tasks=all_tasks)

@app.route('/admin/approve_payment', methods=['POST'])
def approve_payment():
    key = request.form.get('key')
    if key != ADMIN_SECRET:
        return "Unauthorized", 401
    payment_id = request.form.get('payment_id')
    if not payment_id:
        return "Missing payment ID", 400
    payment = payments_ref.child(payment_id).get()
    if not payment:
        return "Payment not found", 404
    user_id = payment['user_id']
    updates = {}
    if 'plan' in payment:
        updates['plan'] = payment['plan']
    if 'role_update' in payment:
        updates['role'] = payment['role_update']
    if updates:
        users_ref.child(str(user_id)).update(updates)
    payments_ref.child(payment_id).update({"status": "approved"})
    try:
        bot.send_message(user_id, "✅ Your payment has been approved! Your account has been upgraded.")
    except Exception as e:
        logger.warning(f"Could not notify user {user_id}: {e}")
    return redirect(url_for('admin_panel', key=key))

@app.route('/admin/add_task', methods=['POST'])
def add_task():
    key = request.form.get('key')
    if key != ADMIN_SECRET:
        return "Unauthorized", 401
    title = request.form.get('title')
    description = request.form.get('description')
    reward = request.form.get('reward')
    link = request.form.get('link', '')
    if not title or not reward:
        return "Missing fields", 400
    tasks_ref.push({
        "title": title,
        "description": description,
        "reward": int(reward),
        "link": link,
        "created_at": {".sv": "timestamp"}
    })
    return redirect(url_for('admin_panel', key=key))

# ------------------------------------------------------------
# Webhook setter (for one‑time setup)
# ------------------------------------------------------------
@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    url = f"https://{VERCEL_URL}/webhook"
    bot.set_webhook(url=url)
    return f"Webhook set to {url}", 200

# ------------------------------------------------------------
# Vercel entry point
# ------------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
