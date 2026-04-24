import os
import json
import logging
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, db

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.getenv('BOT_TOKEN', '8701635891:AAFmgU89KRhd2dhE-PqRY-mBmGy_SxQEGOg')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', 'sk-783d645ce9e84eb8b954786a016561ea')
DEEPSEEK_URL = 'https://api.deepseek.com/v1/chat/completions'
DEEPSEEK_MODEL = 'deepseek-chat'

# Payment & Links
UPI_ID = os.getenv('UPI_ID', '8543083014@mbk')
AD_LINK = os.getenv('AD_LINK', 'https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b')
WELCOME_PHOTO = 'https://i.ibb.co/h1m0cc1W/6a74f155-a6b7-499f-ad34-c1a3989433e0.jpg'

# Social Media
YOUTUBE_CHANNEL = '@USSoccerPulse'
INSTAGRAM_HANDLE = '@digital_rockstar_m'

# ==================== INITIALIZATION ====================
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ==================== FIREBASE SETUP ====================
firebase_db = None

try:
    # Method 1: Try Base64 encoded config
    firebase_config_b64 = os.getenv('FIREBASE_CONFIG_BASE64')
    if firebase_config_b64:
        import base64
        decoded_config = base64.b64decode(firebase_config_b64).decode('utf-8')
        firebase_config = json.loads(decoded_config)
    else:
        # Method 2: Try JSON string config
        firebase_config_json = os.getenv('FIREBASE_CONFIG_JSON')
        if firebase_config_json:
            firebase_config = json.loads(firebase_config_json)
        else:
            # Method 3: Individual environment variables
            private_key = os.getenv('FIREBASE_PRIVATE_KEY', '')
            if '\\n' in private_key:
                private_key = private_key.replace('\\n', '\n')
            
            firebase_config = {
                "type": "service_account",
                "project_id": os.getenv('FIREBASE_PROJECT_ID', 'earn-bot-2026'),
                "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID', ''),
                "private_key": private_key,
                "client_email": os.getenv('FIREBASE_CLIENT_EMAIL', ''),
                "client_id": os.getenv('FIREBASE_CLIENT_ID', ''),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_X509_CERT_URL', '')
            }
    
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred, {
        'databaseURL': os.getenv('FIREBASE_DATABASE_URL', 'https://earn-bot-2026-default-rtdb.firebaseio.com/')
    })
    firebase_db = db.reference()
    logger.info("✅ Firebase initialized successfully")
    
except Exception as e:
    logger.error(f"❌ Firebase initialization error: {e}")
    firebase_db = None

# ==================== HELPER FUNCTIONS ====================

def get_user(user_id):
    """Get user data from Firebase"""
    if not firebase_db:
        return None
    try:
        return firebase_db.child('users').child(str(user_id)).get()
    except:
        return None

def update_user(user_id, data):
    """Update user data in Firebase"""
    if not firebase_db:
        return False
    try:
        firebase_db.child('users').child(str(user_id)).update(data)
        return True
    except:
        return False

def create_user(user_id, username, first_name, referrer_id=None):
    """Create new user in database"""
    if not firebase_db:
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
        'completed_tasks': [],
        'submitted_tasks': []
    }
    
    try:
        firebase_db.child('users').child(str(user_id)).set(user_data)
        
        # Add to referrer's list
        if referrer_id:
            referrer = firebase_db.child('users').child(str(referrer_id)).get()
            if referrer:
                referrals = referrer.get('referrals', [])
                if user_id not in referrals:
                    referrals.append(user_id)
                    firebase_db.child('users').child(str(referrer_id)).update({'referrals': referrals})
        
        return True
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return False

