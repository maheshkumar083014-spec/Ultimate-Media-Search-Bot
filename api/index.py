import os
import logging
import json
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

# Telegram Bot API
import telebot
from telebot import types

# Firebase Admin (optional - with safe fallback)
firebase_db = None
try:
    import firebase_admin
    from firebase_admin import credentials, db
    
    # Only initialize if all required env vars exist
    if all([
        os.getenv('FIREBASE_PROJECT_ID'),
        os.getenv('FIREBASE_PRIVATE_KEY'),
        os.getenv('FIREBASE_CLIENT_EMAIL')
    ]):
        private_key = os.getenv('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n')
        
        cred_dict = {
            "type": "service_account",
            "project_id": os.getenv('FIREBASE_PROJECT_ID'),
            "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID', ''),
            "private_key": private_key,
            "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
            "client_id": os.getenv('FIREBASE_CLIENT_ID', ''),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_X509_CERT_URL', '')
        }
        cred_dict = {k: v for k, v in cred_dict.items() if v}
        
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': os.getenv('FIREBASE_DATABASE_URL', 'https://earn-bot-2026-default-rtdb.firebaseio.com/')
        })
        firebase_db = db.reference()
        logging.info("✅ Firebase Connected")
except Exception as e:
    logging.warning(f"⚠️ Firebase not initialized: {e}")
    firebase_db = None

# Configuration from Environment Variables
BOT_TOKEN = os.getenv('BOT_TOKEN', '8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', 'sk-783d645ce9e84eb8b954786a016561ea')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
UPI_ID = os.getenv('UPI_ID', '8543083014@mbk')
AD_LINK = os.getenv('AD_LINK', 'https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b')
WELCOME_PHOTO = "https://i.ibb.co/h1m0cc1W/6a74f155-a6b7-499f-ad34-c1a3989433e0.jpg"

# Social Media Verification
YOUTUBE_CHANNEL = "@USSoccerPulse"
INSTAGRAM_HANDLE = "@digital_rockstar_m"

# Initialize Flask & Bot
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML', threaded=False)

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== HELPER FUNCTIONS ====================

def get_user_data(user_id):
    """Fetch user data from Firebase"""
    if not firebase_db:
        return {'user_id': str(user_id), 'balance': 0, 'plan': 'free', 'referrals': [], 'tasks_completed': 0, 'verified_youtube': False, 'verified_instagram': False}
    try:
        return firebase_db.child('users').child(str(user_id)).get() or {}
    except:
        return {}

def update_user_data(user_id, data):
    """Update user data in Firebase"""
    if not firebase_db:
        return True
    try:
        firebase_db.child('users').child(str(user_id)).update(data)
        return True
    except:
        return False

def create_user(user_id, username, first_name, referrer_id=None):
    """Create new user in database"""
    if not firebase_db:
        return True
    user_data = {
        'user_id': user_id,
        'username': username,
        'first_name': first_name,
        'balance': 0,
        'plan': 'free',
        'joined_date': datetime.now().isoformat(),
        'total_earned': 0,
        'tasks_completed': 0,
        'referrals': [],
        'referrer_id': referrer_id,
        'verified_youtube': False,
        'verified_instagram': False,
        'last_task_time': None
    }
    try:
        firebase_db.child('users').child(str(user_id)).set(user_data)
        if referrer_id and firebase_db:
            ref = firebase_db.child('users').child(str(referrer_id)).get()
            if ref:
                refs = ref.get('referrals', [])
                if user_id not in refs:
                    refs.append(user_id)
                    firebase_db.child('users').child(str(referrer_id)).update({'referrals': refs})
        return True
    except:
        return False

