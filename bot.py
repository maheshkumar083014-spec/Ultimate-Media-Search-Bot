"""
🤖 Telegram Bot - Main Entry Point
Handles all Telegram interactions, commands, and inline keyboards.
"""
import telebot
from telebot import types
from datetime import datetime
import logging
from config import current_config
from database import get_db
from utils.helpers import generate_web_app_url, log_action
from utils.security import generate_device_fingerprint

logger = logging.getLogger(__name__)

# Initialize bot
bot = telebot.TeleBot(
    current_config.BOT_TOKEN, 
    parse_mode='HTML',
    threaded=True,
    skip_pending=True
)

# Banner image for /start
BANNER_IMAGE = "https://i.ibb.co/9kmTw4Gh/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg"


@bot.message_handler(commands=['start'])
def handle_start(message: types.Message):
    """Handle /start command - Welcome user with premium card"""
    try:
        user = message.from_user
        telegram_id = user.id
        username = user.username or user.first_name or 'User'
        
        # Get referral code from deep link
        referral_code = None
        if message.text and '/start ' in message.text:
            parts = message.text.split()
            if len(parts) > 1:
                referral_code = parts[1].strip()
        
        # Initialize user in database
        db = get_db()
        existing_user = db.get_user(telegram_id)
        
        if not existing_user:
            user_data = db.create_user(telegram_id, username, user.first_name, referral_code)
            welcome_text = f"""
🌟 <b>Welcome to Ultimate Media Search!</b>

👋 Hello <b>{user.first_name}</b>!

💬 <i>"Your smartphone is now your ATM. Stop scrolling for free—start earning for your time!"</i> 💰✨

🎁 <b>How to Earn:</b>
├ 📺 Watch Ads → +{current_config.AD_POINTS} Points
├ 📱 Social Tasks → +{current_config.SOCIAL_POINTS} Points
├ 👥 Refer Friends → +{current_config.REFERRAL_BONUS} Points
└ 💰 <b>{current_config.POINTS_PER_DOLLAR} Points = $1.00 USD</b>

🔐 All submissions are reviewed for fairness.

👇 Tap below to open your Premium Dashboard!
            """
            log_action('user_registered', telegram_id, {'referral': referral_code})
        else:
            # Update existing user
            db.update_user(telegram_id, {
                'username': username,
                'first_name': user.first_name
            })
            welcome_text = f"""
👋 Welcome back, <b>{user.first_name}</b>!

💰 Your Balance: <b>{existing_user.get('points', 0):,} Points</b> (${existing_user.get('points', 0) / current_config.POINTS_PER_DOLLAR:.2f})

🚀 Continue earning rewards!
            """
            log_action('user_returned', telegram_id)
        
        # Create inline keyboard
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        dashboard_url = generate_web_app_url(telegram_id, username)
        
        markup.add(
            types.InlineKeyboardButton(
                "🚀 Open Premium Dashboard", 
                web_app=types.WebAppInfo(url=dashboard_url)
            ),
            types.InlineKeyboardButton(
                "📋 View Tasks", 
                callback_data=f"view_tasks:{telegram_id}"
            ),
            types.InlineKeyboardButton(
                "👥 Invite Friends", 
                callback_data=f"invite:{telegram_id}"
            ),
            types.InlineKeyboardButton(
                "💰 Withdraw", 
                callback_data=f"withdraw:{telegram_id}"
            )
        )
        
        # Send welcome photo with caption
        try:
            bot.send_photo(
                message.chat.id,
                photo=BANNER_IMAGE,
                caption=welcome_text,
                reply_markup=markup
            )
        except Exception as e:
            logger.warning(f"Failed to send photo: {e}")
            # Fallback to text
            bot.send_message(
                message.chat.id,
                welcome_text + f"\n\n🖼️ <a href='{BANNER_IMAGE}'>View Banner</a>",
                reply_markup=markup
            )
        
    except Exception as e:
        logger.error(f"Start command error: {e}")
        bot.send_message(
            message.chat.id, 
            "⚠️ Something went wrong. Please try /start again.",
            parse_mode='HTML'
        )


