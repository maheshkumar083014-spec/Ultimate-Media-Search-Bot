import os
import json
import telebot
import time
import logging
from flask import Flask, request, render_template, jsonify
import firebase_admin
from firebase_admin import credentials, db
from openai import OpenAI

# 🔧 Enable logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Vercel path fixing
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
app = Flask(__name__, template_folder=template_dir)

# --- CONFIGURATION ---
BOT_TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"  # ⚠️ Revoke this token first!
FB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"
DEEPSEEK_KEY = "sk-783d645ce9e84eb8b954786a016561ea"
WELCOME_IMAGE = "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg"
ADMIN_SECRET_KEY = "SUPER_SECRET_ADMIN_123"
TERMS_LINK = "https://ultimatemediasearchbot.com/terms"

bot = telebot.TeleBot(BOT_TOKEN, threaded=False, skip_pending=True)
ai_client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

# --- FIREBASE INIT (With Error Logging) ---
if not firebase_admin._apps:
    fb_config = os.getenv("FIREBASE_SERVICE_ACCOUNT")
    logger.info(f"Firebase config from env: {'Found' if fb_config else 'NOT FOUND'}")
    if fb_config:
        try:
            cred = credentials.Certificate(json.loads(fb_config))
            firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})
            logger.info("✅ Firebase initialized successfully")
        except Exception as e:
            logger.error(f"❌ Firebase Init Error: {str(e)}")
            print(f"Firebase Init Error: {e}")
    else:
        logger.warning("⚠️ FIREBASE_SERVICE_ACCOUNT env var not set!")

# --- DEBUG ROUTE (Check if server is alive) ---
@app.route('/debug')
def debug():
    return jsonify({
        "status": "alive",
        "host": request.host,
        "url": request.url,
        "firebase_init": bool(firebase_admin._apps),
        "bot_token_set": bool(BOT_TOKEN),
        "timestamp": time.time()
    })

# --- WEB ROUTES ---
@app.route('/')
def home():
    logger.info("Root endpoint hit")
    return "Bot & Dashboard Server is Live!"

@app.route('/dashboard')
def dashboard():
    logger.info("Dashboard endpoint hit")
    return render_template('dashboard.html')

@app.route('/admin')
def admin_panel():
    logger.info("Admin endpoint hit")
    users_ref = db.reference('users').get() or {}
    pending_ref = db.reference('submissions').order_by_child('status').equal_to('pending').get() or {}
    pending_list = [{"id": k, **v} for k, v in pending_ref.items()]
    stats = {"total_users": len(users_ref), "pending_reviews": len(pending_list)}
    return render_template('admin.html', stats=stats, pending=pending_list, admin_key=ADMIN_SECRET_KEY)