def add_balance(user_id, amount, task_id=None):
    """Add balance and handle referrals"""
    user = get_user(user_id)
    if not user:
        return False
    
    # Check plan multiplier
    multiplier = 2 if user.get('plan') == 'pro' else 1
    final_amount = amount * multiplier
    
    # Update user
    new_balance = user.get('balance', 0) + final_amount
    new_total = user.get('total_earned', 0) + final_amount
    new_tasks = user.get('tasks_completed', 0) + 1
    
    update_user(user_id, {
        'balance': new_balance,
        'total_earned': new_total,
        'tasks_completed': new_tasks
    })
    
    # Give 10% to referrer
    referrer_id = user.get('referrer_id')
    if referrer_id:
        referrer = get_user(referrer_id)
        if referrer:
            commission = final_amount * 0.10
            ref_balance = referrer.get('balance', 0) + commission
            ref_total = referrer.get('total_earned', 0) + commission
            
            update_user(referrer_id, {
                'balance': ref_balance,
                'total_earned': ref_total
            })
            
            # Notify referrer
            try:
                bot.send_message(
                    referrer_id,
                    f"🎉 <b>Referral Earned!</b>\n\n"
                    f"Your referral completed a task.\n"
                    f"💰 You got: ₹{commission:.2f}\n"
                    f"💵 New Balance: ₹{ref_balance:.2f}",
                    parse_mode='HTML'
                )
            except:
                pass
    
    return True

async def query_deepseek(prompt, user_context=""):
    """Query DeepSeek AI"""
    try:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}'
        }
        
        messages = [
            {
                "role": "system",
                "content": "You are a helpful support assistant for UltimateMediaSearchBot - an Indian earning platform. Be friendly and professional."
            },
            {
                "role": "user",
                "content": f"{user_context}\n\nQuestion: {prompt}"
            }
        ]
        
        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return "Sorry, I'm having trouble right now. Please try again later."
    
    except Exception as e:
        logger.error(f"DeepSeek error: {e}")
        return "An error occurred. Please try again."

# ==================== KEYBOARDS ====================

def main_keyboard():
    """Main menu keyboard"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 Balance", callback_data="menu_balance"),
        types.InlineKeyboardButton("📋 Tasks", callback_data="menu_tasks"),
        types.InlineKeyboardButton("👥 Referrals", callback_data="menu_referrals"),
        types.InlineKeyboardButton("💳 Upgrade", callback_data="menu_upgrade"),
        types.InlineKeyboardButton("💸 Withdraw", callback_data="menu_withdraw"),
        types.InlineKeyboardButton("📊 Stats", callback_data="menu_stats"),
        types.InlineKeyboardButton("🎧 Support", callback_data="menu_support")
    )
    return markup

def verification_keyboard(youtube_done, insta_done):
    """Verification keyboard"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    if not youtube_done:
        markup.add(types.InlineKeyboardButton("✅ Verify YouTube", callback_data="verify_youtube"))
    if not insta_done:
        markup.add(types.InlineKeyboardButton("✅ Verify Instagram", callback_data="verify_instagram"))
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_verify"))
    return markup

# ==================== COMMAND HANDLERS ====================

@bot.message_handler(commands=['start'])
def cmd_start(message):
    """Handle /start command"""
    user_id = message.from_user.id
    username = message.from_user.username or 'User'
    first_name = message.from_user.first_name
    
    # Check referral
    referrer_id = None
    if len(message.text.split()) > 1:
        try:
            ref_code = message.text.split()[1]
            referrer_id = int(ref_code)
            if referrer_id == user_id:
                referrer_id = None
        except:
            referrer_id = None
    
    # Create or get user
    user = get_user(user_id)
    if not user:
        create_user(user_id, username, first_name, referrer_id)
        user = get_user(user_id)
    
    caption = (
        f"👋 <b>Welcome to UltimateMediaSearchBot!</b>\n\n"
        f"🇮🇳 <b>India's #1 Destination</b> for Earning & Promotion!\n\n"
        f"💡 <i>\"Success is not final, failure is not fatal: "
        f"it is the courage to continue that counts.\"</i>\n\n"
        f"🚀 <b>Start earning by completing simple tasks!</b>\n\n"
        f"📊 <b>Your Stats:</b>\n"
        f"💰 Balance: ₹{user.get('balance', 0)}\n"
        f"📦 Plan: {user.get('plan', 'free').upper()}\n"
        f"✅ Tasks: {user.get('tasks_completed', 0)}\n\n"
        f"Use /help for commands."
    )
    
    try:
        bot.send_photo(message.chat.id, WELCOME_PHOTO, caption=caption, reply_markup=main_keyboard())
    except:
        bot.send_message(message.chat.id, caption.replace('<b>', '').replace('</b>', ''), reply_markup=main_keyboard())

