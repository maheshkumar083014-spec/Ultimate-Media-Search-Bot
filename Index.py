import os
import json
import telebot
import time
import logging
from flask import Flask, request, render_template, jsonify
import firebase_admin
from firebase_admin import credentials, db
from openai import OpenAI

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Vercel path fixing
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
app = Flask(__name__, template_folder=template_dir)

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
FB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY", "sk-783d645ce9e84eb8b954786a016561ea")
WELCOME_IMAGE = "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg"
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "SUPER_SECRET_ADMIN_123")
TERMS_LINK = "https://ultimatemediasearchbot.com/terms"

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not set! Please add it in Vercel environment variables")
    raise ValueError("BOT_TOKEN is required")

bot = telebot.TeleBot(BOT_TOKEN, threaded=False, skip_pending=True)
ai_client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

# --- FIREBASE INIT ---
if not firebase_admin._apps:
    fb_config = os.getenv("FIREBASE_SERVICE_ACCOUNT")
    if fb_config:
        try:
            cred = credentials.Certificate(json.loads(fb_config))
            firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})
            logger.info("✅ Firebase initialized successfully")
        except Exception as e:
            logger.error(f"❌ Firebase Init Error: {str(e)}")
    else:
        logger.warning("⚠️ FIREBASE_SERVICE_ACCOUNT not set - using limited mode")

# --- HEALTH CHECK ---
@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "firebase_init": bool(firebase_admin._apps),
        "bot_token_set": bool(BOT_TOKEN),
        "timestamp": time.time()
    }), 200

# --- WEB ROUTES ---
@app.route('/')
def home():
    return "Bot & Dashboard Server is Live! ✅"

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/admin')
def admin_panel():
    try:
        users_ref = db.reference('users').get() or {}
        pending_ref = db.reference('submissions').order_by_child('status').equal_to('pending').get() or {}
        pending_list = [{"id": k, **v} for k, v in pending_ref.items()]
        stats = {"total_users": len(users_ref), "pending_reviews": len(pending_list)}
        return render_template('admin.html', stats=stats, pending=pending_list, admin_key=ADMIN_SECRET_KEY)
    except:
        return render_template('admin.html', stats={"total_users": 0, "pending_reviews": 0}, pending=[], admin_key=ADMIN_SECRET_KEY)

# --- ADMIN API ---
@app.route('/api/admin/review', methods=['POST'])
def review_submission():
    if request.headers.get('X-Admin-Key') != ADMIN_SECRET_KEY:
        return jsonify({"success": False}), 403
    
    data = request.json
    sid = data.get('submission_id')
    approved = data.get('approved')
    reason = data.get('reason', 'Not approved')
    
    sub_ref = db.reference(f'submissions/{sid}')
    submission = sub_ref.get()
    if not submission:
        return jsonify({"success": False, "error": "Submission not found"})
    
    u_id = submission.get('user_id')
    if approved:
        u_ref = db.reference(f'users/{u_id}')
        current_points = u_ref.child('points').get() or 0
        u_ref.update({"points": current_points + submission.get('points', 100)})
        try:
            bot.send_message(u_id, "✅ *Task Approved!* Points added.", parse_mode="Markdown")
        except:
            pass
    else:
        try:
            bot.send_message(u_id, f"❌ *Rejected:* {reason}", parse_mode="Markdown")
        except:
            pass
    
    sub_ref.update({"status": "approved" if approved else "rejected"})
    return jsonify({"success": True})

@app.route('/api/admin/broadcast', methods=['POST'])
def broadcast():
    if request.headers.get('X-Admin-Key') != ADMIN_SECRET_KEY:
        return jsonify({"success": False}), 403
    
    msg = request.json.get('message', '')
    users = db.reference('users').get() or {}
    count = 0
    for uid in users:
        try:
            bot.send_message(uid, f"📢 *Admin:* {msg}", parse_mode="Markdown")
            count += 1
        except:
            continue
    return jsonify({"success": True, "data": {"sent": count}})