def add_balance(user_id, amount):
    """Add balance with referral commission"""
    user = get_user_data(user_id)
    multiplier = 2 if user.get('plan') == 'pro' else 1
    final = amount * multiplier
    new_bal = user.get('balance', 0) + final
    
    update_user_data(user_id, {
        'balance': new_bal,
        'total_earned': user.get('total_earned', 0) + final,
        'tasks_completed': user.get('tasks_completed', 0) + 1
    })
    
    # 10% referral commission
    ref_id = user.get('referrer_id')
    if ref_id and firebase_db:
        ref = firebase_db.child('users').child(str(ref_id)).get()
        if ref:
            comm = final * 0.10
            firebase_db.child('users').child(str(ref_id)).update({
                'balance': ref.get('balance', 0) + comm,
                'total_earned': ref.get('total_earned', 0) + comm
            })
            try:
                bot.send_message(ref_id, f"🎉 Referral Bonus! ₹{comm:.2f} added.")
            except:
                pass
    return True

def main_menu_keyboard():
    """Main menu inline keyboard"""
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("💰 Balance", callback_data="menu_balance"),
        types.InlineKeyboardButton("📋 Tasks", callback_data="menu_tasks"),
        types.InlineKeyboardButton("👥 Referrals", callback_data="menu_referrals"),
        types.InlineKeyboardButton("💳 Upgrade", callback_data="menu_upgrade"),
        types.InlineKeyboardButton("💸 Withdraw", callback_data="menu_withdraw"),
        types.InlineKeyboardButton("📊 Stats", callback_data="menu_stats"),
        types.InlineKeyboardButton("🎧 Support", callback_data="menu_support")
    )
    return kb

# ==================== TELEGRAM HANDLERS ====================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or 'User'
    first_name = message.from_user.first_name
    
    # Check referral
    ref_id = None
    parts = message.text.split()
    if len(parts) > 1:
        try:
            ref_id = int(parts[1])
            if ref_id == user_id:
                ref_id = None
        except:
            ref_id = None
    
    # Create user if new
    if not get_user_data(user_id):
        create_user(user_id, username, first_name, ref_id)
    
    user = get_user_data(user_id)
    caption = (
        f"👋 <b>Welcome to UltimateMediaSearchBot!</b>\n\n"
        f"🇮🇳 <b>India's #1 Destination</b> for Earning & Promotion!\n\n"
        f"💡 <i>\"Success is not final, failure is not fatal: it is the courage to continue that counts.\"</i>\n\n"
        f"🚀 <b>Start earning today!</b>\n\n"
        f"📊 <b>Your Stats:</b>\n"
        f"💰 Balance: ₹{user.get('balance', 0)}\n"
        f"📦 Plan: {user.get('plan', 'free').upper()}\n"
        f"✅ Tasks: {user.get('tasks_completed', 0)}\n\n"
        f"Use /help for commands."
    )
    
    try:
        bot.send_photo(message.chat.id, WELCOME_PHOTO, caption=caption, reply_markup=main_menu_keyboard())
    except:
        bot.send_message(message.chat.id, caption.replace('<b>','').replace('</b>',''), reply_markup=main_menu_keyboard())

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "📚 <b>Commands:</b>\n\n"
        "🏠 /start - Start bot\n"
        "💰 /balance - Check balance\n"
        "📋 /tasks - View tasks\n"
        "👥 /referrals - Your referrals\n"
        "💳 /upgrade - Upgrade plan\n"
        "💸 /withdraw - Withdraw\n"
        "🎧 /support - AI Support\n"
        "📊 /stats - Your statistics\n\n"
        "💡 PRO = 2x rewards | Referral = 10% lifetime"
    )
    bot.send_message(message.chat.id, help_text, reply_markup=main_menu_keyboard())

@bot.message_handler(commands=['balance'])
def check_balance(message):
    user = get_user_data(message.from_user.id)
    plan = user.get('plan', 'free')
    mult = "2x" if plan == 'pro' else "1x"
    text = (
        f"💰 <b>Your Balance</b>\n\n"
        f"💵 Available: ₹{user.get('balance', 0):.2f}\n"
        f"📦 Plan: {plan.upper()} ({mult})\n"
        f"📈 Total: ₹{user.get('total_earned', 0):.2f}\n\n"
        f"<i>/upgrade for 2x rewards!</i>"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu_keyboard())

