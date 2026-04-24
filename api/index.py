import os
import json
import logging
import requests
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, jsonify
import telebot
from telebot import types
from datetime import datetime, timedelta

# Configuration from Environment Variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', 'sk-783d645ce9e84eb8b954786a016561ea')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
UPI_ID = os.getenv('UPI_ID', '8543083014@mbk')
AD_LINK = os.getenv('AD_LINK', 'https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b')

# Social Media
YOUTUBE_CHANNEL = '@USSoccerPulse'
INSTAGRAM_HANDLE = '@digital_rockstar_m'

# Initialize Flask and Bot
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== FIREBASE INITIALIZATION ====================

firebase_db = None

try:
    # Method 1: Try FIREBASE_CONFIG_JSON (Recommended)
    firebase_config_json = os.getenv('FIREBASE_CONFIG_JSON')
    
    if firebase_config_json:
        logger.info("📄 Using FIREBASE_CONFIG_JSON...")
        firebase_config = json.loads(firebase_config_json)
        cred = credentials.Certificate(firebase_config)
    else:
        # Method 2: Try individual variables
        logger.info("📄 Using individual Firebase env variables...")
        private_key = os.getenv('FIREBASE_PRIVATE_KEY', '')
        
        # Fix newlines in private key
        if private_key and '\\n' in private_key:
            private_key = private_key.replace('\\n', '\n')
        
        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": os.getenv('FIREBASE_PROJECT_ID', 'earn-bot-2026'),
            "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
            "private_key": private_key,
            "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
            "client_id": os.getenv('FIREBASE_CLIENT_ID'),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_X509_CERT_URL')
        })
    
    # Initialize Firebase Admin
    firebase_config_dict = cred.credential if hasattr(cred, 'credential') else {}
    database_url = firebase_config_dict.get('databaseURL', os.getenv('FIREBASE_DATABASE_URL', 'https://earn-bot-2026-default-rtdb.firebaseio.com/'))
    
    firebase_admin.initialize_app(cred, {
        'databaseURL': database_url
    })
    
    firebase_db = db.reference()
    logger.info("✅ Firebase initialized successfully!")
    
except Exception as e:
    logger.error(f"❌ Firebase initialization error: {e}")
    logger.error(f"Error type: {type(e).__name__}")
    import traceback
    logger.error(traceback.format_exc())
    firebase_db = None

# ==================== HELPER FUNCTIONS ====================

def get_user_data(user_id):
    """Fetch user data from Firebase"""
    if not firebase_db:
        return None
    try:
        user_ref = firebase_db.child('users').child(str(user_id))
        return user_ref.get()
    except Exception as e:
        logger.error(f"Error fetching user data: {e}")
        return None

