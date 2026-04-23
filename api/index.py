import os
import json
import telebot
import time
from flask import Flask, request, render_template, jsonify
import firebase_admin
from firebase_admin import credentials, db
from openai import OpenAI

# Vercel path fixing (UNCHANGED)
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
app = Flask(__name__, template_folder=template_dir)

# --- CONFIGURATION (SAME KEYS) ---
BOT_TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
FB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"
DEEPSEEK_KEY = "sk-783d645ce9e84eb8b954786a016561ea"
WELCOME_IMAGE = "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg"
ADMIN_SECRET_KEY = "SUPER_SECRET_ADMIN_123"
TERMS_LINK = "https://ultimatemediasearchbot.com/terms"  # ← Optional addition

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
ai_client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

# --- FIREBASE INIT (UNCHANGED) ---
if not firebase_admin._apps:
    fb_config = os.getenv("FIREBASE_SERVICE_ACCOUNT")
    if fb_config:
        try:
            cred = credentials.Certificate(json.loads(fb_config))
            firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})
        except Exception as e:
            print(f"Firebase Init Error: {e}")

# --- WEB ROUTES (UNCHANGED) ---
@app.route('/')
def home():
    return "Bot & Dashboard Server is Live!"

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/admin')
def admin_panel():
    users_ref = db.reference('users').get() or {}
    pending_ref = db.reference('submissions').order_by_child('status').equal_to('pending').get() or {}
    pending_list = [{"id": k, **v} for k, v in pending_ref.items()]
    stats = {"total_users": len(users_ref), "pending_reviews": len(pending_list)}
    return render_template('admin.html', stats=stats, pending=pending_list, admin_key=ADMIN_SECRET_KEY)

# --- ADMIN API (UNCHANGED) ---
@app.route('/api/admin/review', methods=['POST'])
def review_submission():
    if request.headers.get('X-Admin-Key') != ADMIN_SECRET_KEY:
        return jsonify({"success": False}), 403
    data = request.json
    sid = data.get('submission_id')
    approved = data.get('approved')
    reason = data.get('reason')
    
    sub_ref = db.reference(f'submissions/{sid}')
    submission = sub_ref.get()
    if not submission:
        return jsonify({"success": False})
    
    u_id = submission.get('user_id')
    if approved:
        u_ref = db.reference(f'users/{u_id}')
        current_points = u_ref.child('points').get() or 0
        u_ref.update({"points": current_points + submission.get('points', 0)})
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
    msg = request.json.get('message')
    users = db.reference('users').get() or {}
    count = 0
    for uid in users:
        try:
            bot.send_message(uid, f"📢 *Admin:* {msg}", parse_mode="Markdown")
            count += 1
        except:
            continue
    return jsonify({"success": True, "data": {"sent": count}})

# --- BOT LOGIC: /start (UPDATED WELCOME MESSAGE ONLY) ---
@bot.message_handler(commands=['start'])
def start(message):
    u_id = str(message.from_user.id)
    u_ref = db.reference(f'users/{u_id}')
    
    # ← SAME JSON structure: points, plan, name
    user = u_ref.get() or {"points": 100, "plan": "Free", "name": message.from_user.first_name}
    if not u_ref.get():
        u_ref.set(user)
    
    # ← NEW Welcome Caption (As per your prompt)
    caption = f"""✨ *Welcome to UltimateMediaSearchBot!* ✨

🇮🇳 *India's #1 Destination for Earning & Social Media Growth*

Namaste! 🙏 Aapne sahi jagah kadam rakha hai. Chahe aap extra income kamana chahte ho ya apne brand ki reach badhana, hum aapke saath hain.

💰 *EARNING DHAMAKA* (Subscription: ₹100)
Ab apne mobile ka sahi istemal karein aur rozana kamayein!

✅ VIP Tasks: High-paying social media tasks unlock karein
✅ Fast Payout: Apni mehnat ki kamayi turant withdraw karein
✅ Refer & Earn: Doston ko join karayein aur lifetime commission payein

📌 *Start earning by completing these tasks:*
1️⃣ YouTube: @USSoccerPulse
2️⃣ Instagram: @digital_rockstar_m
3️⃣ Facebook: Official Profile

📢 *PROMOTION HUB* (Plan: ₹500)
Kya aap apna YouTube, Instagram ya Facebook viral karna chahte hain?

🚀 Real Traffic: Koi bot nahi, sirf asli users
📈 Instant Reach: Apne link par dheron likes aur followers payein
🔗 Join our Network: UltimateMediaSearch Community

🔥 *AAJ KA MOTIVATION*
"Zamaana badal raha hai, ab mehnat ke saath-saath smart work karne ka time hai. Aaj ka ₹100 ka chota sa investment aapki kal ki badi kamyabi ban sakta hai. Der mat kijiye!"

👇 *Neeche diye gaye buttons par click karke shuru karein!*

⚠️ _Earning aapke kaam aur tasks par depend karti hai_
📄 Terms: {TERMS_LINK}"""

    # ← Buttons (compatible callback_data)
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", url=f"https://{request.host}/dashboard"))
    markup.add(telebot.types.InlineKeyboardButton("💰 Earn Now", callback_data="earn_tasks"))
    markup.add(telebot.types.InlineKeyboardButton("📢 Promote", callback_data="promote_plan"))
    markup.add(telebot.types.InlineKeyboardButton("✅ Verify", callback_data="verify_tasks"))
    markup.add(telebot.types.InlineKeyboardButton("📄 T&C", url=TERMS_LINK))
    
    bot.send_photo(
        message.chat.id, 
        WELCOME_IMAGE, 
        caption=caption, 
        parse_mode="Markdown", 
        reply_markup=markup,
        disable_web_page_preview=True
    )

# ← Callback handlers (optional, non-breaking)
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "earn_tasks":
        bot.answer_callback_query(call.id, "📌 Open dashboard to start earning!")
    elif call.data == "promote_plan":
        bot.answer_callback_query(call.id, "📢 Promotion features in dashboard!")
    elif call.data == "verify_tasks":
        bot.answer_callback_query(call.id, "✅ Upload screenshot in dashboard")

# ← Webhook route (UNCHANGED)
@app.route('/api/index', methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "OK", 200

# ← Keep app reference (UNCHANGED)
app = app
