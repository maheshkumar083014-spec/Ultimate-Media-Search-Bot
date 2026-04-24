#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UltimateMediaSearchBot - Vercel Production Ready
Fixed Firebase Initialization
"""

import os
import json
import logging
from datetime import datetime, timedelta
import requests
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, jsonify
import telebot
from telebot import types

# Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
UPI_ID = os.getenv('UPI_ID', '8543083014@mbk')
AD_LINK = os.getenv('AD_LINK', 'https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b')
YOUTUBE_CHANNEL = '@USSoccerPulse'
INSTAGRAM_HANDLE = '@digital_rockstar_m'
WELCOME_PHOTO = "https://i.ibb.co/h1m0cc1W/6a74f155-a6b7-499f-ad34-c1a3989433e0.jpg"
ADMIN_ID = os.getenv('ADMIN_ID', '')

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flask App
app = Flask(__name__)

# Firebase Initialization - FIXED VERSION
firebase_db = None

def init_firebase():
    global firebase_db
    try:
        logger.info("🔄 Initializing Firebase...")
        
        # Method: Single JSON string from environment variable
        firebase_config_json = os.getenv('FIREBASE_CONFIG_JSON')
        
        if not firebase_config_json:
            logger.error("❌ FIREBASE_CONFIG_JSON environment variable not set!")
            return False
        
        # Parse JSON
        try:
            config = json.loads(firebase_config_json)
            logger.info("✅ JSON parsed successfully")
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing failed: {e}")
            logger.error(f"First 100 chars: {firebase_config_json[:100]}")
            return False
        
        # Validate required fields
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        for field in required_fields:
            if field not in config:
                logger.error(f"❌ Missing field in config: {field}")
                return False
        
        # Create credentials
        try:
            cred = credentials.Certificate(config)
            logger.info("✅ Credentials created")
        except Exception as e:
            logger.error(f"❌ Failed to create credentials: {e}")
            logger.error(f"Private key starts with: {config.get('private_key', '')[:50]}")
            return False
        
        # Initialize Firebase Admin SDK
        project_id = config.get('project_id', 'ultimatemediasearch')
        try:
            firebase_admin.initialize_app(cred, {
                'databaseURL': f"https://{project_id}-default-rtdb.firebaseio.com/"
            })
            firebase_db = db.reference()
            logger.info(f"✅ Firebase initialized successfully for project: {project_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Firebase app: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Firebase init error: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

# Initialize Firebase
firebase_initialized = init_firebase()

# Telegram Bot
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML', threaded=False)

# ==================== DATABASE HELPERS ====================

def get_user(uid):
    if not firebase_db: 
        return None
    try:
        return firebase_db.child('users').child(str(uid)).get()
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return None

def update_user(uid, data):
    if not firebase_db: 
        return False
    try:
        firebase_db.child('users').child(str(uid)).update(data)
        return True
    except Exception as e:
        logger.error(f"Update user error: {e}")
        return False

def create_user(uid, username, fname, ref=None):
    if not firebase_db: 
        return False
    user = {
        'user_id': uid, 
        'username': username, 
        'first_name': fname,
        'balance': 0, 
        'plan': 'free', 
        'joined_date': datetime.now().isoformat(),
        'total_earned': 0, 
        'tasks_completed': 0, 
        'referrals': [],
        'referrer_id': ref, 
        'verified_youtube': False, 
        'verified_instagram': False,
        'last_task_time': None, 
        'completed_tasks': [], 
        'submitted_tasks': []
    }
    try:
        firebase_db.child('users').child(str(uid)).set(user)
        if ref and ref != uid:
            ref_data = firebase_db.child('users').child(str(ref)).get()
            if ref_data:
                refs = ref_data.get('referrals', [])
                if uid not in refs:
                    refs.append(uid)
                    firebase_db.child('users').child(str(ref)).update({'referrals': refs})
        logger.info(f"✅ User {uid} created")
        return True
    except Exception as e:
        logger.error(f"Create user error: {e}")
        return False

def add_balance(uid, amount, task_id=None):
    user = get_user(uid)
    if not user: 
        return False
    mult = 2 if user.get('plan') == 'pro' else 1
    final = amount * mult
    new_bal = user.get('balance', 0) + final
    new_total = user.get('total_earned', 0) + final
    new_tasks = user.get('tasks_completed', 0) + 1
    update_user(uid, {
        'balance': new_bal, 
        'total_earned': new_total, 
        'tasks_completed': new_tasks, 
        'last_task_time': datetime.now().isoformat()
    })
    # Referral commission
    ref_id = user.get('referrer_id')
    if ref_id:
        ref = get_user(ref_id)
        if ref:
            comm = final * 0.10
            try:
                firebase_db.child('users').child(str(ref_id)).update({
                    'balance': ref.get('balance', 0) + comm,
                    'total_earned': ref.get('total_earned', 0) + comm
                })
                bot.send_message(ref_id, f"🎉 Referral commission: ₹{comm:.2f}")
            except Exception as e:
                logger.error(f"Referral update error: {e}")
    return True

# ==================== DEEPSEEK AI ====================

def query_deepseek(messages):
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
            headers=headers, 
            json=payload, 
            timeout=30
        )
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content']
        return "Sorry, AI service unavailable."
    except Exception as e:
        logger.error(f"DeepSeek error: {e}")
        return "An error occurred."

# ==================== KEYBOARDS ====================

def main_menu():
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

def verify_kb():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("✅ Verify YouTube", callback_data="verify_youtube"),
        types.InlineKeyboardButton("✅ Verify Instagram", callback_data="verify_instagram"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_verify")
    )
    return kb

# ==================== COMMAND HANDLERS ====================

@bot.message_handler(commands=['start'])
def cmd_start(msg):
    try:
        uid = msg.from_user.id
        uname = msg.from_user.username or 'User'
        fname = msg.from_user.first_name
        ref = None
        parts = msg.text.split()
        if len(parts) > 1:
            try:
                ref = int(parts[1])
                if ref == uid: 
                    ref = None
            except: 
                ref = None
        
        user = get_user(uid)
        if not user:
            create_user(uid, uname, fname, ref)
            user = get_user(uid)
        
        cap = (f"👋 <b>Welcome to UltimateMediaSearchBot!</b>\n\n"
               f"🇮 <b>India's #1 Destination</b> for Earning & Promotion!\n\n"
               f"💡 <i>\"Success is not final, failure is not fatal: it is the courage to continue that counts.\"</i>\n\n"
               f"🚀 <b>Start earning today!</b>\n\n"
               f"📊 <b>Your Stats:</b>\n💰 Balance: ₹{user.get('balance',0)}\n"
               f"📦 Plan: {user.get('plan','free').upper()}\n✅ Tasks: {user.get('tasks_completed',0)}\n\n"
               f"Use /help for commands.")
        try:
            bot.send_photo(msg.chat.id, WELCOME_PHOTO, caption=cap, reply_markup=main_menu())
        except:
            bot.send_message(msg.chat.id, cap.replace('<b>','').replace('</b>',''), reply_markup=main_menu())
    except Exception as e:
        logger.error(f"Start command error: {e}")

@bot.message_handler(commands=['help'])
def cmd_help(msg):
    txt = ("📚 <b>Commands:</b>\n\n"
           "🏠 /start - Start bot\n💰 /balance - Check balance\n📋 /tasks - View tasks\n"
           "👥 /referrals - Your referrals\n💳 /upgrade - Upgrade plan\n💸 /withdraw - Withdraw\n"
           "📝 /submit_task - Submit task (Advertisers)\n🎧 /support - AI Support\n📊 /stats - Your stats")
    bot.send_message(msg.chat.id, txt, reply_markup=main_menu())

@bot.message_handler(commands=['balance'])
def cmd_balance(msg):
    user = get_user(msg.from_user.id)
    if not user:
        bot.send_message(msg.chat.id, "User not found. Use /start")
        return
    mult = "2x" if user.get('plan')=='pro' else "1x"
    txt = (f"💰 <b>Balance</b>\n💵 Available: ₹{user.get('balance',0):.2f}\n"
           f"📦 Plan: {user.get('plan','free').upper()} ({mult})\n"
           f"📈 Total: ₹{user.get('total_earned',0):.2f}")
    bot.send_message(msg.chat.id, txt, reply_markup=main_menu())

@bot.message_handler(commands=['tasks'])
def cmd_tasks(msg):
    user = get_user(msg.from_user.id)
    if not user:
        bot.send_message(msg.chat.id, "User not found. Use /start")
        return
    if not firebase_db:
        bot.send_message(msg.chat.id, "⚠️ Database unavailable")
        return
    try:
        tasks = firebase_db.child('tasks').get() or {}
        kb = types.InlineKeyboardMarkup(row_width=1)
        for tid, t in tasks.items():
            if t.get('active', True):
                reward = t.get('reward', 10) * (2 if user.get('plan')=='pro' else 1)
                kb.add(types.InlineKeyboardButton(f"💰 {t.get('title','Task')} - ₹{reward}", callback_data=f"task_{tid}"))
        bot.send_message(msg.chat.id, "📋 <b>Available Tasks</b>\nPRO = 2x rewards!", reply_markup=kb)
    except Exception as e:
        logger.error(f"Tasks error: {e}")
        bot.send_message(msg.chat.id, "Error loading tasks")

@bot.message_handler(commands=['referrals'])
def cmd_referrals(msg):
    user = get_user(msg.from_user.id)
    if not user:
        bot.send_message(msg.chat.id, "User not found. Use /start")
        return
    refs = user.get('referrals', [])
    code = msg.from_user.id
    comm = 0
    for r in refs:
        ref_user = get_user(r)
        if ref_user:
            comm += ref_user.get('total_earned', 0) * 0.10
    txt = (f"👥 <b>Referrals</b>\n\n🔗 <b>Your Link:</b>\n"
           f"<code>https://t.me/{bot.get_me().username}?start={code}</code>\n\n"
           f"📊 Total: {len(refs)} | Commission: ₹{comm:.2f}\n"
           f"💵 Rate: 10% lifetime")
    bot.send_message(msg.chat.id, txt, reply_markup=main_menu())

@bot.message_handler(commands=['upgrade'])
def cmd_upgrade(msg):
    user = get_user(msg.from_user.id)
    if not user:
        bot.send_message(msg.chat.id, "User not found. Use /start")
        return
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("💰 ₹100 - PRO (2x)", callback_data="upgrade_pro"),
        types.InlineKeyboardButton("📢 ₹500 - ADVERTISER", callback_data="upgrade_advertiser"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_upgrade")
    )
    txt = (f"💎 <b>Upgrade</b>\n📦 Current: {user.get('plan','free').upper()}\n\n"
           f"🥇 PRO ₹100: 2x rewards\n"
           f"🏢 ADVERTISER ₹500: Submit tasks + PRO features\n\n"
           f"💳 UPI: {UPI_ID}")
    bot.send_message(msg.chat.id, txt, reply_markup=kb)

@bot.message_handler(commands=['withdraw'])
def cmd_withdraw(msg):
    user = get_user(msg.from_user.id)
    if not user:
        bot.send_message(msg.chat.id, "User not found. Use /start")
        return
    bal = user.get('balance', 0)
    if bal < 100:
        bot.send_message(msg.chat.id, f"❌ Min withdrawal: ₹100 | Your balance: ₹{bal}", reply_markup=main_menu())
        return
    kb = types.InlineKeyboardMarkup(row_width=1)
    for amt in [100, 500, 1000]:
        kb.add(types.InlineKeyboardButton(f"💵 Withdraw ₹{amt}", callback_data=f"withdraw_{amt}"))
    kb.add(types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_withdraw"))
    bot.send_message(msg.chat.id, f"💸 <b>Withdraw</b>\nBalance: ₹{bal}\nSelect amount:", reply_markup=kb)

@bot.message_handler(commands=['stats'])
def cmd_stats(msg):
    user = get_user(msg.from_user.id)
    if not user:
        bot.send_message(msg.chat.id, "User not found. Use /start")
        return
    txt = (f"📊 <b>Statistics</b>\n💰 Balance: ₹{user.get('balance',0):.2f}\n"
           f"📈 Earned: ₹{user.get('total_earned',0):.2f}\n✅ Tasks: {user.get('tasks_completed',0)}\n"
           f"👥 Referrals: {len(user.get('referrals',[]))}\n📦 Plan: {user.get('plan','free').upper()}\n"
           f"📅 Joined: {user.get('joined_date','N/A')[:10]}\n\n"
           f"🎯 Verification:\n{'✅' if user.get('verified_youtube') else '❌'} YouTube\n"
           f"{'✅' if user.get('verified_instagram') else '❌'} Instagram")
    bot.send_message(msg.chat.id, txt, reply_markup=main_menu())

@bot.message_handler(commands=['support'])
def cmd_support(msg):
    m = bot.send_message(msg.chat.id, "🎧 <b>AI Support</b>\nDescribe your issue:", reply_markup=types.ForceReply())
    bot.register_next_step_handler(m, process_support)

def process_support(msg):
    if not msg.text:
        bot.send_message(msg.chat.id, "❌ Invalid")
        return
    bot.send_chat_action(msg.chat.id, 'typing')
    user = get_user(msg.from_user.id)
    sys_msg = {"role": "system", "content": f"You are support for UltimateMediaSearchBot. Features: tasks, PRO(₹100)=2x, ADVERTISER(₹500)=submit tasks, referral=10%, withdraw min ₹100, UPI:{UPI_ID}. Be helpful."}
    usr_msg = {"role": "user", "content": f"User:{msg.from_user.first_name} Plan:{user.get('plan','free') if user else 'unknown'} Q:{msg.text}"}
    resp = query_deepseek([sys_msg, usr_msg])
    bot.send_message(msg.chat.id, f"🎧 <b>Support:</b>\n\n{resp}", reply_markup=main_menu())

# ==================== CALLBACKS ====================

@bot.callback_query_handler(func=lambda c: c.data.startswith('menu_'))
def cb_menu(call):
    action = call.data.replace('menu_', '')
    handlers = {
        'balance': cmd_balance, 
        'tasks': cmd_tasks, 
        'referrals': cmd_referrals,
        'upgrade': cmd_upgrade, 
        'withdraw': cmd_withdraw, 
        'stats': cmd_stats, 
        'support': cmd_support
    }
    if action in handlers:
        handlers[action](call.message)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('task_'))
def cb_task(call):
    tid = call.data.replace('task_', '')
    uid = call.from_user.id
    user = get_user(uid)
    if not user:
        bot.answer_callback_query(call.id, "User not found", show_alert=True)
        return
    if not user.get('verified_youtube') or not user.get('verified_instagram'):
        bot.send_message(uid, f"⚠️ <b>Verify First</b>\n1️⃣ Follow: {YOUTUBE_CHANNEL}\n2️⃣ Follow: {INSTAGRAM_HANDLE}", reply_markup=verify_kb())
        bot.answer_callback_query(call.id, "Verify accounts first")
        return
    if not firebase_db:
        bot.answer_callback_query(call.id, "DB error", show_alert=True)
        return
    try:
        task = firebase_db.child('tasks').child(tid).get()
        if not task:
            bot.answer_callback_query(call.id, "Task not found", show_alert=True)
            return
        if tid in user.get('completed_tasks', []):
            bot.answer_callback_query(call.id, "Already completed!", show_alert=True)
            return
        last = user.get('last_task_time')
        if last:
            lt = datetime.fromisoformat(last)
            if datetime.now() - lt < timedelta(minutes=1):
                sec = 60 - (datetime.now()-lt).seconds
                bot.answer_callback_query(call.id, f"Wait {sec}s", show_alert=True)
                return
        reward = task.get('reward',10) * (2 if user.get('plan')=='pro' else 1)
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            types.InlineKeyboardButton("🔗 Open", url=task.get('link','#')),
            types.InlineKeyboardButton("✅ Completed", callback_data=f"complete_{tid}")
        )
        bot.send_message(uid, f"📋 <b>{task.get('title')}</b>\n\n{task.get('description','')}\n\n💰 Reward: ₹{reward}", reply_markup=kb)
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"Task callback error: {e}")
        bot.answer_callback_query(call.id, "Error", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith('complete_'))
def cb_complete(call):
    tid = call.data.replace('complete_', '')
    uid = call.from_user.id
    if not firebase_db:
        bot.answer_callback_query(call.id, "DB error", show_alert=True)
        return
    try:
        task = firebase_db.child('tasks').child(tid).get()
        user = get_user(uid)
        if not task or not user:
            bot.answer_callback_query(call.id, "Error", show_alert=True)
            return
        reward = task.get('reward',10) * (2 if user.get('plan')=='pro' else 1)
        if add_balance(uid, task.get('reward',10), tid):
            done = user.get('completed_tasks', [])
            if tid not in done:
                done.append(tid)
                firebase_db.child('users').child(str(uid)).update({'completed_tasks': done})
            bot.answer_callback_query(call.id, f"✅ ₹{reward} added!")
            bot.send_message(uid, f"✅ <b>Completed!</b>\n💰 +₹{reward}\n📊 Balance: ₹{user.get('balance',0)+reward}", reply_markup=main_menu())
        else:
            bot.answer_callback_query(call.id, "Error", show_alert=True)
    except Exception as e:
        logger.error(f"Complete error: {e}")
        bot.answer_callback_query(call.id, "Error", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith('verify_'))
def cb_verify(call):
    uid = call.from_user.id
    platform = call.data.replace('verify_', '')
    if platform == 'youtube':
        update_user(uid, {'verified_youtube': True})
        bot.answer_callback_query(call.id, "✅ YouTube verified!", show_alert=True)
    elif platform == 'instagram':
        update_user(uid, {'verified_instagram': True})
        bot.answer_callback_query(call.id, "✅ Instagram verified!", show_alert=True)
    user = get_user(uid)
    if user and user.get('verified_youtube') and user.get('verified_instagram'):
        bot.edit_message_text("✅ <b>All Verified!</b>\nStart completing tasks!", call.message.chat.id, call.message.message_id, reply_markup=main_menu())
    else:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=verify_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith('upgrade_'))
def cb_upgrade(call):
    plan = call.data.replace('upgrade_', '')
    uid = call.from_user.id
    if plan == 'pro':
        amt, pname, ben = 100, 'PRO', '2x rewards'
    elif plan == 'advertiser':
        amt, pname, ben = 500, 'ADVERTISER', 'Submit tasks + 2x'
    else:
        bot.answer_callback_query(call.id, "Invalid", show_alert=True)
        return
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("✅ I Paid", callback_data=f"paid_{plan}"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_upgrade")
    )
    bot.send_message(uid, f"💎 <b>Upgrade to {pname}</b>\n💰 ₹{amt}\n✨ {ben}\n\n📲 Pay: <code>{UPI_ID}</code>\n\nClick 'I Paid' after payment.", reply_markup=kb)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('paid_'))
def cb_paid(call):
    plan = call.data.replace('paid_', '')
    uid = call.from_user.id
    if ADMIN_ID:
        try:
            bot.send_message(ADMIN_ID, f"🔔 Upgrade: {call.from_user.first_name} (@{call.from_user.username}) | ID:{uid} | Plan:{plan.upper()}")
        except: 
            pass
    bot.send_message(uid, "✅ <b>Payment Submitted!</b>\nVerification: 2-24 hours.", reply_markup=main_menu())
    bot.answer_callback_query(call.id, "Submitted")

@bot.callback_query_handler(func=lambda c: c.data.startswith('withdraw_'))
def cb_withdraw(call):
    amt = int(call.data.replace('withdraw_', ''))
    uid = call.from_user.id
    user = get_user(uid)
    if not user or user.get('balance',0) < amt:
        bot.answer_callback_query(call.id, "Insufficient balance", show_alert=True)
        return
    if firebase_db:
        try:
            firebase_db.child('withdrawals').push({
                'user_id': uid, 
                'username': call.from_user.username, 
                'amount': amt,
                'status': 'pending', 
                'requested_at': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Withdrawal error: {e}")
    bot.send_message(uid, f"💸 <b>Withdrawal Requested</b>\nAmount: ₹{amt}\nStatus: Pending\nProcess: 24-48 hrs", reply_markup=main_menu())
    bot.answer_callback_query(call.id, "Request submitted")

@bot.callback_query_handler(func=lambda c: c.data in ['cancel_upgrade','cancel_withdraw','cancel_verify'])
def cb_cancel(call):
    bot.edit_message_text("❌ Cancelled.", call.message.chat.id, call.message.message_id, reply_markup=main_menu())
    bot.answer_callback_query(call.id, "Cancelled")

# ==================== FLASK ROUTES ====================

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        try:
            update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
            bot.process_new_updates([update])
            return '', 200
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return '', 500
    return '', 403

@app.route('/set-webhook', methods=['GET'])
def set_webhook():
    webhook_url = os.getenv('WEBHOOK_URL', request.url_root.rstrip('/') + '/webhook')
    try:
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        return jsonify({'status':'success','webhook':webhook_url})
    except Exception as e:
        logger.error(f"Set webhook error: {e}")
        return jsonify({'status':'error','message':str(e)}), 500

@app.route('/', methods=['GET'])
def health():
    return jsonify({
        'status':'ok',
        'bot':'running' if BOT_TOKEN else 'no_token',
        'firebase':'connected' if firebase_db else 'disconnected',
        'firebase_initialized': firebase_initialized
    })

@app.route('/test-db', methods=['GET'])
def test_db():
    if not firebase_db:
        return jsonify({'status':'error','message':'Firebase not initialized'}), 500
    try:
        ref = firebase_db.child('health').push({'ok':True,'ts':datetime.now().isoformat()})
        return jsonify({'status':'success','message':'Firebase OK'})
    except Exception as e:
        logger.error(f"Test DB error: {e}")
        return jsonify({'status':'error','message':str(e)}), 500

# ==================== MAIN ====================

if __name__ == '__main__':
    logger.info("🚀 Starting local server...")
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