@bot.message_handler(commands=['tasks'])
def show_tasks(message):
    user = get_user_data(message.from_user.id)
    if not firebase_db:
        bot.send_message(message.chat.id, "📭 Tasks loading... Try again soon!")
        return
    
    tasks = firebase_db.child('tasks').get() or {}
    kb = types.InlineKeyboardMarkup(row_width=1)
    
    for tid, tdata in tasks.items():
        if tdata.get('active', True):
            reward = tdata.get('reward', 10) * (2 if user.get('plan') == 'pro' else 1)
            kb.add(types.InlineKeyboardButton(f"💰 {tdata.get('title','Task')} - ₹{reward}", callback_data=f"task_{tid}"))
    
    if not kb.keyboard:
        bot.send_message(message.chat.id, "📭 No tasks available. Check back later!")
        return
    
    bot.send_message(message.chat.id, "📋 <b>Available Tasks</b>\n\nPRO members get 2x rewards!", reply_markup=kb)

@bot.message_handler(commands=['referrals'])
def show_referrals(message):
    user = get_user_data(message.from_user.id)
    refs = user.get('referrals', [])
    code = message.from_user.id
    text = (
        f"👥 <b>Your Referrals</b>\n\n"
        f"🔗 <b>Link:</b>\n<code>https://t.me/{bot.get_me().username}?start={code}</code>\n\n"
        f"📊 Total: {len(refs)} referrals\n"
        f"💵 Commission: 10% lifetime\n\n"
        f"<i>Share & earn!</i>"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu_keyboard())

@bot.message_handler(commands=['upgrade'])
def upgrade_plan(message):
    user = get_user_data(message.from_user.id)
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("💰 ₹100 - PRO (2x)", callback_data="upgrade_pro"),
        types.InlineKeyboardButton("📢 ₹500 - ADVERTISER", callback_data="upgrade_advertiser"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_upgrade")
    )
    text = (
        f"💎 <b>Upgrade Plan</b>\n\n"
        f"📦 Current: {user.get('plan','free').upper()}\n\n"
        f"🥇 <b>PRO - ₹100</b>\n• 2x rewards\n• Priority support\n\n"
        f"🏢 <b>ADVERTISER - ₹500</b>\n• All PRO features\n• Submit your tasks\n\n"
        f"💳 UPI: {UPI_ID}"
    )
    bot.send_message(message.chat.id, text, reply_markup=kb)

@bot.message_handler(commands=['withdraw'])
def withdraw(message):
    user = get_user_data(message.from_user.id)
    bal = user.get('balance', 0)
    if bal < 100:
        bot.send_message(message.chat.id, f"❌ Min withdrawal: ₹100\nYour balance: ₹{bal}", reply_markup=main_menu_keyboard())
        return
    
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("💵 ₹100", callback_data="withdraw_100"),
        types.InlineKeyboardButton("💵 ₹500", callback_data="withdraw_500"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_withdraw")
    )
    bot.send_message(message.chat.id, f"💸 <b>Withdraw</b>\n\nBalance: ₹{bal}\n\nSelect amount:", reply_markup=kb)

@bot.message_handler(commands=['stats'])
def show_stats(message):
    user = get_user_data(message.from_user.id)
    text = (
        f"📊 <b>Statistics</b>\n\n"
        f"💰 Balance: ₹{user.get('balance',0):.2f}\n"
        f"📈 Earned: ₹{user.get('total_earned',0):.2f}\n"
        f"✅ Tasks: {user.get('tasks_completed',0)}\n"
        f"👥 Referrals: {len(user.get('referrals',[]))}\n"
        f"📦 Plan: {user.get('plan','free').upper()}\n"
        f"📅 Joined: {user.get('joined_date','N/A')[:10]}\n\n"
        f"🎯 Verification:\n"
        f"{'✅' if user.get('verified_youtube') else '❌'} YouTube: {YOUTUBE_CHANNEL}\n"
        f"{'✅' if user.get('verified_instagram') else '❌'} Instagram: {INSTAGRAM_HANDLE}"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu_keyboard())