def update_user_data(user_id, data):
    """Update user data in Firebase"""
    if not firebase_db:
        return False
    try:
        user_ref = firebase_db.child('users').child(str(user_id))
        user_ref.update(data)
        return True
    except Exception as e:
        logger.error(f"Error updating user data: {e}")
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
        'last_task_time': None,
        'submitted_tasks': [],
        'completed_tasks': []
    }
    
    try:
        user_ref = firebase_db.child('users').child(str(user_id))
        user_ref.set(user_data)
        
        # Add to referrer's list
        if referrer_id:
            referrer_ref = firebase_db.child('users').child(str(referrer_id))
            referrer_data = referrer_ref.get()
            if referrer_data:
                referrals = referrer_data.get('referrals', [])
                if user_id not in referrals:
                    referrals.append(user_id)
                    referrer_ref.update({'referrals': referrals})
        
        logger.info(f"✅ User {user_id} created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return False

def add_balance(user_id, amount, task_id=None):
    """Add balance to user and give commission to referrer"""
    user_data = get_user_data(user_id)
    if not user_data:
        return False
    
    # Double rewards for PRO users
    multiplier = 2 if user_data.get('plan') == 'pro' else 1
    final_amount = amount * multiplier
    
    # Update user
    new_balance = user_data.get('balance', 0) + final_amount
    new_total_earned = user_data.get('total_earned', 0) + final_amount
    new_tasks_completed = user_data.get('tasks_completed', 0) + 1
    
    update_user_data(user_id, {
        'balance': new_balance,
        'total_earned': new_total_earned,
        'tasks_completed': new_tasks_completed,
        'last_task_time': datetime.now().isoformat()
    })
    
    # Give 10% commission to referrer
    referrer_id = user_data.get('referrer_id')
    if referrer_id:
        referrer_data = get_user_data(referrer_id)
        if referrer_data:
            commission = final_amount * 0.10
            referrer_balance = referrer_data.get('balance', 0) + commission
            referrer_total = referrer_data.get('total_earned', 0) + commission
            
            update_user_data(referrer_id, {
                'balance': referrer_balance,
                'total_earned': referrer_total
            })
            
            # Notify referrer
            try:
                bot.send_message(
                    referrer_id,
                    f"🎉 <b>Referral Commission!</b>\n\n"
                    f"Your referral completed a task.\n"
                    f"💰 You earned: ₹{commission:.2f}\n"
                    f"📊 New Balance: ₹{referrer_balance:.2f}",
                    parse_mode='HTML'
                )
            except:
                pass
    
    return True

async def query_deepseek(messages):
    """Query DeepSeek AI"""
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
        
        response = requests.post(
            f'{DEEPSEEK_BASE_URL}/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return "Sorry, I'm having trouble right now."
    
    except Exception as e:
        logger.error(f"DeepSeek error: {e}")
        return "An error occurred. Please try again."

# ==================== KEYBOARDS ====================

def main_menu_keyboard():
    """Main menu keyboard"""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("💰 Balance", callback_data="menu_balance"),
        types.InlineKeyboardButton("📋 Tasks", callback_data="menu_tasks"),
        types.InlineKeyboardButton("👥 Referrals", callback_data="menu_referrals"),
        types.InlineKeyboardButton("💳 Upgrade", callback_data="menu_upgrade"),
        types.InlineKeyboardButton("💸 Withdraw", callback_data="menu_withdraw"),
        types.InlineKeyboardButton("📊 Stats", callback_data="menu_stats"),
        types.InlineKeyboardButton("🎧 Support", callback_data="menu_support")
    )
    return keyboard

# ==================== COMMAND HANDLERS ====================

@bot.message_handler(commands=['start'])
def send_welcome(message):
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
    
    # Create user if not exists
    user_data = get_user_data(user_id)
    if not user_data:
        create_user(user_id, username, first_name, referrer_id)
        user_data = get_user_data(user_id)
    
    welcome_photo = "https://i.ibb.co/h1m0cc1W/6a74f155-a6b7-499f-ad34-c1a3989433e0.jpg"
    
    caption = (
        f"👋 <b>Welcome to UltimateMediaSearchBot!</b>\n\n"
        f"🇮 <b>India's #1 Destination</b> for Earning & Promotion!\n\n"
        f"💡 <i>\"Success is not final, failure is not fatal: "
        f"it is the courage to continue that counts.\"</i>\n\n"
        f"🚀 <b>Start earning today!</b>\n\n"
        f"📊 <b>Your Stats:</b>\n"
        f"💰 Balance: ₹{user_data.get('balance', 0)}\n"
        f"📦 Plan: {user_data.get('plan', 'free').upper()}\n"
        f"✅ Tasks: {user_data.get('tasks_completed', 0)}\n\n"
        f"Use /help to see all commands."
    )
    
    try:
        bot.send_photo(message.chat.id, welcome_photo, caption=caption, reply_markup=main_menu_keyboard())
    except:
        bot.send_message(message.chat.id, caption.replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', ''), reply_markup=main_menu_keyboard())

@bot.message_handler(commands=['help'])
def send_help(message):
    """Handle /help command"""
    help_text = (
        "📚 <b>Available Commands:</b>\n\n"
        "🏠 <b>/start</b> - Start the bot\n"
        "💰 <b>/balance</b> - Check balance\n"
        "📋 <b>/tasks</b> - View tasks\n"
        "👥 <b>/referrals</b> - Your referrals\n"
        "💳 <b>/upgrade</b> - Upgrade plan\n"
        "💸 <b>/withdraw</b> - Withdraw\n"
        "📝 <b>/submit_task</b> - Submit task (Advertisers)\n"
        "🎧 <b>/support</b> - AI Support\n"
        "📊 <b>/stats</b> - Statistics"
    )
    bot.send_message(message.chat.id, help_text, reply_markup=main_menu_keyboard())

@bot.message_handler(commands=['balance'])
def check_balance(message):
    """Handle /balance command"""
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        bot.send_message(message.chat.id, "User not found. Please /start")
        return
    
    plan = user_data.get('plan', 'free')
    multiplier = "2x" if plan == 'pro' else "1x"
    
    text = (
        f"💰 <b>Your Balance</b>\n\n"
        f"💵 Available: ₹{user_data.get('balance', 0):.2f}\n"
        f"📦 Plan: {plan.upper()} ({multiplier})\n"
        f"📈 Total: ₹{user_data.get('total_earned', 0):.2f}\n\n"
        f"Use /upgrade for 2x rewards!"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu_keyboard())

@bot.message_handler(commands=['tasks'])
def show_tasks(message):
    """Handle /tasks command"""
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        bot.send_message(message.chat.id, "User not found. Please /start")
        return
    
    if not firebase_db:
        bot.send_message(message.chat.id, "❌ Database not connected")
        return
    
    tasks_ref = firebase_db.child('tasks')
    tasks = tasks_ref.get() if tasks_ref else {}
    
    if not tasks:
        bot.send_message(message.chat.id, "📭 No tasks available")
        return
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    for task_id, task_data in tasks.items():
        if task_data.get('active', True):
            reward = task_data.get('reward', 10)
            if user_data.get('plan') == 'pro':
                reward *= 2
            
            btn_text = f"💰 {task_data.get('title', 'Task')} - ₹{reward}"
            keyboard.add(types.InlineKeyboardButton(btn_text, callback_data=f"task_{task_id}"))
    
    bot.send_message(
        message.chat.id,
        "📋 <b>Available Tasks</b>\n\nPRO = 2x rewards",
        reply_markup=keyboard
    )

@bot.message_handler(commands=['referrals'])
def show_referrals(message):
    """Handle /referrals command"""
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        bot.send_message(message.chat.id, "User not found. Please /start")
        return
    
    referrals = user_data.get('referrals', [])
    ref_code = message.from_user.id
    
    text = (
        f"👥 <b>Your Referrals</b>\n\n"
        f"🔗 <b>Referral Link:</b>\n"
        f"<code>https://t.me/{bot.get_me().username}?start={ref_code}</code>\n\n"
        f"📊 <b>Stats:</b>\n"
        f"👤 Total: {len(referrals)}\n"
        f"💵 Commission: 10% lifetime"
    )
    
    bot.send_message(message.chat.id, text, reply_markup=main_menu_keyboard())

@bot.message_handler(commands=['upgrade'])
def upgrade_plan(message):
    """Handle /upgrade command"""
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        bot.send_message(message.chat.id, "User not found. Please /start")
        return
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("💰 ₹100 - PRO (2x)", callback_data="upgrade_pro"),
        types.InlineKeyboardButton("📢 ₹500 - ADVERTISER", callback_data="upgrade_advertiser"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_upgrade")
    )
    
    text = (
        f"💎 <b>Upgrade Plan</b>\n\n"
        f"📦 Current: {user_data.get('plan', 'free').upper()}\n\n"
        f"<b>Plans:</b>\n\n"
        f"🥇 <b>PRO - ₹100</b>\n"
        f"• 2x rewards\n"
        f"• Priority support\n\n"
        f"🏢 <b>ADVERTISER - ₹500</b>\n"
        f"• All PRO features\n"
        f"• Submit tasks\n\n"
        f"💳 UPI: {UPI_ID}"
    )
    
    bot.send_message(message.chat.id, text, reply_markup=keyboard)

@bot.message_handler(commands=['withdraw'])
def withdraw(message):
    """Handle /withdraw command"""
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        bot.send_message(message.chat.id, "User not found. Please /start")
        return
    
    balance = user_data.get('balance', 0)
    min_withdraw = 100
    
    if balance < min_withdraw:
        bot.send_message(
            message.chat.id,
            f"❌ Insufficient Balance\n\n"
            f"Minimum: ₹{min_withdraw}\n"
            f"Yours: ₹{balance}",
            reply_markup=main_menu_keyboard()
        )
        return
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("💵 ₹100", callback_data="withdraw_100"),
        types.InlineKeyboardButton("💵 ₹500", callback_data="withdraw_500"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_withdraw")
    )
    
    text = (
        f"💸 <b>Withdraw</b>\n\n"
        f"Balance: ₹{balance}\n"
        f"Min: ₹{min_withdraw}\n\n"
        f"Select amount:"
    )
    
    bot.send_message(message.chat.id, text, reply_markup=keyboard)

@bot.message_handler(commands=['stats'])
def show_stats(message):
    """Handle /stats command"""
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        bot.send_message(message.chat.id, "User not found. Please /start")
        return
    
    text = (
        f"📊 <b>Statistics</b>\n\n"
        f"💰 Balance: ₹{user_data.get('balance', 0):.2f}\n"
        f"📈 Earned: ₹{user_data.get('total_earned', 0):.2f}\n"
        f"✅ Tasks: {user_data.get('tasks_completed', 0)}\n"
        f"👥 Referrals: {len(user_data.get('referrals', []))}\n"
        f"📦 Plan: {user_data.get('plan', 'free').upper()}\n"
        f"📅 Joined: {user_data.get('joined_date', 'N/A')[:10]}\n\n"
        f"🎯 <b>Verification:</b>\n"
        f"{'✅' if user_data.get('verified_youtube') else '❌'} YouTube\n"
        f"{'✅' if user_data.get('verified_instagram') else '❌'} Instagram"
    )
    
    bot.send_message(message.chat.id, text, reply_markup=main_menu_keyboard())

@bot.message_handler(commands=['support'])
def support_command(message):
    """Handle /support command"""
    msg = bot.send_message(
        message.chat.id,
        "🎧 <b>AI Support</b>\n\nAsk your question:",
        reply_markup=types.ForceReply()
    )
    bot.register_next_step_handler(msg, process_support_query)

async def process_support_query(message):
    """Process support query"""
    if message.text is None:
        bot.send_message(message.chat.id, "❌ Invalid input")
        return
    
    bot.send_chat_action(message.chat.id, 'typing')
    
    user_data = get_user_data(message.from_user.id)
    
    system_msg = {
        "role": "system",
        "content": "You are support for UltimateMediaSearchBot. Be helpful and friendly."
    }
    
    user_msg = {
        "role": "user",
        "content": f"User: {message.from_user.first_name}\nPlan: {user_data.get('plan', 'free') if user_data else 'unknown'}\nQ: {message.text}"
    }
    
    response = await query_deepseek([system_msg, user_msg])
    
    bot.send_message(
        message.chat.id,
        f"🎧 <b>Support:</b>\n\n{response}",
        reply_markup=main_menu_keyboard()
    )

# ==================== CALLBACK HANDLERS ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith('task_'))
def handle_task_callback(call):
    """Handle task selection"""
    task_id = call.data.replace('task_', '')
    user_id = call.from_user.id
    
    user_data = get_user_data(user_id)
    if not user_data:
        bot.answer_callback_query(call.id, "Error: User not found", show_alert=True)
        return
    
    # Check verification
    if not user_data.get('verified_youtube') or not user_data.get('verified_instagram'):
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton("✅ Verify YouTube", callback_data="verify_youtube"),
            types.InlineKeyboardButton("✅ Verify Instagram", callback_data="verify_instagram")
        )
        
        bot.send_message(
            user_id,
            f"⚠️ <b>Verify First</b>\n\n"
            f"Follow:\n"
            f"1️⃣ {YOUTUBE_CHANNEL}\n"
            f"2️⃣ {INSTAGRAM_HANDLE}",
            reply_markup=keyboard
        )
        bot.answer_callback_query(call.id, "Verify accounts first")
        return
    
    # Get task
    if not firebase_db:
        bot.answer_callback_query(call.id, "Database error", show_alert=True)
        return
    
    task_ref = firebase_db.child('tasks').child(task_id)
    task_data = task_ref.get()
    
    if not task_data:
        bot.answer_callback_query(call.id, "Task not found", show_alert=True)
        return
    
    # Check if completed
    completed = user_data.get('completed_tasks', [])
    if task_id in completed:
        bot.answer_callback_query(call.id, "Already completed!", show_alert=True)
        return
    
    # Show task
    reward = task_data.get('reward', 10)
    if user_data.get('plan') == 'pro':
        reward *= 2
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("🔗 Open Link", url=task_data.get('link', '#')),
        types.InlineKeyboardButton("✅ Completed", callback_data=f"complete_{task_id}")
    )
    
    bot.send_message(
        user_id,
        f"📋 <b>{task_data.get('title')}</b>\n\n"
        f"{task_data.get('description', '')}\n\n"
        f"💰 Reward: ₹{reward}",
        reply_markup=keyboard
    )
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('complete_'))
def handle_complete_task(call):
    """Handle task completion"""
    task_id = call.data.replace('complete_', '')
    user_id = call.from_user.id
    
    if not firebase_db:
        bot.answer_callback_query(call.id, "Database error", show_alert=True)
        return
    
    task_ref = firebase_db.child('tasks').child(task_id)
    task_data = task_ref.get()
    
    if not task_data:
        bot.answer_callback_query(call.id, "Task not found", show_alert=True)
        return
    
    user_data = get_user_data(user_id)
    reward = task_data.get('reward', 10)
    
    if user_data.get('plan') == 'pro':
        reward *= 2
    
    if add_balance(user_id, task_data.get('reward', 10), task_id):
        # Mark completed
        user_ref = firebase_db.child('users').child(str(user_id))
        completed = user_data.get('completed_tasks', [])
        completed.append(task_id)
        user_ref.update({'completed_tasks': completed})
        
        bot.answer_callback_query(call.id, f"✅ ₹{reward} added!", show_alert=False)
        
        bot.send_message(
            user_id,
            f"✅ <b>Completed!</b>\n\n"
            f"₹{reward} added to balance.",
            reply_markup=main_menu_keyboard()
        )
    else:
        bot.answer_callback_query(call.id, "Error. Try again", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith('verify_'))
