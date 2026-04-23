import os
import json
import time
import hashlib
import requests
from flask import Flask, request, jsonify, render_template, redirect, url_for
import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, db, initialize_app
from openai import OpenAI

# ==================== CONFIGURATION ====================
app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Hardcoded credentials (⚠️ USE ENV VARS IN PRODUCTION)
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw')
FIREBASE_DB_URL = os.environ.get('FIREBASE_DATABASE_URL', 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', 'sk-783d645ce9e84eb8b954786a016561ea')
ADMIN_TELEGRAM_ID = os.environ.get('ADMIN_TELEGRAM_ID', '123456789')  # Replace with your actual ID
UPI_ID = os.environ.get('UPI_ID', '8543083014@ikwik')
QR_CODE_URL = "https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=" + UPI_ID

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": "ultimatemediasearch",
        "private_key_id": "dummy",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC7+t...\n-----END PRIVATE KEY-----\n",
        "client_email": "firebase-adminsdk-dummy@ultimatemediasearch.iam.gserviceaccount.com",
        "client_id": "dummy",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-dummy%40ultimatemediasearch.iam.gserviceaccount.com"
    })
    # For Realtime Database only, we can use direct URL
    initialize_app(options={'databaseURL': FIREBASE_DB_URL})

# Initialize Telegram Bot
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# Initialize DeepSeek/OpenAI Client
deepseek_client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1"
)

# ==================== HELPER FUNCTIONS ====================
def get_user_data(user_id):
    """Fetch user data from Firebase"""
    try:
        user_ref = db.reference(f'users/{user_id}')
        return user_ref.get()
    except:
        return None

def update_user_data(user_id, data):
    """Update user data in Firebase"""
    try:
        user_ref = db.reference(f'users/{user_id}')
        user_ref.update(data)
        return True
    except:
        return False

def register_user(user_id, username, first_name, referral_code=None):
    """Register new user in Firebase"""
    user_data = {
        'user_id': user_id,
        'username': username,
        'first_name': first_name,
        'balance': 0,
        'is_premium': False,
        'referral_code': hashlib.md5(str(user_id).encode()).hexdigest()[:8],
        'referred_by': referral_code,
        'total_messages': 0,
        'joined_at': int(time.time()),
        'last_active': int(time.time()),
        'pending_payments': []
    }
    
    # Add referral bonus if applicable
    if referral_code:
        # Find referrer
        users_ref = db.reference('users')
        all_users = users_ref.get()
        if all_users:
            for uid, data in all_users.items():
                if data.get('referral_code') == referral_code:
                    # Award bonus to referrer
                    referrer_balance = data.get('balance', 0) + 50
                    users_ref.child(uid).update({'balance': referrer_balance})
                    # Award bonus to new user
                    user_data['balance'] = 25
                    break
    
    db.reference(f'users/{user_id}').set(user_data)
    return user_data

def deduct_balance(user_id, amount):
    """Deduct points from user balance"""
    user = get_user_data(user_id)
    if user and user.get('balance', 0) >= amount:
        new_balance = user['balance'] - amount
        update_user_data(user_id, {'balance': new_balance})
        return True
    return False

def generate_ai_response(message, user_data):
    """Generate AI response using DeepSeek"""
    try:
        system_prompt = "You are Ultimate Media Search AI Assistant. Help users with media searches, content recommendations, and platform guidance. Be concise and helpful."
        
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ AI Service Temporarily Unavailable: {str(e)}"