# --- ADMIN API ---
@app.route('/api/admin/review', methods=['POST'])
def review_submission():
    logger.info(f"Review API hit: {request.headers.get('X-Admin-Key')}")
    if request.headers.get('X-Admin-Key') != ADMIN_SECRET_KEY:
        logger.warning("❌ Admin auth failed")
        return jsonify({"success": False}), 403
    
    data = request.json
    sid = data.get('submission_id')
    approved = data.get('approved')
    reason = data.get('reason')
    
    logger.info(f"Processing submission: {sid}, approved: {approved}")
    
    sub_ref = db.reference(f'submissions/{sid}')
    submission = sub_ref.get()
    if not submission:
        logger.error(f"Submission not found: {sid}")
        return jsonify({"success": False})
    
    u_id = submission.get('user_id')
    if approved:
        u_ref = db.reference(f'users/{u_id}')
        current_points = u_ref.child('points').get() or 0
        u_ref.update({"points": current_points + submission.get('points', 0)})
        try:
            bot.send_message(u_id, "✅ *Task Approved!* Points added.", parse_mode="Markdown")
            logger.info(f"Sent approval message to {u_id}")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
    else:
        try:
            bot.send_message(u_id, f"❌ *Rejected:* {reason}", parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to send rejection: {e}")
    
    sub_ref.update({"status": "approved" if approved else "rejected"})
    logger.info(f"Submission {sid} updated")
    return jsonify({"success": True})

@app.route('/api/admin/broadcast', methods=['POST'])
def broadcast():
    logger.info("Broadcast API hit")
    if request.headers.get('X-Admin-Key') != ADMIN_SECRET_KEY:
        return jsonify({"success": False}), 403
    
    msg = request.json.get('message')
    users = db.reference('users').get() or {}
    count = 0
    for uid in users:
        try:
            bot.send_message(uid, f"📢 *Admin:* {msg}", parse_mode="Markdown")
            count += 1
        except Exception as e:
            logger.error(f"Failed to send to {uid}: {e}")
            continue
    logger.info(f"Broadcast sent to {count} users")
    return jsonify({"success": True, "data": {"sent": count}})

# --- BOT LOGIC: /start (With Debug Logging) ---
@bot.message_handler(commands=['start'])
def start(message):
    logger.info(f"🚀 /start command received from user: {message.from_user.id}")
    
    try:
        u_id = str(message.from_user.id)
        u_ref = db.reference(f'users/{u_id}')
        
        # Fetch or create user
        user = u_ref.get()
        logger.info(f"User data from Firebase: {user}")
        
        if not user:
            user = {"points": 100, "plan": "Free", "name": message.from_user.first_name}
            u_ref.set(user)
            logger.info(f"Created new user: {u_id}")
        
        caption = f"""✨ *Welcome to UltimateMediaSearchBot!* ✨

🇮🇳 *India's #1 Destination for Earning & Social Media Growth*

Namaste! 🙏 Aapne sahi jagah kadam rakha hai.

💰 *EARNING DHAMAKA* (Subscription: ₹100)
✅ VIP Tasks | ✅ Fast Payout | ✅ Refer & Earn

📌 *Tasks:*
1️⃣ YouTube: @USSoccerPulse
2️⃣ Instagram: @digital_rockstar_m
3️⃣ Facebook: Official Profile

⚠️ _Earning aapke kaam aur tasks par depend karti hai_
📄 Terms: {TERMS_LINK}"""

        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        dashboard_url = f"https://{request.host}/dashboard" if request.host else "https://your-project.vercel.app/dashboard"
        markup.add(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", url=dashboard_url))
        markup.add(telebot.types.InlineKeyboardButton("💰 Earn Now", callback_data="earn_tasks"))
        markup.add(telebot.types.InlineKeyboardButton("📄 T&C", url=TERMS_LINK))
        
        logger.info(f"Sending welcome photo to {u_id}")
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
        logger.error(f"❌ Error in /start handler: {str(e)}", exc_info=True)
        # Fallback message
        try:
            bot.send_message(message.chat.id, "⚠️ Bot is initializing. Please try again in 10 seconds.")
        except:
            pass

# ← Callback handlers (non-breaking)
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    logger.info(f"Callback received: {call.data} from {call.from_user.id}")
    bot.answer_callback_query(call.id, "Feature coming soon!")

# ← Webhook route (CRITICAL - Must return "OK", 200)
@app.route('/api/index', methods=['POST'])
def webhook():
    logger.info(f"🔗 Webhook hit! Headers: {request.headers.get('Content-Type')}")
    
    try:
        update_data = request.get_data().decode('utf-8')
        logger.debug(f"Update payload: {update_data[:200]}...")  # Log first 200 chars
        
        update = telebot.types.Update.de_json(update_data)
        bot.process_new_updates([update])
        
        logger.info("✅ Update processed successfully")
        return "OK", 200
        
    except Exception as e:
        logger.error(f"❌ Webhook processing error: {str(e)}", exc_info=True)
        # Still return 200 to prevent Telegram retries
        return "OK", 200

# ← Optional: Set webhook on startup (for testing)
@app.route('/set-webhook', methods=['GET'])
def set_webhook():
    webhook_url = f"https://{request.host}/api/index"
    logger.info(f"Setting webhook to: {webhook_url}")
    bot.remove_webhook()
    bot.set_webhook(webhook_url)
    return f"Webhook set to: {webhook_url}"

# ← Keep Vercel compatible
app = app

# ← For local testing only (comment out on Vercel)
if __name__ == '__main__':
    logger.info("🚀 Starting server locally...")
    app.run(host='0.0.0.0', port=5000, debug=True)