# --- BOT HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    try:
        u_id = str(message.from_user.id)
        u_ref = db.reference(f'users/{u_id}')
        
        user = u_ref.get()
        if not user:
            user = {
                "points": 100,
                "plan": "Free",
                "name": message.from_user.first_name,
                "joined": int(time.time())
            }
            u_ref.set(user)
        
        caption = f"""✨ *Welcome to UltimateMediaSearchBot!* ✨

🇮🇳 *India's #1 Destination for Earning & Social Media Growth*

Namaste! 🙏 Aapne sahi jagah kadam rakha hai.

💰 *EARNING DHAMAKA* (Subscription: ₹100)
✅ VIP Tasks: High-paying social media tasks
✅ Fast Payout: Instant withdrawal
✅ Refer & Earn: Lifetime commission

📌 *Start earning by completing these tasks:*
1️⃣ YouTube: @USSoccerPulse
2️⃣ Instagram: @digital_rockstar_m
3️⃣ Facebook: Official Profile

🔥 *AAJ KA MOTIVATION*
"Zamaana badal raha hai, ab mehnat ke saath-saath smart work karne ka time hai."

👇 *Neeche diye gaye buttons par click karke shuru karein!*

⚠️ _Earning aapke kaam aur tasks par depend karti hai_"""

        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        dashboard_url = f"https://{request.host}/dashboard" if request.host else "#"
        markup.add(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", url=dashboard_url))
        markup.add(telebot.types.InlineKeyboardButton("💰 Earn Now", callback_data="earn_tasks"))
        markup.add(telebot.types.InlineKeyboardButton("📢 Promote", callback_data="promote_plan"))
        markup.add(telebot.types.InlineKeyboardButton("✅ Verify", callback_data="verify_tasks"))
        
        bot.send_photo(
            message.chat.id,
            WELCOME_IMAGE,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=markup,
            disable_web_page_preview=True
        )
        logger.info(f"✅ Welcome message sent to {u_id}")
        
    except Exception as e:
        logger.error(f"❌ Error in /start: {str(e)}")
        bot.send_message(message.chat.id, "⚠️ Bot is initializing. Please try again in 10 seconds.")

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """📚 *Help & Support*

Available Commands:
/start - Start the bot
/help - Show this help message
/earn - Check earning tasks
/withdraw - Withdraw your points

Need help? Contact: @YourAdminUsername

⚠️ _Earning depends on your work_"""
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        if call.data == "earn_tasks":
            bot.answer_callback_query(call.id, "📌 Open dashboard to start earning tasks!", show_alert=True)
        elif call.data == "promote_plan":
            bot.answer_callback_query(call.id, "📢 Promotion features coming soon!", show_alert=True)
        elif call.data == "verify_tasks":
            bot.answer_callback_query(call.id, "✅ Upload screenshot in dashboard for verification", show_alert=True)
    except Exception as e:
        logger.error(f"Callback error: {str(e)}")

# --- WEBHOOK ROUTE (CRITICAL) ---
@app.route('/api/index', methods=['POST'])
def webhook():
    try:
        # Get JSON data from request
        if not request.is_json:
            logger.warning("⚠️ Request is not JSON")
            return "OK", 200
        
        update_data = request.get_json()
        if not update_data:
            logger.warning("⚠️ Empty update data")
            return "OK", 200
        
        # Process update
        update = telebot.types.Update.de_json(json.dumps(update_data))
        bot.process_new_updates([update])
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {str(e)}", exc_info=True)
        # Always return 200 to prevent Telegram retries
        return "OK", 200

# Set webhook endpoint (for testing)
@app.route('/set-webhook', methods=['GET'])
def set_webhook():
    if not request.host:
        return "Error: Cannot determine host", 400
    
    webhook_url = f"https://{request.host}/api/index"
    bot.remove_webhook()
    bot.set_webhook(webhook_url)
    return f"✅ Webhook set to: {webhook_url}"

# Keep Vercel compatible
app = app

# For local testing only
if __name__ == '__main__':
    logger.info("🚀 Starting server locally on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)