@bot.message_handler(commands=['help'])
def cmd_help(message):
    """Handle /help command"""
    help_text = (
        "📚 <b>Available Commands:</b>\n\n"
        "🏠 <b>/start</b> - Start the bot\n"
        "💰 <b>/balance</b> - Check balance\n"
        "📋 <b>/tasks</b> - View tasks\n"
        "👥 <b>/referrals</b> - Your referrals\n"
        "💳 <b>/upgrade</b> - Upgrade plan\n"
        "💸 <b>/withdraw</b> - Withdraw\n"
        "📝 <b>/addtask</b> - Add task (Advertisers)\n"
        "🎧 <b>/support</b> - AI Support\n"
        "📊 <b>/stats</b> - Statistics\n\n"
        "💡 <b>Tips:</b>\n"
        "• PRO plan = 2x rewards\n"
        "• 10% referral commission\n"
        "• Min withdrawal: ₹100"
    )
    bot.send_message(message.chat.id, help_text, reply_markup=main_keyboard())

@bot.message_handler(commands=['balance'])
def cmd_balance(message):
    """Handle /balance command"""
    user = get_user(message.from_user.id)
    if not user:
        bot.send_message(message.chat.id, "User not found. Please /start")
        return
    
    multiplier = "2x" if user.get('plan') == 'pro' else "1x"
    text = (
        f"💰 <b>Your Balance</b>\n\n"
        f"💵 Available: ₹{user.get('balance', 0):.2f}\n"
        f"📦 Plan: {user.get('plan', 'upper').upper()} ({multiplier})\n"
        f"📈 Total Earned: ₹{user.get('total_earned', 0):.2f}\n\n"
        f"💡 Upgrade to PRO for 2x rewards!\n"
        f"Use /upgrade"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard())

