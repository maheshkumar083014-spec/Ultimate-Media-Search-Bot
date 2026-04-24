#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UltimateMediaSearchBot - Vercel Serverless Function
Location: api/index.py
"""

import os
import json
import logging
from datetime import datetime, timedelta
import requests
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, jsonify, make_response
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

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flask App
app = Flask(__name__)

# Firebase Initialization
firebase_db = None
firebase_initialized = False

def init_firebase():
    global firebase_db, firebase_initialized
    if firebase_initialized:
        return True
    
    try:
        logger.info("🔄 Initializing Firebase...")
        
        firebase_config_json = os.getenv('FIREBASE_CONFIG_JSON')
        
        if not firebase_config_json:
            logger.error("❌ FIREBASE_CONFIG_JSON not set!")
            return False
        
        config = json.loads(firebase_config_json)
        cred = credentials.Certificate(config)
        
        project_id = config.get('project_id', 'ultimatemediasearch')
        firebase_admin.initialize_app(cred, {
            'databaseURL': f"https://{project_id}-default-rtdb.firebaseio.com/"
        })
        
        firebase_db = db.reference()
        firebase_initialized = True
        logger.info(f"✅ Firebase initialized: {project_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Firebase error: {e}")
        return False

# Initialize Firebase
init_firebase()

# Telegram Bot
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML', threaded=False)

# ==================== DATABASE FUNCTIONS ====================

def get_user(uid):
    if not firebase_db:
        return None
    try:
        return firebase_db.child('users').child(str(uid)).get()
    except:
        return None

def update_user(uid, data):
    if not firebase_db:
        return False
    try:
        firebase_db.child('users').child(str(uid)).update(data)
        return True
    except:
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
        return True
    except:
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
    # Referral
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
            except:
                pass
    return True

# ==================== DEEPSEEK ====================

def query_deepseek(messages):
    try:
        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {DEEPSEEK_API_KEY}'}
        payload = {'model': DEEPSEEK_MODEL, 'messages': messages, 'temperature': 0.7, 'max_tokens': 500}
        resp = requests.post(f'{DEEPSEEK_BASE_URL}/v1/chat/completions', headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content']
        return "AI service unavailable."
    except:
        return "Error occurred."

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
        types.InlineKeyboardButton("✅ Verify Instagram", callback_data="verify_instagram")
    )
    return kb

# ==================== BOT COMMANDS ====================

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
        
        cap = (f"👋 <b>Welcome!</b>\n\n"
               f"🇮 <b>India's #1 Earning Bot</b>\n\n"
               f"💡 <i>\"Success is the courage to continue.\"</i>\n\n"
               f"📊 <b>Your Stats:</b>\n"
               f"💰 Balance: ₹{user.get('balance',0)}\n"
               f"📦 Plan: {user.get('plan','free').upper()}\n"
               f"✅ Tasks: {user.get('tasks_completed',0)}\n\n"
               f"Use /help")
        try:
            bot.send_photo(msg.chat.id, WELCOME_PHOTO, caption=cap, reply_markup=main_menu())
        except:
            bot.send_message(msg.chat.id, cap.replace('<b>','').replace('</b>',''), reply_markup=main_menu())
    except Exception as e:
        logger.error(f"Start error: {e}")

@bot.message_handler(commands=['help'])
def cmd_help(msg):
    txt = ("📚 <b>Commands:</b>\n\n"
           "/start - Start bot\n"
           "/balance - Check balance\n"
           "/tasks - View tasks\n"
           "/referrals - Your referrals\n"
           "/upgrade - Upgrade plan\n"
           "/withdraw - Withdraw\n"
           "/stats - Your stats\n"
           "/support - AI Support")
    bot.send_message(msg.chat.id, txt, reply_markup=main_menu())

@bot.message_handler(commands=['balance'])
def cmd_balance(msg):
    user = get_user(msg.from_user.id)
    if not user:
        bot.send_message(msg.chat.id, "Use /start")
        return
    mult = "2x" if user.get('plan')=='pro' else "1x"
    txt = (f"💰 <b>Balance</b>\n"
           f"Available: ₹{user.get('balance',0):.2f}\n"
           f"Plan: {user.get('plan','free').upper()} ({mult})\n"
           f"Total: ₹{user.get('total_earned',0):.2f}")
    bot.send_message(msg.chat.id, txt, reply_markup=main_menu())

@bot.message_handler(commands=['tasks'])
def cmd_tasks(msg):
    user = get_user(msg.from_user.id)
    if not user:
        bot.send_message(msg.chat.id, "Use /start")
        return
    if not firebase_db:
        bot.send_message(msg.chat.id, "DB unavailable")
        return
    tasks = firebase_db.child('tasks').get() or {}
    kb = types.InlineKeyboardMarkup(row_width=1)
    for tid, t in tasks.items():
        if t.get('active', True):
            reward = t.get('reward', 10) * (2 if user.get('plan')=='pro' else 1)
            kb.add(types.InlineKeyboardButton(f"💰 {t.get('title')} - ₹{reward}", callback_data=f"task_{tid}"))
    bot.send_message(msg.chat.id, "📋 <b>Tasks</b>", reply_markup=kb)

@bot.message_handler(commands=['referrals'])
def cmd_referrals(msg):
    user = get_user(msg.from_user.id)
    if not user:
        bot.send_message(msg.chat.id, "Use /start")
        return
    refs = user.get('referrals', [])
    code = msg.from_user.id
    comm = sum((get_user(r).get('total_earned',0)*0.10) for r in refs if get_user(r))
    txt = (f"👥 <b>Referrals</b>\n\n"
           f"🔗 <code>https://t.me/{bot.get_me().username}?start={code}</code>\n\n"
           f"Total: {len(refs)} | Commission: ₹{comm:.2f}\n"
           f"Rate: 10% lifetime")
    bot.send_message(msg.chat.id, txt, reply_markup=main_menu())

@bot.message_handler(commands=['upgrade'])
def cmd_upgrade(msg):
    user = get_user(msg.from_user.id)
    if not user:
        bot.send_message(msg.chat.id, "Use /start")
        return
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("💰 ₹100 - PRO (2x)", callback_data="upgrade_pro"),
        types.InlineKeyboardButton("📢 ₹500 - ADVERTISER", callback_data="upgrade_advertiser")
    )
    txt = (f"💎 <b>Upgrade</b>\nCurrent: {user.get('plan','free').upper()}\n\n"
           f"🥇 PRO ₹100: 2x rewards\n"
           f"🏢 ADVERTISER ₹500: Submit tasks\n\n"
           f"💳 UPI: {UPI_ID}")
    bot.send_message(msg.chat.id, txt, reply_markup=kb)

@bot.message_handler(commands=['withdraw'])
def cmd_withdraw(msg):
    user = get_user(msg.from_user.id)
    if not user:
        bot.send_message(msg.chat.id, "Use /start")
        return
    bal = user.get('balance', 0)
    if bal < 100:
        bot.send_message(msg.chat.id, f"Min: ₹100 | Balance: ₹{bal}", reply_markup=main_menu())
        return
    kb = types.InlineKeyboardMarkup(row_width=1)
    for amt in [100, 500, 1000]:
        kb.add(types.InlineKeyboardButton(f"₹{amt}", callback_data=f"withdraw_{amt}"))
    bot.send_message(msg.chat.id, f"💸 Withdraw\nBalance: ₹{bal}", reply_markup=kb)

@bot.message_handler(commands=['stats'])
def cmd_stats(msg):
    user = get_user(msg.from_user.id)
    if not user:
        bot.send_message(msg.chat.id, "Use /start")
        return
    txt = (f"📊 <b>Stats</b>\n"
           f"Balance: ₹{user.get('balance',0):.2f}\n"
           f"Earned: ₹{user.get('total_earned',0):.2f}\n"
           f"Tasks: {user.get('tasks_completed',0)}\n"
           f"Referrals: {len(user.get('referrals',[]))}\n"
           f"Plan: {user.get('plan','free').upper()}")
    bot.send_message(msg.chat.id, txt, reply_markup=main_menu())

@bot.message_handler(commands=['support'])
def cmd_support(msg):
    m = bot.send_message(msg.chat.id, "🎧 Describe your issue:", reply_markup=types.ForceReply())
    bot.register_next_step_handler(m, process_support)

def process_support(msg):
    if not msg.text:
        return
    user = get_user(msg.from_user.id)
    sys_msg = {"role": "system", "content": f"Support for earning bot. PRO=₹100=2x, ADVERTISER=₹500, referral=10%, withdraw min ₹100, UPI:{UPI_ID}"}
    usr_msg = {"role": "user", "content": f"User:{msg.from_user.first_name} Plan:{user.get('plan','free') if user else '?'} Q:{msg.text}"}
    resp = query_deepseek([sys_msg, usr_msg])
    bot.send_message(msg.chat.id, f"🎧 Support:\n\n{resp}", reply_markup=main_menu())

# ==================== CALLBACKS ====================

@bot.callback_query_handler(func=lambda c: c.data.startswith('menu_'))
def cb_menu(call):
    action = call.data.replace('menu_', '')
    handlers = {
        'balance': cmd_balance, 'tasks': cmd_tasks, 'referrals': cmd_referrals,
        'upgrade': cmd_upgrade, 'withdraw': cmd_withdraw, 'stats': cmd_stats, 'support': cmd_support
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
        bot.answer_callback_query(call.id, "Error", show_alert=True)
        return
    if not user.get('verified_youtube') or not user.get('verified_instagram'):
        bot.send_message(uid, "⚠️ Verify first", reply_markup=verify_kb())
        bot.answer_callback_query(call.id, "Verify first")
        return
    if not firebase_db:
        bot.answer_callback_query(call.id, "DB error", show_alert=True)
        return
    task = firebase_db.child('tasks').child(tid).get()
    if not task:
        bot.answer_callback_query(call.id, "Not found", show_alert=True)
        return
    if tid in user.get('completed_tasks', []):
        bot.answer_callback_query(call.id, "Already done", show_alert=True)
        return
    reward = task.get('reward',10) * (2 if user.get('plan')=='pro' else 1)
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("🔗 Open", url=task.get('link','#')),
        types.InlineKeyboardButton("✅ Done", callback_data=f"complete_{tid}")
    )
    bot.send_message(uid, f"📋 {task.get('title')}\n💰 ₹{reward}", reply_markup=kb)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('complete_'))
def cb_complete(call):
    tid = call.data.replace('complete_', '')
    uid = call.from_user.id
    if not firebase_db:
        bot.answer_callback_query(call.id, "Error", show_alert=True)
        return
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
        bot.answer_callback_query(call.id, f"✅ +₹{reward}")
    else:
        bot.answer_callback_query(call.id, "Error", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith('verify_'))
def cb_verify(call):
    uid = call.from_user.id
    platform = call.data.replace('verify_', '')
    if platform == 'youtube':
        update_user(uid, {'verified_youtube': True})
        bot.answer_callback_query(call.id, "✅ YouTube", show_alert=True)
    elif platform == 'instagram':
        update_user(uid, {'verified_instagram': True})
        bot.answer_callback_query(call.id, "✅ Instagram", show_alert=True)
    user = get_user(uid)
    if user and user.get('verified_youtube') and user.get('verified_instagram'):
        bot.edit_message_text("✅ All verified!", call.message.chat.id, call.message.message_id, reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: c.data.startswith('upgrade_'))
def cb_upgrade(call):
    plan = call.data.replace('upgrade_', '')
    uid = call.from_user.id
    amt = 100 if plan == 'pro' else 500
    pname = 'PRO' if plan == 'pro' else 'ADVERTISER'
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("✅ Paid", callback_data=f"paid_{plan}"))
    bot.send_message(uid, f"💎 {pname} - ₹{amt}\nUPI: {UPI_ID}\nClick after payment", reply_markup=kb)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('paid_'))
def cb_paid(call):
    plan = call.data.replace('paid_', '')
    uid = call.from_user.id
    if ADMIN_ID:
        try:
            bot.send_message(ADMIN_ID, f"🔔 {call.from_user.first_name} | {plan.upper()}")
        except:
            pass
    bot.send_message(uid, "✅ Submitted for verification", reply_markup=main_menu())
    bot.answer_callback_query(call.id, "Submitted")

@bot.callback_query_handler(func=lambda c: c.data.startswith('withdraw_'))
def cb_withdraw(call):
    amt = int(call.data.replace('withdraw_', ''))
    uid = call.from_user.id
    user = get_user(uid)
    if not user or user.get('balance',0) < amt:
        bot.answer_callback_query(call.id, "Insufficient", show_alert=True)
        return
    if firebase_db:
        firebase_db.child('withdrawals').push({
            'user_id': uid, 'amount': amt, 'status': 'pending',
            'requested_at': datetime.now().isoformat()
        })
    bot.send_message(uid, f"💸 ₹{amt} requested\n24-48 hrs", reply_markup=main_menu())
    bot.answer_callback_query(call.id, "Requested")

# ==================== FLASK ROUTES (VERCEL) ====================

@app.route('/api/webhook', methods=['POST'])
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

@app.route('/api/set-webhook', methods=['GET'])
@app.route('/set-webhook', methods=['GET'])
def set_webhook():
    webhook_url = os.getenv('WEBHOOK_URL', request.host_url.rstrip('/') + '/webhook')
    try:
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        return jsonify({'status':'success','webhook':webhook_url})
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500

@app.route('/api', methods=['GET'])
@app.route('/', methods=['GET'])
def health():
    return jsonify({
        'status':'ok',
        'bot':'running' if BOT_TOKEN else 'no_token',
        'firebase':'connected' if firebase_db else 'disconnected',
        'initialized': firebase_initialized
    })

@app.route('/api/test-db', methods=['GET'])
@app.route('/test-db', methods=['GET'])
def test_db():
    if not firebase_db:
        return jsonify({'status':'error','message':'Firebase not initialized'}), 500
    try:
        firebase_db.child('health').push({'ok':True,'ts':datetime.now().isoformat()})
        return jsonify({'status':'success','message':'Firebase OK'})
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500

# Vercel serverless handler
def handler(request):
    return app(request.environ, lambda *args: None)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
