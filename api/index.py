import os
import json
import telebot
import time
from flask import Flask, request, render_template, jsonify
import firebase_admin
from firebase_admin import credentials, db
from openai import OpenAI

# Vercel path fixing
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
app = Flask(__name__, template_folder=template_dir)

# --- CONFIGURATION ---
BOT_TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
FB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"
DEEPSEEK_KEY = "sk-783d645ce9e84eb8b954786a016561ea"
WELCOME_IMAGE = "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg"
ADMIN_SECRET_KEY = "SUPER_SECRET_ADMIN_123"
TERMS_LINK = "https://ultimatemediasearchbot.com/terms"  # Add your terms link

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
ai_client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

# --- FIREBASE INIT ---
if not firebase_admin._apps:
    fb_config = os.getenv("FIREBASE_SERVICE_ACCOUNT")
    if fb_config:
        try:
            cred = credentials.Certificate(json.loads(fb_config))
            firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})
        except Exception as e:
            print(f"Firebase Init Error: {e}")

# --- WEB ROUTES ---
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

# --- ADMIN API ---
@app.route('/api/admin/review', methods=['POST'])
def review_submission():
    if request.headers.get('X-Admin-Key') != ADMIN_SECRET_KEY: 
        return jsonify({"success": False}), 403
    data = request.json
    sid, approved, reason = data.get('submission_id'), data.get('approved'), data.get('reason')
    sub_ref = db.reference(f'submissions/{sid}')
    submission = sub_ref.get()
    if not submission: 
        return jsonify({"success": False})
    u_id = submission.get('user_id')
    if approved:
        u_ref = db.reference(f'users/{u_id}')
        u_ref.update({"points": (u_ref.child('points').get() or 0) + submission.get('points', 0)})
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

# --- BOT LOGIC ---
@bot.message_handler(commands=['start'])
def start(message):
    u_id = str(message.from_user.id)
    u_ref = db.reference(f'users/{u_id}')
    user = u_ref.get() or {"points": 100, "plan": "Free", "name": message.from_user.first_name}
    if not u_ref.get(): 
        u_ref.set(user)
    
    # Welcome Message Caption
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

    # Create Inline Keyboard
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    
    # Main Action Buttons
    btn_dashboard = telebot.types.InlineKeyboardButton("🚀 Open Dashboard", url=f"https://{request.host}/dashboard")
    btn_earn = telebot.types.InlineKeyboardButton("💰 Earn Now", callback_data="earn_tasks")
    btn_promote = telebot.types.InlineKeyboardButton("📢 Promote", callback_data="promote_plan")
    btn_verify = telebot.types.InlineKeyboardButton("✅ Verify Tasks", callback_data="verify_tasks")
    
    # Secondary Buttons
    btn_refer = telebot.types.InlineKeyboardButton("👥 Refer & Earn", callback_data="refer_earn")
    btn_withdraw = telebot.types.InlineKeyboardButton("💵 Withdraw", callback_data="withdraw")
    btn_help = telebot.types.InlineKeyboardButton("❓ Help", callback_data="help")
    btn_terms = telebot.types.InlineKeyboardButton("📄 T&C", url=TERMS_LINK)
    
    # Add buttons to markup
    markup.add(btn_dashboard)
    markup.add(btn_earn, btn_promote)
    markup.add(btn_verify, btn_refer)
    markup.add(btn_withdraw, btn_help)
    markup.add(btn_terms)
    
    # Send welcome photo with caption
    bot.send_photo(
        message.chat.id, 
        WELCOME_IMAGE, 
        caption=caption, 
        parse_mode="Markdown", 
        reply_markup=markup,
        disable_web_page_preview=True
    )
    
    # Send user info
    user_info = f"""👤 *Your Profile*
Name: {user.get('name', 'User')}
💎 Plan: {user.get('plan', 'Free')}
💰 Balance: {user.get('points', 0)} Points
📊 Status: Active"""
    
    bot.send_message(message.chat.id, user_info, parse_mode="Markdown")