@bot.message_handler(commands=['menu', 'tasks', 'earn'])
def handle_tasks_menu(message: types.Message):
    """Show available earning tasks"""
    telegram_id = message.from_user.id
    db = get_db()
    user = db.get_user(telegram_id)
    
    if not user:
        bot.send_message(message.chat.id, "Please start the bot first with /start")
        return
    
    tasks = [
        ("📺", "Watch Advertisement", f"+{current_config.AD_POINTS} pts", "ad"),
        ("▶️", "YouTube Subscribe", f"+{current_config.SOCIAL_POINTS} pts", "youtube_subscribe"),
        ("❤️", "YouTube Like Video", f"+{current_config.SOCIAL_POINTS} pts", "youtube_like"),
        ("📘", "Facebook Follow", f"+{current_config.SOCIAL_POINTS} pts", "facebook_follow"),
        ("📷", "Instagram Follow", f"+{current_config.SOCIAL_POINTS} pts", "instagram_follow"),
    ]
    
    text = f"""
💎 <b>Available Tasks</b>

👤 <b>{user.get('first_name')}</b> | 💰 {user.get('points', 0):,} Points

📋 Complete tasks, upload screenshot, earn points!
All submissions require admin approval.
    """
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for icon, title, reward, task_id in tasks:
        markup.add(types.InlineKeyboardButton(
            f"{icon} {title} {reward}",
            callback_data=f"task:{task_id}:{telegram_id}"
        ))
    
    markup.add(types.InlineKeyboardButton(
        "🏠 Back to Dashboard",
        web_app=types.WebAppInfo(url=generate_web_app_url(telegram_id, user.get('username', '')))
    ))
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='HTML')


@bot.callback_query_handler(func=lambda call: call.data.startswith('task:'))
def handle_task_selection(call: types.CallbackQuery):
    """Handle task selection from inline keyboard"""
    try:
        parts = call.data.split(':')
        task_type = parts[1]
        telegram_id = int(parts[2])
        
        if call.from_user.id != telegram_id:
            bot.answer_callback_query(call.id, "⚠️ Unauthorized", show_alert=True)
            return
        
        from utils.verification import get_task_requirements
        req = get_task_requirements(task_type)
        
        text = f"""
{req['title']}

📝 <b>Instructions:</b>
{req['instruction']}

✅ <b>What we check:</b>
{chr(10).join(f"• {el}" for el in req['expected_elements'])}

{req['proof_text_hint'] and f"📝 <b>Optional:</b> {req['proof_text_hint']}"}

📸 After completing the task:
1. Take a clear screenshot
2. Upload via the Web App dashboard
3. Wait for admin approval (~24h)

⚠️ Fake submissions will result in account ban.
        """
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton(
            "📤 Upload Screenshot (Web App)",
            web_app=types.WebAppInfo(url=f"{current_config.WEBAPP_URL}/dashboard?task={task_type}&id={telegram_id}")
        ))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data=f"menu:{telegram_id}"))
        
        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup,
            parse_mode='HTML'
        )
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Task selection error: {e}")
        bot.answer_callback_query(call.id, "⚠️ Error loading task", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('invite:'))