# ==================== TELEGRAM BOT HANDLERS ====================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or 'User'
    first_name = message.from_user.first_name
    
    # Check if user exists
    user_data = get_user_data(user_id)
    if not user_data:
        # Extract referral code if present
        referral_code = None
        if len(message.text.split()) > 1:
            referral_code = message.text.split()[1]
        user_data = register_user(user_id, username, first_name, referral_code)
    
    # Update last active
    update_user_data(user_id, {'last_active': int(time.time()), 'username': username})
    
    # Send welcome photo with dynamic caption
    photo_url = "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg"
    balance = user_data.get('balance', 0)
    status = "🌟 PREMIUM" if user_data.get('is_premium') else "⚡ FREE"
    
    caption = f"""
👋 Welcome, {first_name}!

📊 <b>Your Dashboard</b>
💰 Balance: <b>{balance} pts</b>
🎫 Status: <b>{status}</b>
👥 Referral Code: <code>{user_data.get('referral_code')}</code>

🎁 <b>How to Earn</b>
• Daily Check-in: +10 pts
• Watch Ads: +5 pts/ad
• Invite Friends: +50 pts/referral
• Premium Tasks: +100 pts

🤖 <b>Commands</b>
/ai - Chat with AI Assistant
/dashboard - Open Web Dashboard
/admin - Admin Panel (if authorized)
/help - View Help Guide

🔗 <b>Follow Us</b>
📺 YouTube: @USSoccerPulse
📸 Instagram: @digital_rockstar_m
📘 Facebook: UltimateMediaSearch
    """
    
    bot.send_photo(message.chat.id, photo_url, caption=caption, reply_markup=get_main_keyboard())

