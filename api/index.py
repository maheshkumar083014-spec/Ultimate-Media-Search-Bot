# ============================================
# START: index.py - UltimateMediaSearchBot
# ============================================

import os
import logging
import requests
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, jsonify
import telebot
from telebot import types
from datetime import datetime, timedelta
import json
import re

# ============================================
# CONFIGURATION (Environment Variables)
# ============================================

BOT_TOKEN = os.getenv('BOT_TOKEN', '')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
UPI_ID = os.getenv('UPI_ID', '8543083014@mbk')
AD_LINK = os.getenv('AD_LINK', '')
YOUTUBE_CHANNEL = '@USSoccerPulse'
INSTAGRAM_HANDLE = '@digital_rockstar_m'
WELCOME_PHOTO = 'https://i.ibb.co/h1m0cc1W/6a74f155-a6b7-499f-ad34-c1a3989433e0.jpg'

# ============================================
# INITIALIZATION
# ============================================

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask App
app = Flask(__name__)

# Telegram Bot (lazy initialization for serverless)
_bot_instance = None

def get_bot():
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')
        register_handlers(_bot_instance)
    return _bot_instance

# Firebase (lazy initialization)
_firebase_db = None

def get_firebase_db():
    global _firebase_db
    if _firebase_db is None and not firebase_admin._apps:
        try:
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": "earn-bot-2026",
                "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID', ''),
                "private_key": os.getenv('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n'),
                "client_email": os.getenv('FIREBASE_CLIENT_EMAIL', ''),
                "client_id": os.getenv('FIREBASE_CLIENT_ID', ''),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_X509_CERT_URL', '')
            })
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://earn-bot-2026-default-rtdb.firebaseio.com/'
            })
            _firebase_db = db.reference()
            logger.info("Firebase initialized")
        except Exception as e:
            logger.error(f"Firebase init error: {e}")
    return _firebase_db

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_user_data(user_id):
    fb = get_firebase_db()
    if not fb:
        return None
    try:
        return fb.child('users').child(str(user_id)).get()
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return None

def update_user_data(user_id, data):
    fb = get_firebase_db()
    if not fb:
        return False
    try:
        fb.child('users').child(str(user_id)).update(data)
        return True
    except Exception as e:
        logger.error(f"Update user error: {e}")
        return False

def create_user(user_id, username, first_name, referrer_id=None):
    fb = get_firebase_db()
    if not fb:
        return False
    
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
        'last_task_time': None,
        'submitted_tasks': [],
        'completed_tasks': []
    }
    
    try:
        fb.child('users').child(str(user_id)).set(user_data)
        if referrer_id:
            ref = fb.child('users').child(str(referrer_id)).get()
            if ref:
                refs = ref.get('referrals', [])
                if user_id not in refs:
                    refs.append(user_id)
                    fb.child('users').child(str(referrer_id)).update({'referrals': refs})
        return True
    except Exception as e:
        logger.error(f"Create user error: {e}")
        return False

def add_balance(user_id, amount, task_id=None):
    user = get_user_data(user_id)
    if not user:
        return False
    
    multiplier = 2 if user.get('plan') == 'pro' else 1
    final_amount = amount * multiplier
    
    new_balance = user.get('balance', 0) + final_amount
    new_total = user.get('total_earned', 0) + final_amount
    new_tasks = user.get('tasks_completed', 0) + 1
    
    update_user_data(user_id, {
        'balance': new_balance,
        'total_earned': new_total,
        'tasks_completed': new_tasks,
        'last_task_time': datetime.now().isoformat()
    })
    
    # Referral commission
    ref_id = user.get('referrer_id')
    if ref_id:
        ref = get_user_data(ref_id)
        if ref:
            commission = final_amount * 0.10
            ref_bal = ref.get('balance', 0) + commission
            ref_tot = ref.get('total_earned', 0) + commission
            update_user_data(ref_id, {'balance': ref_bal, 'total_earned': ref_tot})
            try:
                bot = get_bot()
                bot.send_message(
                    ref_id,
                    f"🎉 <b>Referral Commission!</b>\n💰 Earned: ₹{commission:.2f}\n📊 Balance: ₹{ref_bal:.2f}",
                    parse_mode='HTML'
                )
            except:
                pass
    return True