@bot.message_handler(commands=['support'])
def support_cmd(message):
    msg = bot.send_message(message.chat.id, "🎧 <b>AI Support</b>\n\nAsk your question:", reply_markup=types.ForceReply())
    bot.register_next_step_handler(msg, process_support)

async def process_support(message):
    if not message.text:
        return
    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        headers = {'Authorization': f'Bearer {DEEPSEEK_API_KEY}', 'Content-Type': 'application/json'}
        payload = {
            'model': DEEPSEEK_MODEL,
            'messages': [
                {'role': 'system', 'content': 'You are support for UltimateMediaSearchBot. Help users with tasks, payments, referrals. UPI: ' + UPI_ID},
                {'role': 'user', 'content': message.text}
            ],
            'temperature': 0.7,
            'max_tokens': 400
        }
        resp = requests.post(f'{DEEPSEEK_BASE_URL}/v1/chat/completions', headers=headers, json=payload, timeout=20)
        reply = resp.json()['choices'][0]['message']['content'] if resp.status_code == 200 else "Sorry, try again later."
    except:
        reply = "⚠️ Connection issue. Please try again."
    
    bot.send_message(message.chat.id, f"🎧 <b>Response:</b>\n\n{reply}", reply_markup=main_menu_keyboard())

# ==================== CALLBACK HANDLERS ====================

@bot.callback_query_handler(func=lambda c: c.data.startswith('menu_'))
def menu_cb(call):
    action = call.data.replace('menu_', '')
    handlers = {
        'balance': check_balance, 'tasks': show_tasks, 'referrals': show_referrals,
        'upgrade': upgrade_plan, 'withdraw': withdraw, 'stats': show_stats, 'support': support_cmd
    }
    if action in handlers:
        handlers[action](call.message)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('task_'))
def task_cb(call):
    task_id = call.data.replace('task_', '')
    user_id = call.from_user.id
    user = get_user_data(user_id)
    
    if not user.get('verified_youtube') or not user.get('verified_instagram'):
        kb = types.InlineKeyboardMarkup(row_width=1)
        if not user.get('verified_youtube'):
            kb.add(types.InlineKeyboardButton("✅ Verify YouTube", callback_data="verify_youtube"))
        if not user.get('verified_instagram'):
            kb.add(types.InlineKeyboardButton("✅ Verify Instagram", callback_data="verify_instagram"))
        bot.send_message(user_id, f"⚠️ Verify first:\n• Follow {YOUTUBE_CHANNEL}\n• Follow {INSTAGRAM_HANDLE}", reply_markup=kb)
        bot.answer_callback_query(call.id, "Verify accounts first")
        return
    
    if not firebase_db:
        bot.answer_callback_query(call.id, "Tasks unavailable", show_alert=True)
        return
    
    task = firebase_db.child('tasks').child(task_id).get()
    if not task:
        bot.answer_callback_query(call.id, "Task not found", show_alert=True)
        return
    
    reward = task.get('reward', 10) * (2 if user.get('plan') == 'pro' else 1)
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("🔗 Open Link", url=task.get('link','#')),
        types.InlineKeyboardButton("✅ Done", callback_data=f"complete_{task_id}")
    )
    bot.send_message(user_id, f"📋 <b>{task.get('title')}</b>\n\n{task.get('description','')}\n\n💰 Reward: ₹{reward}", reply_markup=kb)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('complete_'))
def complete_cb(call):
    task_id = call.data.replace('complete_', '')
    user_id = call.from_user.id
    
    if not firebase_db:
        bot.answer_callback_query(call.id, "Error", show_alert=True)
        return
    
    task = firebase_db.child('tasks').child(task_id).get()
    user = get_user_data(user_id)
    
    if task_id in user.get('completed_tasks', []):
        bot.answer_callback_query(call.id, "Already completed!", show_alert=True)
        return
    
    reward = task.get('reward', 10)
    add_balance(user_id, reward)
    
    # Mark completed
    done = user.get('completed_tasks', [])
    done.append(task_id)
    update_user_data(user_id, {'completed_tasks': done})
    
    bot.answer_callback_query(call.id, f"✅ ₹{reward * (2 if user.get('plan')=='pro' else 1)} added!")
    bot.send_message(user_id, f"✅ Task completed! ₹{reward * (2 if user.get('plan')=='pro' else 1)} added.", reply_markup=main_menu_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith('verify_'))