def handle_verification(call):
    """Handle verification"""
    user_id = call.from_user.id
    platform = call.data.replace('verify_', '')
    
    if platform == 'youtube':
        update_user_data(user_id, {'verified_youtube': True})
        bot.answer_callback_query(call.id, "✅ YouTube verified!", show_alert=True)
    elif platform == 'instagram':
        update_user_data(user_id, {'verified_instagram': True})
        bot.answer_callback_query(call.id, "✅ Instagram verified!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith('upgrade_'))
def handle_upgrade(call):
    """Handle upgrade"""
    plan_type = call.data.replace('upgrade_', '')
    user_id = call.from_user.id
    
    amount = 100 if plan_type == 'pro' else 500
    plan_name = "PRO" if plan_type == 'pro' else "ADVERTISER"
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("✅ I Paid", callback_data=f"paid_{plan_type}"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_upgrade")
    )
    
    bot.send_message(
        user_id,
        f"💎 <b>Upgrade to {plan_name}</b>\n\n"
        f"💰 Amount: ₹{amount}\n\n"
        f"📲 Send to:\n<code>{UPI_ID}</code>\n\n"
        f"Then click 'I Paid'",
        reply_markup=keyboard
    )
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('paid_'))
def handle_payment_confirmation(call):
    """Handle payment confirmation"""
    plan_type = call.data.replace('paid_', '')
    user_id = call.from_user.id
    
    bot.send_message(
        user_id,
        "✅ <b>Payment Submitted!</b>\n\n"
        "Will be verified in 24 hours.",
        reply_markup=main_menu_keyboard()
    )
    
    bot.answer_callback_query(call.id, "Submitted for verification")

@bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw_'))
def handle_withdraw(call):
    """Handle withdrawal"""
    amount = int(call.data.replace('withdraw_', ''))
    user_id = call.from_user.id
    
    user_data = get_user_data(user_id)
    if not user_data:
        bot.answer_callback_query(call.id, "Error", show_alert=True)
        return
    
    if user_data.get('balance', 0) < amount:
        bot.answer_callback_query(call.id, "Insufficient balance", show_alert=True)
        return
    
    # Create withdrawal request
    if firebase_db:
        withdrawal_data = {
            'user_id': user_id,
            'amount': amount,
            'status': 'pending',
            'requested_at': datetime.now().isoformat()
        }
        firebase_db.child('withdrawals').push().set(withdrawal_data)
    
    bot.send_message(
        user_id,
        f"💸 <b>Withdrawal Request</b>\n\n"
        f"Amount: ₹{amount}\n"
        f"Status: Pending\n"
        f"Will process in 24-48h",
        reply_markup=main_menu_keyboard()
    )
    
    bot.answer_callback_query(call.id, "Request submitted")

@bot.callback_query_handler(func=lambda call: call.data.startswith('menu_'))
def handle_menu_callbacks(call):
    """Handle menu buttons"""
    action = call.data.replace('menu_', '')
    
    if action == 'balance':
        check_balance(call.message)
    elif action == 'tasks':
        show_tasks(call.message)
    elif action == 'referrals':
        show_referrals(call.message)
    elif action == 'upgrade':
        upgrade_plan(call.message)
    elif action == 'withdraw':
        withdraw(call.message)
    elif action == 'stats':
        show_stats(call.message)
    elif action == 'support':
        support_command(call.message)
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data in ['cancel_upgrade', 'cancel_withdraw'])
def handle_cancel(call):
    """Handle cancel"""
    bot.edit_message_text(
        "❌ Cancelled",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=main_menu_keyboard()
    )
    bot.answer_callback_query(call.id, "Cancelled")

# ==================== FLASK WEBHOOK ====================

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle webhook"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return '', 403

@app.route('/set-webhook', methods=['GET'])
def set_webhook():
    """Set webhook"""
    webhook_url = os.getenv('WEBHOOK_URL')
    
    try:
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        return jsonify({'status': 'success', 'message': 'Webhook set'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/', methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({'status': 'ok', 'message': 'Bot running'})

# ==================== MAIN ====================

if __name__ == '__main__':
    logger.info("Starting Flask server...")
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