async def query_deepseek(messages):
    try:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}'
        }
        payload = {
            'model': DEEPSEEK_MODEL,
            'messages': messages,
            'temperature': 0.7,
            'max_tokens': 500
        }
        resp = requests.post(
            f'{DEEPSEEK_BASE_URL}/v1/chat/completions',
            headers=headers, json=payload, timeout=30
        )
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content']
        return "Sorry, I'm having trouble connecting. Try again later."
    except Exception as e:
        logger.error(f"DeepSeek error: {e}")
        return "An error occurred. Please try again."

def main_menu_keyboard():
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

# ============================================
# BOT HANDLERS REGISTRATION
# ============================================

def register_handlers(bot):
    
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        user_id = message.from_user.id
        username = message.from_user.username or 'User'
        first_name = message.from_user.first_name
        
        referrer_id = None
        parts = message.text.split()
        if len(parts) > 1:
            try:
                referrer_id = int(parts[1])
                if referrer_id == user_id:
                    referrer_id = None
            except:
                referrer_id = None
        
        user = get_user_data(user_id)
        if not user:
            create_user(user_id, username, first_name, referrer_id)
            user = get_user_data(user_id)
        
        caption = (
            f"👋 <b>Welcome to UltimateMediaSearchBot!</b>\n\n"
            f"🇮🇳 <b>India's #1 Destination</b> for Earning & Promotion!\n\n"
            f"💡 <i>\"Success is not final, failure is not fatal: it is the courage to continue that counts.\"</i>\n\n"
            f"🚀 <b>Start earning today by completing simple tasks!</b>\n\n"
            f"📊 <b>Your Stats:</b>\n"
            f"💰 Balance: ₹{user.get('balance', 0)}\n"
            f"📦 Plan: {user.get('plan', 'free').upper()}\n"
            f"✅ Tasks Completed: {user.get('tasks_completed', 0)}\n\n"
            f"Use /help to see all commands."
        )
        
        try:
            bot.send_photo(message.chat.id, WELCOME_PHOTO, caption=caption, reply_markup=main_menu_keyboard())
        except:
            bot.send_message(message.chat.id, re.sub(r'<[^>]+>', '', caption), reply_markup=main_menu_keyboard())

    @bot.message_handler(commands=['help'])
    def send_help(message):
        help_text = (
            "📚 <b>Available Commands:</b>\n\n"
            "🏠 <b>/start</b> - Start the bot\n"
            "💰 <b>/balance</b> - Check your balance\n"
            "📋 <b>/tasks</b> - View available tasks\n"
            "👥 <b>/referrals</b> - View your referrals\n"
            "💳 <b>/upgrade</b> - Upgrade your plan\n"
            "💸 <b>/withdraw</b> - Withdraw earnings\n"
            "📝 <b>/submit_task</b> - Submit your task (Advertisers only)\n"
            "🎧 <b>/support</b> - Get AI-powered support\n"
            "📊 <b>/stats</b> - View your statistics"
        )
        bot.send_message(message.chat.id, help_text, reply_markup=main_menu_keyboard())

    @bot.message_handler(commands=['balance'])
    def check_balance(message):
        user = get_user_data(message.from_user.id)
        if not user:
            bot.send_message(message.chat.id, "User not found. Please /start the bot.")
            return
        plan = user.get('plan', 'free')
        mult = "2x" if plan == 'pro' else "1x"
        text = (
            f"💰 <b>Your Balance</b>\n\n"
            f"💵 Available: ₹{user.get('balance', 0):.2f}\n"
            f"📦 Plan: {plan.upper()} ({mult} rewards)\n"
            f"📈 Total Earned: ₹{user.get('total_earned', 0):.2f}\n\n"
            f"💡 <i>Upgrade to PRO for double rewards!</i>"
        )
        bot.send_message(message.chat.id, text, reply_markup=main_menu_keyboard())

    @bot.message_handler(commands=['tasks'])
    def show_tasks(message):
        user = get_user_data(message.from_user.id)
        if not user:
            bot.send_message(message.chat.id, "User not found.")
            return
        fb = get_firebase_db()
        tasks = fb.child('tasks').get() if fb else {}
        if not tasks:
            bot.send_message(message.chat.id, "📭 No tasks available.")
            return
        kb = types.InlineKeyboardMarkup(row_width=1)
        for tid, tdata in tasks.items():
            if tdata.get('active', True):
                reward = tdata.get('reward', 10)
                if user.get('plan') == 'pro':
                    reward *= 2
                kb.add(types.InlineKeyboardButton(f"💰 {tdata.get('title', 'Task')} - ₹{reward}", callback_data=f"task_{tid}"))
        bot.send_message(message.chat.id, "📋 <b>Available Tasks</b>\n\nPRO members get 2x rewards.", reply_markup=kb)

    @bot.message_handler(commands=['referrals'])
    def show_referrals(message):
        user = get_user_data(message.from_user.id)
        if not user:
            bot.send_message(message.chat.id, "User not found.")
            return
        refs = user.get('referrals', [])
        ref_code = message.from_user.id
        total_comm = sum((get_user_data(r).get('total_earned', 0) * 0.10) for r in refs if get_user_data(r))
        text = (
            f"👥 <b>Your Referrals</b>\n\n"
            f"🔗 <b>Your Link:</b>\n<code>https://t.me/{bot.get_me().username}?start={ref_code}</code>\n\n"
            f"📊 Total Referrals: {len(refs)}\n"
            f"💰 Total Commission: ₹{total_comm:.2f}\n"
            f"💵 Rate: 10% lifetime"
        )
        bot.send_message(message.chat.id, text, reply_markup=main_menu_keyboard())

    @bot.message_handler(commands=['upgrade'])
    def upgrade_plan(message):
        user = get_user_data(message.from_user.id)
        if not user:
            bot.send_message(message.chat.id, "User not found.")
            return
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            types.InlineKeyboardButton("💰 ₹100 - PRO (2x Rewards)", callback_data="upgrade_pro"),
            types.InlineKeyboardButton("📢 ₹500 - ADVERTISER", callback_data="upgrade_advertiser"),
            types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_upgrade")
        )
        text = (
            f"💎 <b>Upgrade Your Plan</b>\n\n"
            f"📦 Current: {user.get('plan', 'free').upper()}\n\n"
            f"🥇 <b>PRO - ₹100</b>\n• 2x rewards\n• Priority support\n\n"
            f"🏢 <b>ADVERTISER - ₹500</b>\n• All PRO features\n• Submit tasks\n\n"
            f"💳 UPI: {UPI_ID}"
        )
        bot.send_message(message.chat.id, text, reply_markup=kb)

    @bot.message_handler(commands=['withdraw'])
    def withdraw(message):
        user = get_user_data(message.from_user.id)
        if not user:
            bot.send_message(message.chat.id, "User not found.")
            return
        bal = user.get('balance', 0)
        if bal < 100:
            bot.send_message(message.chat.id, f"❌ Minimum withdrawal: ₹100\nYour balance: ₹{bal}", reply_markup=main_menu_keyboard())
            return
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            types.InlineKeyboardButton("💵 Withdraw ₹100", callback_data="withdraw_100"),
            types.InlineKeyboardButton("💵 Withdraw ₹500", callback_data="withdraw_500"),
            types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_withdraw")
        )
        bot.send_message(message.chat.id, f"💸 <b>Withdraw</b>\n\nBalance: ₹{bal}\n\nSelect amount:", reply_markup=kb)

    @bot.message_handler(commands=['stats'])
    def show_stats(message):
        user = get_user_data(message.from_user.id)
        if not user:
            bot.send_message(message.chat.id, "User not found.")
            return
        text = (
            f"📊 <b>Your Statistics</b>\n\n"
            f"💰 Balance: ₹{user.get('balance', 0):.2f}\n"
            f"📈 Total Earned: ₹{user.get('total_earned', 0):.2f}\n"
            f"✅ Tasks Completed: {user.get('tasks_completed', 0)}\n"
            f"👥 Referrals: {len(user.get('referrals', []))}\n"
            f"📦 Plan: {user.get('plan', 'free').upper()}\n"
            f"📅 Joined: {user.get('joined_date', 'N/A')[:10]}"
        )
        bot.send_message(message.chat.id, text, reply_markup=main_menu_keyboard())

    @bot.message_handler(commands=['support'])
    def support_cmd(message):
        msg = bot.send_message(message.chat.id, "🎧 <b>AI Support</b>\n\nDescribe your issue:", reply_markup=types.ForceReply())
        bot.register_next_step_handler(msg, process_support)

    async def process_support(message):
        if not message.text:
            bot.send_message(message.chat.id, "❌ Invalid input.")
            return
        bot.send_chat_action(message.chat.id, 'typing')
        user = get_user_data(message.from_user.id)
        sys_msg = {"role": "system", "content": "You are support for UltimateMediaSearchBot. Be helpful and professional."}
        usr_msg = {"role": "user", "content": f"User: {message.from_user.first_name}\nPlan: {user.get('plan', 'free') if user else 'unknown'}\nQ: {message.text}"}
        resp = await query_deepseek([sys_msg, usr_msg])
        bot.send_message(message.chat.id, f"🎧 <b>Support:</b>\n\n{resp}", reply_markup=main_menu_keyboard())

    # Callback handlers
    @bot.callback_query_handler(func=lambda c: c.data.startswith('task_'))
    def handle_task(cb):
        tid = cb.data.replace('task_', '')
        uid = cb.from_user.id
        user = get_user_data(uid)
        if not user:
            bot.answer_callback_query(cb.id, "Error", show_alert=True)
            return
        if not user.get('verified_youtube') or not user.get('verified_instagram'):
            kb = types.InlineKeyboardMarkup(row_width=1)
            if not user.get('verified_youtube'):
                kb.add(types.InlineKeyboardButton("✅ Verify YouTube", callback_data="verify_youtube"))
            if not user.get('verified_instagram'):
                kb.add(types.InlineKeyboardButton("✅ Verify Instagram", callback_data="verify_instagram"))
            bot.send_message(uid, f"⚠️ Verify:\n1️⃣ {YOUTUBE_CHANNEL}\n2️⃣ {INSTAGRAM_HANDLE}", reply_markup=kb)
            bot.answer_callback_query(cb.id, "Verify first")
            return
        fb = get_firebase_db()
        task = fb.child('tasks').child(tid).get() if fb else None
        if not task:
            bot.answer_callback_query(cb.id, "Task not found", show_alert=True)
            return
        if tid in user.get('completed_tasks', []):
            bot.answer_callback_query(cb.id, "Already completed!", show_alert=True)
            return
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            types.InlineKeyboardButton("🔗 Open Link", url=task.get('link', '#')),
            types.InlineKeyboardButton("✅ I Completed It", callback_data=f"complete_{tid}")
        )
        reward = task.get('reward', 10) * (2 if user.get('plan') == 'pro' else 1)
        bot.send_message(uid, f"📋 <b>{task.get('title')}</b>\n\n💰 Reward: ₹{reward}", reply_markup=kb)
        bot.answer_callback_query(cb.id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('complete_'))
    def handle_complete(cb):
        tid = cb.data.replace('complete_', '')
        uid = cb.from_user.id
        fb = get_firebase_db()
        task = fb.child('tasks').child(tid).get() if fb else None
        if not task:
            bot.answer_callback_query(cb.id, "Error", show_alert=True)
            return
        user = get_user_data(uid)
        reward = task.get('reward', 10) * (2 if user.get('plan') == 'pro' else 1)
        if add_balance(uid, task.get('reward', 10), tid):
            if fb:
                done = user.get('completed_tasks', [])
                done.append(tid)
                fb.child('users').child(str(uid)).update({'completed_tasks': done})
            bot.answer_callback_query(cb.id, f"✅ ₹{reward} added!")
            bot.send_message(uid, f"✅ <b>Done!</b>\n💰 ₹{reward} added\n📊 Balance: ₹{get_user_data(uid).get('balance', 0)}", reply_markup=main_menu_keyboard())
        else:
            bot.answer_callback_query(cb.id, "Error", show_alert=True)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('verify_'))
    def handle_verify(cb):
        uid = cb.from_user.id
        plat = cb.data.replace('verify_', '')
        if plat == 'youtube':
            update_user_data(uid, {'verified_youtube': True})
            bot.answer_callback_query(cb.id, "✅ YouTube verified!", show_alert=True)
        elif plat == 'instagram':
            update_user_data(uid, {'verified_instagram': True})
            bot.answer_callback_query(cb.id, "✅ Instagram verified!", show_alert=True)
        user = get_user_data(uid)
        if user.get('verified_youtube') and user.get('verified_instagram'):
            bot.edit_message_text("✅ <b>All Verified!</b>\nStart earning now!", cb.message.chat.id, cb.message.message_id, reply_markup=main_menu_keyboard())

    @bot.callback_query_handler(func=lambda c: c.data.startswith('upgrade_'))
    def handle_upgrade(cb):
        plan = cb.data.replace('upgrade_', '')
        uid = cb.from_user.id
        amt = 100 if plan == 'pro' else 500
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            types.InlineKeyboardButton("✅ I've Paid", callback_data=f"paid_{plan}"),
            types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_upgrade")
        )
        bot.send_message(uid, f"💎 <b>Upgrade to {plan.upper()}</b>\n\n💰 ₹{amt}\n📲 Pay: <code>{UPI_ID}</code>\n\nClick 'I've Paid' after payment.", reply_markup=kb)
        bot.answer_callback_query(cb.id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('paid_'))
    def handle_paid(cb):
        bot.send_message(cb.from_user.id, "✅ <b>Payment Submitted!</b>\n\nVerification in 2-24 hours.", reply_markup=main_menu_keyboard())
        bot.answer_callback_query(cb.id, "Submitted")

    @bot.callback_query_handler(func=lambda c: c.data.startswith('withdraw_'))
    def handle_withdraw(cb):
        amt = int(cb.data.replace('withdraw_', ''))
        uid = cb.from_user.id
        user = get_user_data(uid)
        if user.get('balance', 0) < amt:
            bot.answer_callback_query(cb.id, "Insufficient balance", show_alert=True)
            return
        fb = get_firebase_db()
        if fb:
            fb.child('withdrawals').push().set({
                'user_id': uid, 'amount': amt, 'status': 'pending', 'requested_at': datetime.now().isoformat()
            })
        bot.send_message(uid, f"💸 <b>Withdrawal Submitted</b>\n\nAmount: ₹{amt}\nStatus: Pending", reply_markup=main_menu_keyboard())
        bot.answer_callback_query(cb.id, "Submitted")

    @bot.callback_query_handler(func=lambda c: c.data.startswith('menu_') or c.data.startswith('cancel_'))
    def handle_menu(cb):
        action = cb.data.replace('menu_', '').replace('cancel_', '')
        if action == 'balance': check_balance(cb.message)
        elif action == 'tasks': show_tasks(cb.message)
        elif action == 'referrals': show_referrals(cb.message)
        elif action == 'upgrade': upgrade_plan(cb.message)
        elif action == 'withdraw': withdraw(cb.message)
        elif action == 'stats': show_stats(cb.message)
        elif action == 'support': support_cmd(cb.message)
        elif action == 'upgrade': bot.edit_message_text("❌ Cancelled", cb.message.chat.id, cb.message.message_id, reply_markup=main_menu_keyboard())
        bot.answer_callback_query(cb.id)