# --- CALLBACK HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    u_id = str(call.from_user.id)
    
    if call.data == "earn_tasks":
        msg = """💰 *EARNING TASKS*

Complete these tasks to earn points:

1️⃣ *YouTube Subscribe* - 10 points
   Channel: @USSoccerPulse
   
2️⃣ *Instagram Follow* - 10 points
   Handle: @digital_rockstar_m
   
3️⃣ *Facebook Like* - 10 points
   Page: Official Profile

📸 *After completing, upload screenshot for verification!*

💡 Note: Earning aapke kaam aur tasks par depend karti hai."""
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("📸 Upload Screenshot", callback_data="upload_screenshot"))
        markup.add(telebot.types.InlineKeyboardButton("🔙 Back", callback_data="back"))
        
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown", reply_markup=markup)
    
    elif call.data == "promote_plan":
        msg = """📢 *PROMOTION HUB* - ₹500 Plan

Apne social media ko viral karein!

🚀 *What you get:*
✅ Real Traffic (No bots)
✅ Instant Reach
✅ Likes, Followers, Views
✅ YouTube, Instagram, Facebook

📝 *How to submit:*
1. Share your social media link
2. Make payment of ₹500
3. Upload payment screenshot
4. Wait for admin approval

💡 Note: Results aapke content quality par depend karte hain."""
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("📝 Submit for Promotion", callback_data="submit_promotion"))
        markup.add(telebot.types.InlineKeyboardButton("🔙 Back", callback_data="back"))
        
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown", reply_markup=markup)
    
    elif call.data == "verify_tasks":
        msg = """✅ *TASK VERIFICATION*

Apne completed tasks verify karein:

📌 *Process:*
1. Task complete karein
2. Screenshot lein
3. Yahan upload karein
4. Admin verify karega
5. Points milenge!

⏱️ Verification time: 24-48 hours"""
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("📤 Upload Proof", callback_data="upload_proof"))
        markup.add(telebot.types.InlineKeyboardButton("🔙 Back", callback_data="back"))
        
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown", reply_markup=markup)
    
    elif call.data == "refer_earn":
        # Get user's referral link
        referral_link = f"https://t.me/UltimateMediaSearchBot?start={u_id}"
        msg = f"""👥 *REFER & EARN*

Doston ko invite karein aur kamayein!

💰 *Earnings:*
• ₹10 per referral (instant)
• 5% lifetime commission
• No limit on referrals!

🔗 *Your Referral Link:*
`{referral_link}`

📊 Share this link with friends and start earning!"""
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🔙 Back", callback_data="back"))
        
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown", reply_markup=markup)
    
    elif call.data == "withdraw":
        user_ref = db.reference(f'users/{u_id}')
        user_data = user_ref.get() or {}
        points = user_data.get('points', 0)
        
        msg = f"""💵 *WITHDRAWAL*

Current Balance: {points} Points

💰 *Withdrawal Options:*
• 100 Points = ₹1 (Minimum)
• 1000 Points = ₹10
• 10000 Points = ₹100

📝 *Process:*
1. Minimum 100 points required
2. Click "Request Withdrawal"
3. Enter UPI/Payment details
4. Get paid within 24-48 hours

⚠️ Note: Fake accounts will be banned."""
        
        markup = telebot.types.InlineKeyboardMarkup()
        if points >= 100:
            markup.add(telebot.types.InlineKeyboardButton("💸 Request Withdrawal", callback_data="request_withdraw"))
        markup.add(telebot.types.InlineKeyboardButton("🔙 Back", callback_data="back"))
        
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown", reply_markup=markup)
    
    elif call.data == "help":
        msg = """❓ *HELP & SUPPORT*

Hum aapki madad ke liye yahan hain!

📞 *Contact:*
• Admin: @YourAdminUsername
• Support Group: @YourSupportGroup

📚 *Quick Links:*
• How to Earn? - /earn
• Withdrawal - /withdraw
• Tasks - /tasks
• Promotion - /promote

⏰ Support Hours: 10 AM - 8 PM IST

💡 *Earning aapke kaam aur tasks par depend karti hai*"""
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🔙 Back", callback_data="back"))
        
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown", reply_markup=markup)
    
    elif call.data == "back":
        # Re-send welcome message
        start(call.message)
    
    elif call.data == "upload_screenshot" or call.data == "upload_proof":
        msg = """📸 *UPLOAD SCREENSHOT*

Apna screenshot yahan send karein. 
Bot automatically receive karega aur admin ko bhej dega verification ke liye.

⏱️ Aapko 24-48 hours mein response milega."""
        
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")
        # You can add logic here to handle photo uploads
    
    elif call.data == "submit_promotion":
        msg = """📝 *SUBMIT PROMOTION REQUEST*

Please provide:
1. Your social media link (YouTube/Instagram/Facebook)
2. Payment screenshot (₹500)
3. Target audience details

📤 Send these details in the next message."""
        
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")
    
    elif call.data == "request_withdraw":
        msg = """💸 *WITHDRAWAL REQUEST*

Please provide:
1. Amount (in ₹)
2. UPI ID / Bank Details
3. Confirmation message

📤 Send these details in the next message.

⚠️ Note: Earning aapke kaam aur tasks par depend karti hai"""
        
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")

# Handle photo/document uploads for verification
@bot.message_handler(content_types=['photo', 'document'])
def handle_uploads(message):
    u_id = str(message.from_user.id)
    
    # Save submission to Firebase
    submission_data = {
        "user_id": u_id,
        "timestamp": time.time(),
        "status": "pending",
        "type": "verification"
    }
    
    db.reference(f'submissions').push(submission_data)
    
    bot.send_message(
        message.chat.id, 
        "✅ Screenshot received! Admin will verify within 24-48 hours.\n\n⚠️ Earning aapke kaam aur tasks par depend karti hai",
        parse_mode="Markdown"
    )

# Webhook route
@app.route('/api/index', methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "OK", 200

# Set webhook on startup (optional)
@app.route('/set-webhook', methods=['GET'])
def set_webhook():
    webhook_url = f"https://{request.host}/api/index"
    bot.remove_webhook()
    bot.set_webhook(webhook_url)
    return f"Webhook set to: {webhook_url}"

app = app