def handle_invite_request(call: types.CallbackQuery):
    """Show referral link and invite instructions"""
    telegram_id = int(call.data.split(':')[1])
    
    if call.from_user.id != telegram_id:
        bot.answer_callback_query(call.id, "⚠️ Unauthorized", show_alert=True)
        return
    
    db = get_db()
    user = db.get_user(telegram_id)
    
    if not user:
        bot.answer_callback_query(call.id, "User not found", show_alert=True)
        return
    
    referral_link = f"https://t.me/{bot.get_me().username}?start={user['referral_code']}"
    
    text = f"""
👥 <b>Invite Friends & Earn!</b>

🎁 Earn <b>+{current_config.REFERRAL_BONUS} Points</b> for each friend who joins!

🔗 <b>Your Referral Link:</b>
<code>{referral_link}</code>

📋 <b>How it works:</b>
1. Share your link with friends
2. They click & start the bot
3. You get points automatically!

💡 Pro Tip: Share in groups & social media for maximum earnings!
    """
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📋 Copy Link", switch_inline_query=referral_link),
        types.InlineKeyboardButton("🏠 Dashboard", web_app=types.WebAppInfo(url=generate_web_app_url(telegram_id, user.get('username', ''))))
    )
    
    bot.edit_message_text(
        text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup,
        parse_mode='HTML'
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw:'))
def handle_withdraw_request(call: types.CallbackQuery):
    """Handle withdrawal request"""
    telegram_id = int(call.data.split(':')[1])
    
    if call.from_user.id != telegram_id:
        bot.answer_callback_query(call.id, "⚠️ Unauthorized", show_alert=True)
        return
    
    db = get_db()
    user = db.get_user(telegram_id)
    
    if not user:
        bot.answer_callback_query(call.id, "User not found", show_alert=True)
        return
    
    points = user.get('points', 0)
    min_withdraw = current_config.POINTS_PER_DOLLAR  # $1 minimum
    
    if points < min_withdraw:
        text = f"""
💰 <b>Withdrawal</b>

❌ Insufficient balance for withdrawal.

📊 Your Balance: <b>{points:,} Points</b> (${points / current_config.POINTS_PER_DOLLAR:.2f})
🎯 Minimum: <b>{min_withdraw:,} Points</b> ($1.00)

🚀 Keep completing tasks to reach withdrawal threshold!
        """
    else:
        usd_amount = points / current_config.POINTS_PER_DOLLAR
        text = f"""
💰 <b>Withdrawal Request</b>

✅ You have enough points to withdraw!

📊 Balance: <b>{points:,} Points</b> (${usd_amount:.2f})
💵 Withdrawal Amount: <b>${usd_amount:.2f}</b>

⚠️ Withdrawals are processed manually within 24-48 hours.
Payment methods: PayPal, Crypto, or Bank Transfer.

🔐 To request withdrawal:
1. Open Web App Dashboard
2. Go to Withdraw section
3. Select payment method & confirm
        """
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(
        "💳 Open Withdraw Dashboard",
        web_app=types.WebAppInfo(url=f"{current_config.WEBAPP_URL}/dashboard?section=withdraw&id={telegram_id}")
    ))
    markup.add(types.InlineKeyboardButton("🏠 Back", callback_data=f"menu:{telegram_id}"))
    
    bot.edit_message_text(
        text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup,
        parse_mode='HTML'
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('menu:'))
def handle_back_to_menu(call: types.CallbackQuery):
    """Return to main tasks menu"""
    # Re-trigger tasks menu
    fake_message = types.Message(
        message_id=call.message.message_id,
        from_user=call.from_user,
        chat=call.message.chat,
        date=int(datetime.now().timestamp()),
        text='/menu'
    )
    handle_tasks_menu(fake_message)
    bot.answer_callback_query(call.id)


# ─────────────────────────────────────────────────────────────────────────────
# 🛡️ Admin Commands (Restricted)
# ─────────────────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['admin'])
def handle_admin_panel(message: types.Message):
    """Admin-only: Show admin panel link"""
    if message.from_user.id not in current_config.ADMIN_USER_IDS:
        bot.send_message(message.chat.id, "🔐 Admin access required.")
        return
    
    admin_url = f"{current_config.WEBAPP_URL}/admin?key={current_config.ADMIN_SECRET_KEY}"
    
    text = f"""
🔧 <b>Admin Panel</b>

👤 Admin: {message.from_user.first_name}

🔗 <b>Access Admin Dashboard:</b>
{admin_url}

⚠️ Keep this link private!
    """
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔧 Open Admin Panel", url=admin_url))
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='HTML')


@bot.message_handler(commands=['broadcast'])
def handle_broadcast_command(message: types.Message):
    """Admin-only: Broadcast message to all users"""
    if message.from_user.id not in current_config.ADMIN_USER_IDS:
        return
    
    # Extract message text after /broadcast
    broadcast_text = message.text.replace('/broadcast', '').strip()
    if not broadcast_text:
        bot.reply_to(message, "Usage: /broadcast Your message here")
        return
    
    db = get_db()
    result = db.broadcast_message(message.from_user.id, broadcast_text)
    
    if result.get('success'):
        bot.reply_to(message, f"✅ Broadcast sent to {result['sent']} users!")
        log_action('broadcast_sent', message.from_user.id, {'count': result['sent'], 'message': broadcast_text[:100]})
    else:
        bot.reply_to(message, f"❌ Error: {result.get('error', 'Unknown')}")


# ─────────────────────────────────────────────────────────────────────────────
# 🚀 Bot Startup & Webhook
# ─────────────────────────────────────────────────────────────────────────────

def setup_bot():
    """Initialize bot with webhook for production"""
    try:
        # For Vercel/serverless, webhook is set externally
        # For local development, you can set it here:
        # bot.set_webhook(f"{current_config.APP_URL}/webhook")
        
        logger.info("✅ Bot initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Bot setup failed: {e}")
        return False


# For local testing only (Vercel uses webhook via app.py)
if __name__ == '__main__':
    from config import current_config
    if current_config.DEBUG:
        logger.info("🤖 Starting bot in polling mode (development)...")
        setup_bot()
        bot.infinity_polling()