@bot.message_handler(commands=['tasks'])
def cmd_tasks(message):
    """Handle /tasks command"""
    user = get_user(message.from_user.id)
    if not user:
        bot.send_message(message.chat.id, "User not found. Please /start")
        return
    
    if not firebase_db:
        bot.send_message(message.chat.id, "Database not connected")
        return
    
    tasks = firebase_db.child('tasks').get()
    
    if not tasks:
        bot.send_message(message.chat.id, "📭 No tasks available. Check back later!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for task_id, task_data in tasks.items():
        if task_data.get('active', True):
            reward = task_data.get('reward', 10)
            if user.get('plan') == 'pro':
                reward *= 2
            
            btn_text = f"💰 {task_data.get('title', 'Task')} - ₹{reward}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"task_{task_id}"))
    
    bot.send_message(
        message.chat.id,
        "📋 <b>Available Tasks</b>\n\nPRO members get 2x rewards!",
        reply_markup=markup
    )

@bot.message_handler(commands=['referrals'])
def cmd_referrals(message):
    """Handle /referrals command"""
    user = get_user(message.from_user.id)
    if not user:
        bot.send_message(message.chat.id, "User not found. Please /start")
        return
    
    referrals = user.get('referrals', [])
    ref_code = message.from_user.id
    
    # Calculate commission
    total_commission = 0
    for ref_id in referrals:
        ref_data = get_user(ref_id)
        if ref_data:
            total_commission += ref_data.get('total_earned', 0) * 0.10
    
    text = (
        f"👥 <b>Your Referrals</b>\n\n"
        f"🔗 <b>Referral Link:</b>\n"
        f"<code>https://t.me/{bot.get_me().username}?start={ref_code}</code>\n\n"
        f"📊 <b>Stats:</b>\n"
        f"👤 Total: {len(referrals)}\n"
        f"💰 Commission: ₹{total_commission:.2f}\n"
        f"💵 Rate: 10% lifetime\n\n"
        f"<i>Share & earn 10% on every task!</i>"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard())

@bot.message_handler(commands=['upgrade'])
def cmd_upgrade(message):
    """Handle /upgrade command"""
    user = get_user(message.from_user.id)
    if not user:
        bot.send_message(message.chat.id, "User not found. Please /start")
        return
    
    current = user.get('plan', 'free')
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💰 ₹100 - PRO (2x)", callback_data="upgrade_pro"),
        types.InlineKeyboardButton("📢 ₹500 - ADVERTISER", callback_data="upgrade_advertiser"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_upgrade")
    )
    
    text = (
        f"💎 <b>Upgrade Plan</b>\n\n"
        f"📦 Current: <b>{current.upper()}</b>\n\n"
        f"<b>Plans:</b>\n\n"
        f"🥇 <b>PRO - ₹100</b>\n"
        f"• 2x rewards on tasks\n"
        f"• Priority support\n\n"
        f"🏢 <b>ADVERTISER - ₹500</b>\n"
        f"• All PRO features\n"
        f"• Submit your tasks\n"
        f"• Reach thousands\n\n"
        f"💳 UPI: {UPI_ID}"
    )
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(commands=['withdraw'])
def cmd_withdraw(message):
    """Handle /withdraw command"""
    user = get_user(message.from_user.id)
    if not user:
        bot.send_message(message.chat.id, "User not found. Please /start")
        return
    
    balance = user.get('balance', 0)
    min_withdraw = 100
    
    if balance < min_withdraw:
        bot.send_message(
            message.chat.id,
            f"❌ <b>Insufficient Balance</b>\n\n"
            f"Minimum: ₹{min_withdraw}\n"
            f"Yours: ₹{balance}\n\n"
            f"Complete more tasks!",
            reply_markup=main_keyboard()
        )
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💵 ₹100", callback_data="withdraw_100"),
        types.InlineKeyboardButton("💵 ₹500", callback_data="withdraw_500"),
        types.InlineKeyboardButton("💵 ₹1000", callback_data="withdraw_1000"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_withdraw")
    )
    
    text = (
        f"💸 <b>Withdraw</b>\n\n"
        f"💰 Balance: ₹{balance}\n"
        f"📊 Minimum: ₹{min_withdraw}\n\n"
        f"<b>Select amount:</b>"
    )
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(commands=['addtask'])
def cmd_addtask(message):
    """Handle /addtask command (Advertisers only)"""
    user = get_user(message.from_user.id)
    if not user:
        bot.send_message(message.chat.id, "User not found. Please /start")
        return
    
    if user.get('plan') != 'advertiser':
        bot.send_message(
            message.chat.id,
            "❌ <b>Advertiser Plan Required</b>\n\n"
            "Upgrade to submit tasks.\n"
            "Use /upgrade",
            reply_markup=main_keyboard()
        )
        return
    
    msg = bot.send_message(
        message.chat.id,
        "📝 <b>New Task</b>\n\nSend task title:",
        reply_markup=types.ForceReply()
    )
    bot.register_next_step_handler(msg, process_task_title)

def process_task_title(message):
    """Process task title"""
    if not message.text:
        bot.send_message(message.chat.id, "❌ Invalid. Try again.")
        return
    
    task_data = {
        'title': message.text,
        'advertiser_id': message.from_user.id,
        'created_at': datetime.now().isoformat()
    }
    
    msg = bot.send_message(
        message.chat.id,
        "📝 Send description:",
        reply_markup=types.ForceReply()
    )
    bot.register_next_step_handler(msg, lambda m: process_task_desc(m, task_data))

def process_task_desc(message, task_data):
    """Process task description"""
    if not message.text:
        bot.send_message(message.chat.id, "❌ Invalid. Try again.")
        return
    
    task_data['description'] = message.text
    
    msg = bot.send_message(
        message.chat.id,
        "💰 Send reward (₹):",
        reply_markup=types.ForceReply()
    )
    bot.register_next_step_handler(msg, lambda m: process_task_reward(m, task_data))

def process_task_reward(message, task_data):
    """Process task reward"""
    try:
        reward = float(message.text)
        if reward < 1:
            raise ValueError("Min ₹1")
        
        task_data['reward'] = reward
        
        msg = bot.send_message(
            message.chat.id,
            "🔗 Send task URL:",
            reply_markup=types.ForceReply()
        )
        bot.register_next_step_handler(msg, lambda m: process_task_url(m, task_data))
    
    except ValueError as e:
        bot.send_message(message.chat.id, f"❌ Error: {e}")

def process_task_url(message, task_data):
    """Process task URL"""
    if not message.text or not message.text.startswith('http'):
        bot.send_message(message.chat.id, "❌ Valid URL required (http://...)")
        return
    
    task_data['link'] = message.text
    task_data['active'] = True
    
    if firebase_db:
        new_task = firebase_db.child('tasks').push()
        new_task.set(task_data)
        
        # Add to user's tasks
        user_ref = firebase_db.child('users').child(str(message.from_user.id))
        user_data = user_ref.get()
        tasks = user_data.get('submitted_tasks', [])
        tasks.append(new_task.key)
        user_ref.update({'submitted_tasks': tasks})
    
    bot.send_message(
        message.chat.id,
        "✅ <b>Task Submitted!</b>\n\n"
        f"Title: {task_data['title']}\n"
        f"Reward: ₹{task_data['reward']}\n\n"
        "Task is now live!",
        reply_markup=main_keyboard()
    )

@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    """Handle /stats command"""
    user = get_user(message.from_user.id)
    if not user:
        bot.send_message(message.chat.id, "User not found. Please /start")
        return
    
    text = (
        f"📊 <b>Your Statistics</b>\n\n"
        f"💰 Balance: ₹{user.get('balance', 0):.2f}\n"
        f"📈 Total: ₹{user.get('total_earned', 0):.2f}\n"
        f"✅ Tasks: {user.get('tasks_completed', 0)}\n"
        f"👥 Referrals: {len(user.get('referrals', []))}\n"
        f"📦 Plan: {user.get('plan', 'free').upper()}\n"
        f"📅 Joined: {user.get('joined_date', 'N/A')[:10]}\n\n"
        f"🎯 <b>Verification:</b>\n"
        f"{'✅' if user.get('verified_youtube') else '❌'} YouTube: {YOUTUBE_CHANNEL}\n"
        f"{'✅' if user.get('verified_instagram') else '❌'} Instagram: {INSTAGRAM_HANDLE}"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard())

@bot.message_handler(commands=['support'])
def cmd_support(message):
    """Handle /support command"""
    msg = bot.send_message(
        message.chat.id,
        "🎧 <b>AI Support</b>\n\n"
        "Describe your question:",
        reply_markup=types.ForceReply()
    )
    bot.register_next_step_handler(msg, process_support)

async def process_support(message):
    """Process support query"""
    if not message.text:
        bot.send_message(message.chat.id, "❌ Invalid. Try again.")
        return
    
    bot.send_chat_action(message.chat.id, 'typing')
    
    user = get_user(message.from_user.id)
    context = f"User: {message.from_user.first_name}\nPlan: {user.get('plan', 'free') if user else 'unknown'}"
    
    response = await query_deepseek(message.text, context)
    
    bot.send_message(
        message.chat.id,
        f"🎧 <b>Support:</b>\n\n{response}",
        reply_markup=main_keyboard()
    )

# ==================== CALLBACK HANDLERS ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith('task_'))
def handle_task(call):
    """Handle task selection"""
    task_id = call.data.replace('task_', '')
    user_id = call.from_user.id
    
    user = get_user(user_id)
    if not user:
        bot.answer_callback_query(call.id, "Error: User not found", show_alert=True)
        return
    
    # Check verification
    if not user.get('verified_youtube') or not user.get('verified_instagram'):
        markup = verification_keyboard(
            user.get('verified_youtube', False),
            user.get('verified_instagram', False)
        )
        
        bot.send_message(
            user_id,
            "⚠️ <b>Verification Required</b>\n\n"
            f"1️⃣ Follow: {YOUTUBE_CHANNEL}\n"
            f"2️⃣ Follow: {INSTAGRAM_HANDLE}\n\n"
            "Click below to verify:",
            reply_markup=markup
        )
        bot.answer_callback_query(call.id, "Verify first")
        return
    
    # Get task
    if not firebase_db:
        bot.answer_callback_query(call.id, "Database error", show_alert=True)
        return
    
    task = firebase_db.child('tasks').child(task_id).get()
    if not task:
        bot.answer_callback_query(call.id, "Task not found", show_alert=True)
        return
    
    # Check if completed
    completed = user.get('completed_tasks', [])
    if task_id in completed:
        bot.answer_callback_query(call.id, "Already completed!", show_alert=True)
        return
    
    # Check cooldown
    last_task = user.get('last_task_time')
    if last_task:
        last_time = datetime.fromisoformat(last_task)
        if datetime.now() - last_time < timedelta(minutes=1):
            remaining = 60 - (datetime.now() - last_time).seconds
            bot.answer_callback_query(call.id, f"Wait {remaining}s", show_alert=True)
            return
    
    # Show task
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔗 Open Link", url=task.get('link', '#')),
        types.InlineKeyboardButton("✅ Completed", callback_data=f"complete_{task_id}")
    )
    
    reward = task.get('reward', 10)
    if user.get('plan') == 'pro':
        reward *= 2
    
    bot.send_message(
        user_id,
        f"📋 <b>{task.get('title')}</b>\n\n"
        f"📝 {task.get('description', '')}\n\n"
        f"💰 Reward: ₹{reward}\n\n"
        f"Open link, complete, then click 'Completed'",
        reply_markup=markup
    )
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('complete_'))
def handle_complete(call):
    """Handle task completion"""
    task_id = call.data.replace('complete_', '')
    user_id = call.from_user.id
    
    if not firebase_db:
        bot.answer_callback_query(call.id, "Database error", show_alert=True)
        return
    
    task = firebase_db.child('tasks').child(task_id).get()
    if not task:
        bot.answer_callback_query(call.id, "Task not found", show_alert=True)
        return
    
    user = get_user(user_id)
    reward = task.get('reward', 10)
    
    if user.get('plan') == 'pro':
        reward *= 2
    
    if add_balance(user_id, task.get('reward', 10), task_id):
        # Mark completed
        user_ref = firebase_db.child('users').child(str(user_id))
        completed = user.get('completed_tasks', [])
        completed.append(task_id)
        user_ref.update({
            'completed_tasks': completed,
            'last_task_time': datetime.now().isoformat()
        })
        
        bot.answer_callback_query(call.id, f"✅ ₹{reward} added!", show_alert=False)
        
        bot.send_message(
            user_id,
            f"✅ <b>Completed!</b>\n\n"
            f"💰 ₹{reward} added\n"
            f"📊 Balance: ₹{user.get('balance', 0) + reward}",
            reply_markup=main_keyboard()
        )
    else:
        bot.answer_callback_query(call.id, "Error. Try again.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith('verify_'))
def handle_verify(call):
    """Handle verification"""
    user_id = call.from_user.id
    platform = call.data.replace('verify_', '')
    
    if platform == 'youtube':
        update_user(user_id, {'verified_youtube': True})
        bot.answer_callback_query(call.id, "✅ YouTube verified!", show_alert=True)
    elif platform == 'instagram':
        update_user(user_id, {'verified_instagram': True})
        bot.answer_callback_query(call.id, "✅ Instagram verified!", show_alert=True)
    
    # Update message
    user = get_user(user_id)
    markup = verification_keyboard(
        user.get('verified_youtube', False),
        user.get('verified_instagram', False)
    )
    
    if user.get('verified_youtube') and user.get('verified_instagram'):
        bot.edit_message_text(
            "✅ <b>All Verified!</b>\n\nStart completing tasks!",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_keyboard()
        )
    else:
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith('upgrade_'))
def handle_upgrade(call):
    """Handle upgrade"""
    plan_type = call.data.replace('upgrade_', '')
    
    if plan_type == 'pro':
        amount = 100
        benefits = "2x rewards"
    elif plan_type == 'advertiser':
        amount = 500
        benefits = "Submit tasks + 2x"
    else:
        bot.answer_callback_query(call.id, "Invalid", show_alert=True)
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("✅ Paid", callback_data=f"paid_{plan_type}"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_upgrade")
    )
    
    bot.send_message(
        call.from_user.id,
        f"💎 <b>Upgrade to {plan_type.upper()}</b>\n\n"
        f"💰 Amount: ₹{amount}\n"
        f"✨ Benefits: {benefits}\n\n"
        f"📲 Send to:\n"
        f"<code>{UPI_ID}</code>\n\n"
        f"After payment, click 'Paid'",
        reply_markup=markup
    )
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('paid_'))
def handle_paid(call):
    """Handle payment confirmation"""
    plan_type = call.data.replace('paid_', '')
    user_id = call.from_user.id
    
    # Notify admin (implement later)
    
    bot.send_message(
        user_id,
        "✅ <b>Payment Submitted!</b>\n\n"
        "Verification in 2-24 hours.\n"
        "You'll be notified.",
        reply_markup=main_keyboard()
    )
    
    bot.answer_callback_query(call.id, "Submitted for verification")

@bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw_'))
def handle_withdraw(call):
    """Handle withdrawal"""
    amount = int(call.data.replace('withdraw_', ''))
    user_id = call.from_user.id
    
    user = get_user(user_id)
    if not user:
        bot.answer_callback_query(call.id, "User not found", show_alert=True)
        return
    
    if user.get('balance', 0) < amount:
        bot.answer_callback_query(call.id, f"Insufficient balance", show_alert=True)
        return
    
    if firebase_db:
        withdrawal = {
            'user_id': user_id,
            'username': call.from_user.username,
            'amount': amount,
            'status': 'pending',
            'requested_at': datetime.now().isoformat()
        }
        firebase_db.child('withdrawals').push().set(withdrawal)
    
    bot.send_message(
        user_id,
        f"💸 <b>Withdrawal Request</b>\n\n"
        f"Amount: ₹{amount}\n"
        f"Status: Pending\n"
        f"UPI: {UPI_ID}\n\n"
        f"Processed in 24-48 hours.",
        reply_markup=main_keyboard()
    )
    
    bot.answer_callback_query(call.id, "Request submitted")

@bot.callback_query_handler(func=lambda call: call.data.startswith('menu_'))
def handle_menu(call):
    """Handle menu buttons"""
    action = call.data.replace('menu_', '')
    
    if action == 'balance':
        cmd_balance(call.message)
    elif action == 'tasks':
        cmd_tasks(call.message)
    elif action == 'referrals':
        cmd_referrals(call.message)
    elif action == 'upgrade':
        cmd_upgrade(call.message)
    elif action == 'withdraw':
        cmd_withdraw(call.message)
    elif action == 'stats':
        cmd_stats(call.message)
    elif action == 'support':
        cmd_support(call.message)
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_'))
def handle_cancel(call):
    """Handle cancel"""
    bot.edit_message_text(
        "❌ Cancelled.",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=main_keyboard()
    )
    bot.answer_callback_query(call.id, "Cancelled")

# ==================== FLASK ROUTES ====================

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle Telegram webhook"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return '', 403

@app.route('/set-webhook', methods=['GET'])
def set_webhook():
    """Set webhook"""
    webhook_url = os.getenv('WEBHOOK_URL', 'https://your-app.vercel.app/webhook')
    
    try:
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        return jsonify({'status': 'success', 'message': 'Webhook set'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'ok', 'message': 'Bot running'})

# ==================== MAIN ====================

if __name__ == '__main__':
    logger.info("Starting bot...")
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