# ============================================
# FLASK ROUTES (VERCEL SERVERLESS)
# ============================================

@app.route('/api/index', methods=['POST', 'GET'])
@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return jsonify({'status': 'ok', 'message': 'Bot is running 🚀'})
    
    if request.headers.get('content-type') != 'application/json':
        return '', 403
    
    try:
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot = get_bot()
        bot.process_new_updates([update])
        return '', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/index', methods=['GET'])
@app.route('/', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'UltimateMediaSearchBot'})

# ============================================
# VERCEL SERVERLESS ENTRY
# ============================================

def handler(event, context):
    """Vercel serverless handler wrapper"""
    from werkzeug.test import EnvironBuilder
    from werkzeug.wrappers import Request
    
    # Convert Vercel event to WSGI environ
    builder = EnvironBuilder(
        path=event.get('path', '/'),
        query_string=event.get('query', ''),
        method=event.get('method', 'GET'),
        headers=event.get('headers', {}),
        json=event.get('body') if event.get('headers', {}).get('content-type') == 'application/json' else None
    )
    environ = builder.get_environ()
    
    # Process with Flask
    response = app(environ, lambda s, h, e=None: None)
    
    # Return Vercel-compatible response
    return {
        'statusCode': response[1][0][0],
        'headers': dict(response[1][0][1]),
        'body': ''.join(response[0]).decode('utf-8') if isinstance(response[0], bytes) else ''.join(response[0])
    }

# ============================================
# END: index.py - UltimateMediaSearchBot
# ============================================