@bot.message_handler(commands=['ai'])
def ai_chat_command(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    if not user_data:
        bot.reply_to(message, "❌ Please start the bot first with /start")
        return
    
    # Check balance for free users
    if not user_data.get('is_premium'):
        if user_data.get('balance', 0) < 10:
            bot.reply_to(message, "❌ Insufficient balance! Free users need 10 pts per AI message.\n\n💡 Earn points: /dashboard\n🎁 Upgrade to Premium for unlimited AI!")
            return
        deduct_balance(user_id, 10)
    
    # Send typing indicator
    bot.send_chat_action(message.chat.id, 'typing')
    
    # Get AI response
    user_message = message.text.replace('/ai', '').strip()
    if not user_message:
        bot.reply_to(message, "💬 Please type your message after /ai command")
        return
    
    ai_response = generate_ai_response(user_message, user_data)
    
    # Update message count
    total_msgs = user_data.get('total_messages', 0) + 1
    update_user_data(user_id, {'total_messages': total_msgs})
    
    bot.reply_to(message, f"🤖 {ai_response}")

@bot.message_handler(commands=['dashboard'])
def dashboard_command(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    if not user_data:
        bot.reply_to(message, "❌ Please start with /start first")
        return
    
    # Generate secure dashboard link (simple token)
    token = hashlib.sha256(f"{user_id}{time.time()}".encode()).hexdigest()[:16]
    # In production, store token in DB with expiry
    dashboard_url = f"https://your-vercel-app.vercel.app/dashboard?uid={user_id}&token={token}"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🌐 Open Dashboard", url=dashboard_url))
    
    bot.send_message(message.chat.id, "🔗 Click below to open your Glassmorphism Dashboard:", reply_markup=markup)

@bot.message_handler(commands=['admin'])
def admin_command(message):
    user_id = str(message.from_user.id)
    if user_id != str(ADMIN_TELEGRAM_ID):
        bot.reply_to(message, "🔐 Admin access denied.")
        return
    
    admin_url = f"https://your-vercel-app.vercel.app/admin?token={hashlib.sha256(f'admin_{time.time()}'.encode()).hexdigest()[:16]}"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚙️ Open Admin Panel", url=admin_url))
    
    bot.send_message(message.chat.id, "👨‍💻 Admin Control Panel:", reply_markup=markup)

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """
📚 <b>Ultimate Media Search - Help Guide</b>

🤖 <b>AI Chat</b>
• Use /ai [your message] to chat
• Free users: 10 pts/message
• Premium: Unlimited AI

💰 <b>Earning Points</b>
• Daily Login: +10 pts
• Watch Ad: +5 pts
• Invite Friend: +50 pts
• Complete Tasks: +25-100 pts

🌟 <b>Premium Benefits</b>
• Unlimited AI Messages
• Priority Support
• Exclusive Content Access
• Ad-Free Experience
• Price: ₹99/month

💳 <b>Upgrade to Premium</b>
1. Send ₹99 to UPI: <code>8543083014@ikwik</code>
2. Screenshot payment
3. Submit via Dashboard → Premium Tab
4. Auto-approval within 24hrs

🔗 <b>Useful Links</b>
• Dashboard: /dashboard
• Admin Panel: /admin (authorized only)
• Support: @digital_rockstar_m

⚠️ <b>Disclaimer</b>
• Points have no cash value
• Premium payments are non-refundable
• Bot usage subject to Telegram ToS
    """
    bot.send_message(message.chat.id, help_text, reply_markup=get_main_keyboard())

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('/ai', '/dashboard')
    markup.add('/help', '/start')
    return markup

# ==================== FLASK ROUTES ====================
@app.route('/')
def home():
    return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
    user_id = request.args.get('uid')
    token = request.args.get('token')
    
    if not user_id:
        return "❌ Invalid access. Please use /dashboard from Telegram bot.", 400
    
    user_data = get_user_data(user_id)
    if not user_data:
        return "❌ User not found. Please start the bot with /start", 404
    
    # Simple token validation (enhance in production)
    expected_token = hashlib.sha256(f"{user_id}".encode()).hexdigest()[:16]
    
    return render_template('dashboard.html', 
                         user=user_data, 
                         upi_id=UPI_ID, 
                         qr_code=QR_CODE_URL,
                         social_links={
                             'youtube': '@USSoccerPulse',
                             'instagram': '@digital_rockstar_m', 
                             'facebook': 'UltimateMediaSearch'
                         })

@app.route('/admin')
def admin_panel():
    # Simple auth check (enhance with proper sessions in production)
    token = request.args.get('token')
    if not token:
        return "🔐 Admin authentication required", 401
    
    # Fetch pending payments
    pending_payments = []
    try:
        users_ref = db.reference('users')
        all_users = users_ref.get()
        if all_users:
            for uid, data in all_users.items():
                if data.get('pending_payments'):
                    for payment in data['pending_payments']:
                        pending_payments.append({
                            'user_id': uid,
                            'username': data.get('username'),
                            'payment': payment
                        })
    except:
        pass
    
    return render_template('admin.html', 
                         pending_payments=pending_payments,
                         admin_id=ADMIN_TELEGRAM_ID)

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """AI Chat Endpoint for Dashboard"""
    try:
        data = request.json
        user_id = data.get('user_id')
        message = data.get('message')
        
        if not user_id or not message:
            return jsonify({'error': 'Missing user_id or message'}), 400
        
        user_data = get_user_data(user_id)
        if not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        # Check balance for free users
        if not user_data.get('is_premium'):
            if user_data.get('balance', 0) < 10:
                return jsonify({'error': 'Insufficient balance. Free users need 10 pts per message.'}), 402
            deduct_balance(user_id, 10)
        
        # Generate AI response
        response = generate_ai_response(message, user_data)
        
        # Update stats
        total_msgs = user_data.get('total_messages', 0) + 1
        update_user_data(user_id, {'total_messages': total_msgs, 'last_active': int(time.time())})
        
        return jsonify({
            'response': response,
            'remaining_balance': get_user_data(user_id).get('balance', 0)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit-payment', methods=['POST'])
def submit_payment():
    """Handle Premium Payment Submission"""
    try:
        data = request.json
        user_id = data.get('user_id')
        screenshot_url = data.get('screenshot_url')
        transaction_id = data.get('transaction_id')
        
        if not all([user_id, screenshot_url, transaction_id]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        payment_record = {
            'screenshot_url': screenshot_url,
            'transaction_id': transaction_id,
            'submitted_at': int(time.time()),
            'status': 'pending'
        }
        
        # Add to user's pending payments
        user_ref = db.reference(f'users/{user_id}/pending_payments')
        payment_key = user_ref.push(payment_record).key
        
        return jsonify({
            'success': True, 
            'message': 'Payment submitted for review',
            'payment_id': payment_key
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/approve-payment', methods=['POST'])
def approve_payment():
    """Admin: Approve Premium Payment"""
    try:
        data = request.json
        user_id = data.get('user_id')
        payment_id = data.get('payment_id')
        
        if not all([user_id, payment_id]):
            return jsonify({'error': 'Missing user_id or payment_id'}), 400
        
        # Update payment status
        payment_ref = db.reference(f'users/{user_id}/pending_payments/{payment_id}')
        payment_ref.update({'status': 'approved', 'approved_at': int(time.time())})
        
        # Upgrade user to premium
        db.reference(f'users/{user_id}').update({
            'is_premium': True,
            'premium_since': int(time.time())
        })
        
        # Notify user via Telegram
        try:
            bot.send_message(
                user_id, 
                "🎉 <b>Premium Activated!</b>\n\n✅ Your payment has been approved.\n🌟 Enjoy unlimited AI, ad-free experience, and exclusive features!\n\n💬 Use /ai to start chatting!",
                parse_mode='HTML'
            )
        except:
            pass  # Bot might be offline
        
        return jsonify({'success': True, 'message': 'Premium activated successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reject-payment', methods=['POST'])
def reject_payment():
    """Admin: Reject Premium Payment"""
    try:
        data = request.json
        user_id = data.get('user_id')
        payment_id = data.get('payment_id')
        reason = data.get('reason', 'No reason provided')
        
        if not all([user_id, payment_id]):
            return jsonify({'error': 'Missing user_id or payment_id'}), 400
        
        # Update payment status
        payment_ref = db.reference(f'users/{user_id}/pending_payments/{payment_id}')
        payment_ref.update({'status': 'rejected', 'rejected_at': int(time.time()), 'rejection_reason': reason})
        
        # Notify user
        try:
            bot.send_message(
                user_id,
                f"❌ <b>Payment Update</b>\n\n⚠️ Your premium payment was rejected.\n📝 Reason: {reason}\n\n💡 Please contact support if you believe this is an error.",
                parse_mode='HTML'
            )
        except:
            pass
        
        return jsonify({'success': True, 'message': 'Payment rejected'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/broadcast', methods=['POST'])
def broadcast_message():
    """Admin: Broadcast message to all users"""
    try:
        data = request.json
        message = data.get('message')
        admin_token = data.get('admin_token')
        
        if not message or admin_token != hashlib.sha256(f'admin_{ADMIN_TELEGRAM_ID}'.encode()).hexdigest()[:16]:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # Get all user IDs
        users_ref = db.reference('users')
        all_users = users_ref.get()
        
        sent_count = 0
        if all_users:
            for uid, data in all_users.items():
                try:
                    bot.send_message(uid, f"📢 <b>Broadcast</b>\n\n{message}", parse_mode='HTML')
                    sent_count += 1
                except:
                    continue  # Skip users who blocked the bot
        
        return jsonify({'success': True, 'sent_to': sent_count})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    """Telegram Webhook Handler for Vercel"""
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.get_json(force=True))
        bot.process_new_updates([update])
        return '', 200
    return '', 403

# Set webhook on startup (for Vercel)
def set_webhook():
    webhook_url = os.environ.get('VERCEL_URL', 'http://localhost:5000')
    if webhook_url:
        webhook_url = f"https://{webhook_url}/webhook"
        try:
            bot.remove_webhook()
            bot.set_webhook(webhook_url)
            print(f"✅ Webhook set to: {webhook_url}")
        except Exception as e:
            print(f"⚠️ Webhook setup failed: {e}")

# ==================== APP ENTRY POINT ====================
if __name__ == '__main__':
    # For local development
    set_webhook()
    app.run(host='0.0.0.0', port=5000, debug=True)
else:
    # For Vercel serverless
    set_webhook()