def verify_cb(call):
    platform = call.data.replace('verify_', '')
    user_id = call.from_user.id
    field = f'verified_{platform}'
    update_user_data(user_id, {field: True})
    bot.answer_callback_query(call.id, f"✅ {platform.title()} verified!", show_alert=True)
    
    user = get_user_data(user_id)
    if user.get('verified_youtube') and user.get('verified_instagram'):
        bot.edit_message_text("✅ All verified! Start earning now!", call.message.chat.id, call.message.message_id, reply_markup=main_menu_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith('upgrade_'))
def upgrade_cb(call):
    plan = call.data.replace('upgrade_', '')
    amount = 100 if plan == 'pro' else 500
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("✅ Paid", callback_data=f"paid_{plan}"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_upgrade")
    )
    bot.send_message(call.from_user.id, f"💎 Upgrade to {plan.upper()}\n\n💰 ₹{amount}\n📲 Pay: {UPI_ID}\n\nClick 'Paid' after payment.", reply_markup=kb)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('paid_'))
def paid_cb(call):
    plan = call.data.replace('paid_', '')
    # In production: Add admin verification logic here
    update_user_data(call.from_user.id, {'plan': plan})
    bot.send_message(call.from_user.id, f"✅ {plan.upper()} activated! Enjoy 2x rewards!", reply_markup=main_menu_keyboard())
    bot.answer_callback_query(call.id, "Upgrade submitted!")

@bot.callback_query_handler(func=lambda c: c.data.startswith('withdraw_'))
def withdraw_cb(call):
    amount = int(call.data.replace('withdraw_', ''))
    user = get_user_data(call.from_user.id)
    if user.get('balance', 0) < amount:
        bot.answer_callback_query(call.id, "Insufficient balance", show_alert=True)
        return
    
    if firebase_db:
        firebase_db.child('withdrawals').push().set({
            'user_id': call.from_user.id, 'amount': amount, 'status': 'pending', 'time': datetime.now().isoformat()
        })
    bot.send_message(call.from_user.id, f"💸 Withdrawal ₹{amount} requested!\nProcessed in 24-48h to {UPI_ID}", reply_markup=main_menu_keyboard())
    bot.answer_callback_query(call.id, "Request submitted")

@bot.callback_query_handler(func=lambda c: 'cancel' in c.data)
def cancel_cb(call):
    bot.edit_message_text("❌ Cancelled.", call.message.chat.id, call.message.message_id, reply_markup=main_menu_keyboard())
    bot.answer_callback_query(call.id, "Cancelled")

# ==================== FLASK ROUTES (VERCEL) ====================

@app.route('/', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'bot': 'running', 'firebase': 'connected' if firebase_db else 'disconnected'}), 200

@app.route('/api/index', methods=['POST', 'GET'])
def webhook():
    """Vercel webhook endpoint: /api/index"""
    if request.method == 'GET':
        return jsonify({'status': 'webhook active', 'method': 'GET'}), 200
    
    if request.headers.get('content-type') != 'application/json':
        return '', 403
    
    try:
        update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
        bot.process_new_updates([update])
        return '', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return '', 500

@app.route('/api/index/set-webhook', methods=['GET'])
def set_webhook():
    """Set webhook URL"""
    try:
        webhook_url = os.getenv('VERCEL_URL', 'https://your-project-name.vercel.app') + '/api/index'
        bot.remove_webhook()
        result = bot.set_webhook(url=webhook_url)
        return jsonify({'status': 'success' if result else 'failed', 'url': webhook_url}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== VERCEL ENTRY POINT ====================

# This makes the Flask app work as Vercel serverless function
def handler(request, context=None):
    """Vercel serverless handler"""
    return app(request.environ, lambda status, headers, exc_info=None: None)

# For local testing
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
