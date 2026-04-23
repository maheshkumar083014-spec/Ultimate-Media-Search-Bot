import os
import json
import uuid
import requests
import logging
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, make_response
from flask_cors import CORS
import telebot
from dotenv import load_dotenv

# Load environment variables for local development
load_dotenv()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ Configuration ============
BOT_TOKEN = os.getenv('BOT_TOKEN', '8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw')
FIREBASE_DATABASE_URL = os.getenv('FIREBASE_DATABASE_URL', 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', 'sk-783d645ce9e84eb8b954786a016561ea')
ADMIN_TELEGRAM_ID = int(os.getenv('ADMIN_TELEGRAM_ID', '123456789'))
UPI_ID = os.getenv('UPI_ID', '8543083014@ikwik')

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# ============ Initialize Flask ============
app = Flask(__name__, static_folder='../static', static_url_path='/static')

# Enable CORS for API routes
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-User-ID", "X-Telegram-User-Id"]
    }
})

# Initialize Telegram Bot (threaded=False for serverless)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML', threaded=False, disable_web_page_preview=True)

# ============ Firebase Initialization ============
firebase_ready = False
firebase_db = None

def init_firebase():
    """Initialize Firebase Admin SDK"""
    global firebase_ready, firebase_db
    try:
        from firebase_admin import credentials, initialize_app, db as firebase_db_module
        
        # Try to load service account from environment
        sa_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
        if sa_json:
            cred = credentials.Certificate(json.loads(sa_json))
        else:
            # Development fallback - configure proper database rules in production
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": "ultimatemediasearch",
                "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID', 'dev'),
                "private_key": os.getenv('FIREBASE_PRIVATE_KEY', '-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7...\n-----END PRIVATE KEY-----\n').replace('\\n', '\n'),
                "client_email": "firebase-adminsdk@ultimatemediasearch.iam.gserviceaccount.com",
                "client_id": os.getenv('FIREBASE_CLIENT_ID', 'dev'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk%40ultimatemediasearch.iam.gserviceaccount.com"
            })
        
        initialize_app(cred, {'databaseURL': FIREBASE_DATABASE_URL})
        firebase_db = firebase_db_module
        firebase_ready = True
        logger.info("✅ Firebase initialized successfully")
        return True
    except ImportError:
        logger.warning("⚠️ firebase-admin not installed - using mock mode")
        return False
    except Exception as e:
        logger.error(f"❌ Firebase init error: {e}")
        return False

# Initialize Firebase on startup
init_firebase()

# ============ Helper Functions ============
def get_user(uid):
    """Fetch user data from Firebase"""
    if not firebase_ready:
        return {'points': 0, 'plan': 'Free', 'referrals': [], 'joined': datetime.now().isoformat()}
    try:
        ref = firebase_db.reference(f'users/{uid}')
        data = ref.get()
        return data or {'points': 0, 'plan': 'Free', 'referrals': [], 'joined': datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"❌ Firebase read error: {e}")
        return {'points': 0, 'plan': 'Free', 'referrals': []}

def update_user(uid, data):
    """Update user data in Firebase"""
    if not firebase_ready:
        return False
    try:
        ref = firebase_db.reference(f'users/{uid}')
        ref.update(data)
        return True
    except Exception as e:
        logger.error(f"❌ Firebase write error: {e}")
        return False

def call_deepseek(messages):
    """Call DeepSeek API with OpenAI-compatible format"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }
    try:
        resp = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=45)
        resp.raise_for_status()
        return resp.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logger.error(f"❌ DeepSeek API error: {e}")
        return "⚠️ AI service temporarily unavailable. Please try again later."

def verify_admin(req):
    """Verify admin access via Telegram user ID header"""
    admin_id = req.headers.get('X-Telegram-User-Id')
    return admin_id and int(admin_id) == ADMIN_TELEGRAM_ID

def get_task_links():
    """Get social task links from Firebase config"""
    default = {
        'youtube': 'https://www.youtube.com/@USSoccerPulse',
        'instagram': 'https://www.instagram.com/digital_rockstar_m',
        'facebook': 'https://www.facebook.com/UltimateMediaSearch'
    }
    if not firebase_ready:
        return default
    try:
        data = firebase_db.reference('config/tasks').get()
        return {**default, **(data or {})}
    except:
        return default

def cors_response(response):
    """Add CORS headers to response"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-User-ID, X-Telegram-User-Id')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    return response

# ============ Telegram Bot Handlers ============
@bot.message_handler(commands=['start'])
def cmd_start(msg):
    """Handle /start command with referral support"""
    try:
        uid = msg.from_user.id
        name = msg.from_user.first_name or "Friend"
        username = msg.from_user.username or ""
        ref_code = msg.text.split()[-1] if len(msg.text.split()) > 1 else None
        
        # Handle referral logic
        if ref_code and ref_code.isdigit() and int(ref_code) != uid:
            referrer_data = get_user(ref_code)
            current_data = get_user(uid)
            
            # Prevent duplicate referrals
            if not current_data.get('referred_by') and uid not in referrer_data.get('referrals', []):
                # Award referral bonus
                update_user(ref_code, {
                    'points': (referrer_data.get('points', 0) + 50),
                    'referrals': list(set(referrer_data.get('referrals', []) + [str(uid)])),
                    'last_referral': datetime.now().isoformat()
                })
                update_user(uid, {
                    'referred_by': str(ref_code),
                    'points': current_data.get('points', 0) + 25,
                    'joined': datetime.now().isoformat()
                })
                # Notify referrer
                try:
                    bot.send_message(
                        ref_code,
                        f"🎉 <b>New Referral!</b>\n\n"
                        f"👤 @{username or uid} joined via your link!\n"
                        f"💰 +50 bonus points added to your account!",
                        parse_mode='HTML'
                    )
                except:
                    pass
        
        # Get user data
        data = get_user(uid)
        plan_display = {
            'Free': 'Free',
            'Earner_Pro': '🥇 Earner Pro',
            'Influencer_Pro': '🌟 Influencer Pro'
        }.get(data.get('plan', 'Free'), 'Free')
        
        # Welcome photo and caption
        photo = "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg"
        dashboard_url = f"https://{os.getenv('VERCEL_URL', 'localhost:5000')}/dashboard?uid={uid}"
        
        caption = (
            f"👋 <b>Welcome, {name}!</b>\n\n"
            f"📊 <b>Your Account</b>\n"
            f"├─ 💰 Points: <code>{data.get('points', 0)}</code>\n"
            f"├─ 🎫 Plan: <code>{plan_display}</code>\n"
            f"├─ 👥 Referrals: <code>{len(data.get('referrals', []))}</code>\n"
            f"└─ 🔗 Ref Link: <code>https://t.me/{bot.get_me().username}?start={uid}</code>\n\n"
            f"🚀 Tap below to open your dashboard!"
        )
        
        # Inline keyboard
        kb = telebot.types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            telebot.types.InlineKeyboardButton('🚀 Open Dashboard', url=dashboard_url),
            telebot.types.InlineKeyboardButton('💎 Upgrade', callback_data='upgrade')
        )
        kb.add(
            telebot.types.InlineKeyboardButton('🤖 AI Chat', callback_data='ai_chat'),
            telebot.types.InlineKeyboardButton('👥 Invite Friends', callback_data='refer')
        )
        
        bot.send_photo(msg.chat.id, photo, caption=caption, reply_markup=kb)
        
    except Exception as e:
        logger.error(f"❌ /start error: {e}")
        bot.reply_to(msg, "⚠️ Something went wrong. Please try /start again.")

@bot.message_handler(commands=['ai'])
def cmd_ai(msg):
    """Handle /ai command for DeepSeek chat"""
    try:
        uid = msg.from_user.id
        plan = get_user(uid).get('plan', 'Free')
        question = msg.text.replace('/ai', '', 1).strip()
        
        if not question:
            bot.reply_to(msg, "❓ Usage: <code>/ai Your question here</code>\n💡 Free users: 10 pts/query", parse_mode='HTML')
            return
        
        # Deduct points for Free users
        if plan == 'Free':
            current = get_user(uid).get('points', 0)
            if current < 10:
                bot.reply_to(msg, "❌ <b>Insufficient Points!</b>\n\nNeed: 10 | Have: {}\n💎 Upgrade for unlimited AI!".format(current), parse_mode='HTML')
                return
            update_user(uid, {'points': current - 10})
            bot.reply_to(msg, "🤖 <em>Thinking... (-10 pts)</em>", parse_mode='HTML')
        
        # Call DeepSeek API
        messages = [
            {"role": "system", "content": "You are EarnBot AI, a helpful Telegram assistant for EarnBot users. Be concise, friendly, and helpful. Answer in the user's language when possible."},
            {"role": "user", "content": question}
        ]
        reply = call_deepseek(messages)
        
        # Send response (truncate if too long)
        if len(reply) > 4000:
            reply = reply[:3997] + "..."
        bot.reply_to(msg, f"🤖 <b>AI Response:</b>\n\n{reply}", parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"❌ /ai error: {e}")
        bot.reply_to(msg, "⚠️ AI service error. Please try again later.")

@bot.message_handler(commands=['refer'])
def cmd_refer(msg):
    """Handle /refer command to show referral info"""
    try:
        uid = msg.from_user.id
        data = get_user(uid)
        ref_link = f"https://t.me/{bot.get_me().username}?start={uid}"
        
        bot.reply_to(msg,
            f"👥 <b>Referral Program</b>\n\n"
            f"🔗 Your Link:\n<code>{ref_link}</code>\n\n"
            f"🎁 Rewards:\n"
            f"• +25 pts when someone joins via your link\n"
            f"• +50 pts when they complete their first task\n\n"
            f"📊 Your Stats:\n"
            f"• Total Referrals: <code>{len(data.get('referrals', []))}</code>\n"
            f"• Earned from referrals: <code>{len(data.get('referrals', [])) * 50}</code> pts",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"❌ /refer error: {e}")
        bot.reply_to(msg, "⚠️ Error fetching referral info.")

@bot.callback_query_handler(func=lambda c: True)
def handle_callback(call):
    """Handle all inline button callbacks"""
    try:
        uid = call.from_user.id
        data = get_user(uid)
        bot.answer_callback_query(call.id)  # Acknowledge callback
        
        if call.data == 'dashboard':
            dashboard_url = f"https://{os.getenv('VERCEL_URL', 'localhost:5000')}/dashboard?uid={uid}"
            kb = telebot.types.InlineKeyboardMarkup()
            kb.add(telebot.types.InlineKeyboardButton('🚀 Open Dashboard', url=dashboard_url))
            bot.edit_message_text(
                "📊 <b>Dashboard</b>\n\nClick below to open your web dashboard:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode='HTML',
                reply_markup=kb
            )
        
        elif call.data == 'upgrade':
            kb = telebot.types.InlineKeyboardMarkup()
            kb.add(
                telebot.types.InlineKeyboardButton('🥇 Earner Pro - ₹100', callback_data='buy_earner'),
                telebot.types.InlineKeyboardButton('🌟 Influencer Pro - ₹500', callback_data='buy_influencer')
            )
            kb.add(telebot.types.InlineKeyboardButton('💳 UPI Info', callback_data='upi_info'))
            bot.edit_message_text(
                f"💎 <b>Upgrade Plans</b>\n\n"
                f"🥇 <b>Earner Pro (₹100)</b>\n• 2x points on all tasks\n• 500 bonus points\n• Priority support\n\n"
                f"🌟 <b>Influencer Pro (₹500)</b>\n• Unlimited AI queries\n• 5x points multiplier\n• Promote your link feature\n• Exclusive badges\n\n"
                f"📱 Pay via UPI: <code>{UPI_ID}</code>\nThen submit your TXN ID in the dashboard:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode='HTML',
                reply_markup=kb
            )
        
        elif call.data == 'ai_chat':
            bot.edit_message_text(
                "🤖 <b>AI Chat</b>\n\n"
                "Use <code>/ai [your question]</code> to start chatting with AI.\n\n"
                "💡 Pricing:\n"
                "• Free users: 10 pts per query\n"
                "• Pro users: Unlimited queries",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode='HTML'
            )
        
        elif call.data == 'refer':
            ref_link = f"https://t.me/{bot.get_me().username}?start={uid}"
            kb = telebot.types.InlineKeyboardMarkup()
            kb.add(telebot.types.InlineKeyboardButton('🔗 Share Link', url=f'https://t.me/share/url?url={ref_link}&text=Join%20EarnBot%20%26%20earn%20rewards!'))
            bot.edit_message_text(
                f"👥 <b>Invite & Earn</b>\n\n"
                f"🔗 Your Referral Link:\n<code>{ref_link}</code>\n\n"
                f"🎁 Rewards:\n"
                f"• +25 pts per signup\n"
                f"• +50 pts when they complete first task\n\n"
                f"📊 Your referrals: <code>{len(data.get('referrals', []))}</code>",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode='HTML',
                reply_markup=kb
            )
        
        elif call.data.startswith('buy_'):
            plan = "Earner_Pro" if "earner" in call.data else "Influencer_Pro"
            price = "₹100" if "earner" in call.data else "₹500"
            bot.edit_message_text(
                f"💳 <b>{plan.replace('_', ' ').title()} - {price}</b>\n\n"
                f"1️⃣ Pay <code>{price}</code> to UPI: <code>{UPI_ID}</code>\n"
                f"2️⃣ Copy your Transaction ID\n"
                f"3️⃣ Open dashboard → 💎 Upgrade → Submit TXN\n"
                f"4️⃣ Admin verifies within ~24 hours ✅\n\n"
                f"⚠️ Keep your payment screenshot safe!",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode='HTML'
            )
        
        elif call.data == 'upi_info':
            bot.answer_callback_query(call.id, f"UPI ID: {UPI_ID}", show_alert=True)
            
    except Exception as e:
        logger.error(f"❌ Callback error: {e}")
        bot.answer_callback_query(call.id, "⚠️ Error. Please try /start again.", show_alert=True)

# ============ Flask Routes - Static Files ============
@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files from ../static folder"""
    return send_from_directory('../static', filename)

@app.route('/dashboard')
@app.route('/welcome')
@app.route('/admin')
@app.route('/')
def serve_frontend():
    """Serve frontend HTML files based on route"""
    path = request.path.strip('/')
    
    if path in ['admin', 'admin.html']:
        return send_from_directory('../static', 'admin.html')
    elif path in ['', 'dashboard', 'welcome', 'index.html']:
        return send_from_directory('../static', 'index.html')
    else:
        return send_from_directory('../static', 'index.html')

# ============ API Endpoints ============
@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def api_chat():
    """AI Chat endpoint - calls DeepSeek API"""
    if request.method == 'OPTIONS':
        return cors_response(make_response('', 204))
    
    try:
        data = request.get_json(force=True, silent=True) or {}
        uid = data.get('user_id')
        message = data.get('message', '').strip()
        
        if not uid or not message:
            return cors_response(jsonify({'error': 'Missing required fields: user_id, message'})), 400
        
        user = get_user(uid)
        
        # Deduct points for Free users
        if user.get('plan') == 'Free':
            if user.get('points', 0) < 10:
                return cors_response(jsonify({'error': 'Insufficient points. Need 10 pts for AI query.'})), 402
            update_user(uid, {'points': user['points'] - 10})
        
        # Call DeepSeek
        messages = [
            {"role": "system", "content": "You are EarnBot AI, a helpful assistant. Be concise and friendly."},
            {"role": "user", "content": message}
        ]
        reply = call_deepseek(messages)
        
        return cors_response(jsonify({'reply': reply, 'points_used': 10 if user.get('plan') == 'Free' else 0})), 200
        
    except Exception as e:
        logger.error(f"❌ /api/chat error: {e}")
        return cors_response(jsonify({'error': 'Internal server error'})), 500

@app.route('/api/upgrade/submit', methods=['POST', 'OPTIONS'])
def submit_upgrade():
    """Submit premium upgrade request with payment proof"""
    if request.method == 'OPTIONS':
        return cors_response(make_response('', 204))
    
    try:
        data = request.get_json(force=True, silent=True) or {}
        uid = data.get('user_id')
        plan = data.get('plan')
        txn = data.get('transaction_id', '').strip()
        
        if not all([uid, plan, txn]):
            return cors_response(jsonify({'error': 'Missing required fields: user_id, plan, transaction_id'})), 400
        
        # Create pending upgrade record
        upgrade_id = uuid.uuid4().hex
        firebase_db.reference(f'upgrades/pending/{upgrade_id}').set({
            'user_id': uid,
            'plan': plan,
            'transaction_id': txn,
            'screenshot_url': data.get('screenshot_url', ''),
            'amount': 100 if plan == 'Earner_Pro' else 500,
            'status': 'pending',
            'submitted_at': datetime.now().isoformat(),
            'submitted_from': request.headers.get('X-User-ID', 'unknown')
        }) if firebase_ready else None
        
        # Notify admin via Telegram
        try:
            bot.send_message(
                ADMIN_TELEGRAM_ID,
                f"🔔 <b>New Upgrade Request</b>\n\n"
                f"👤 User: <code>{uid}</code>\n"
                f"💎 Plan: <code>{plan}</code>\n"
                f"🧾 TXN: <code>{txn}</code>\n"
                f"💰 Amount: ₹{100 if plan == 'Earner_Pro' else 500}\n\n"
                f"✅ Check admin panel to approve!",
                parse_mode='HTML'
            )
        except:
            pass
        
        return cors_response(jsonify({'success': True, 'message': 'Upgrade request submitted! Admin will verify within 24h.'})), 200
        
    except Exception as e:
        logger.error(f"❌ /api/upgrade/submit error: {e}")
        return cors_response(jsonify({'error': 'Submission failed. Please try again.'})), 500

@app.route('/api/tasks', methods=['GET', 'OPTIONS'])
def api_tasks():
    """Get social task links"""
    if request.method == 'OPTIONS':
        return cors_response(make_response('', 204))
    return cors_response(jsonify({'tasks': get_task_links()})), 200

@app.route('/api/user/<uid>', methods=['GET', 'OPTIONS'])
def api_user(uid):
    """Get user data by ID"""
    if request.method == 'OPTIONS':
        return cors_response(make_response('', 204))
    return cors_response(jsonify(get_user(uid))), 200

@app.route('/api/referral/stats', methods=['GET', 'OPTIONS'])
def api_referral_stats():
    """Get referral statistics for a user"""
    if request.method == 'OPTIONS':
        return cors_response(make_response('', 204))
    
    uid = request.args.get('uid')
    if not uid:
        return cors_response(jsonify({'error': 'Missing uid parameter'})), 400
    
    data = get_user(uid)
    referrals = data.get('referrals', [])
    
    return cors_response(jsonify({
        'total_referrals': len(referrals),
        'referral_list': referrals[:10],  # Return first 10 for privacy
        'earned_from_refs': len(referrals) * 50,
        'pending_bonus': len(referrals) * 25  # Simplified logic
    })), 200

# ============ Admin Endpoints (Protected) ============
@app.route('/admin/api/users', methods=['GET', 'OPTIONS'])
def admin_get_users():
    """Get all users - Admin only"""
    if request.method == 'OPTIONS':
        return cors_response(make_response('', 204))
    if not verify_admin(request):
        return cors_response(jsonify({'error': 'Unauthorized - Admin access required'})), 401
    
    try:
        users = firebase_db.reference('users').get() if firebase_ready else {}
        users = users or {}
        
        # Format and clean response
        user_list = []
        for uid, data in users.items():
            if isinstance(data, dict):
                user_list.append({
                    'id': uid,
                    'name': data.get('name', 'Unknown'),
                    'username': data.get('username', ''),
                    'points': data.get('points', 0),
                    'plan': data.get('plan', 'Free'),
                    'referrals': len(data.get('referrals', [])),
                    'joined': data.get('joined'),
                    'last_active': data.get('last_active')
                })
        
        # Sort by join date (newest first)
        user_list.sort(key=lambda x: x.get('joined', ''), reverse=True)
        
        return cors_response(jsonify({'users': user_list, 'total': len(user_list)})), 200
        
    except Exception as e:
        logger.error(f"❌ Admin users error: {e}")
        return cors_response(jsonify({'error': 'Failed to fetch users'})), 500

@app.route('/admin/api/upgrades', methods=['GET', 'POST', 'OPTIONS'])
def admin_manage_upgrades():
    """Manage pending upgrades - Admin only"""
    if request.method == 'OPTIONS':
        return cors_response(make_response('', 204))
    if not verify_admin(request):
        return cors_response(jsonify({'error': 'Unauthorized'})), 401
    
    if request.method == 'GET':
        try:
            pending = firebase_db.reference('upgrades/pending').get() if firebase_ready else {}
            pending = pending or {}
            
            upgrades = []
            for key, data in pending.items():
                if isinstance(data, dict) and data.get('status') == 'pending':
                    upgrades.append({'id': key, **data})
            
            # Sort by submission time (newest first)
            upgrades.sort(key=lambda x: x.get('submitted_at', ''), reverse=True)
            
            return cors_response(jsonify({'upgrades': upgrades, 'total': len(upgrades)})), 200
            
        except Exception as e:
            logger.error(f"❌ Admin upgrades GET error: {e}")
            return cors_response(jsonify({'error': 'Failed to fetch upgrades'})), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json(force=True) or {}
            upgrade_id = data.get('upgrade_id')
            action = data.get('action')  # 'approve' or 'reject'
            
            if not upgrade_id or action not in ['approve', 'reject']:
                return cors_response(jsonify({'error': 'Invalid request parameters'})), 400
            
            ref = firebase_db.reference(f'upgrades/pending/{upgrade_id}')
            upgrade = ref.get()
            
            if not upgrade:
                return cors_response(jsonify({'error': 'Upgrade request not found'})), 404
            
            if action == 'approve':
                # Update user plan and award bonus points
                user_ref = firebase_db.reference(f'users/{upgrade["user_id"]}')
                current = user_ref.get() or {}
                
                bonus = 500 if upgrade['plan'] == 'Earner_Pro' else 2500
                user_ref.update({
                    'plan': upgrade['plan'],
                    'points': (current.get('points', 0) + bonus),
                    'upgraded_at': datetime.now().isoformat()
                })
                
                # Notify user via Telegram
                try:
                    bot.send_message(
                        int(upgrade['user_id']),
                        f"🎉 <b>Upgrade Approved!</b>\n\n"
                        f"✅ You are now <b>{upgrade['plan'].replace('_', ' ').title()}</b>!\n"
                        f"💰 Bonus: +{bonus} points added to your account.\n\n"
                        f"Enjoy your premium features! 🚀",
                        parse_mode='HTML'
                    )
                except:
                    pass
            
            # Move to history and delete from pending
            firebase_db.reference(f'upgrades/history/{upgrade_id}').set({
                **upgrade,
                'status': action,
                'processed_at': datetime.now().isoformat(),
                'processed_by': ADMIN_TELEGRAM_ID
            })
            ref.delete()
            
            return cors_response(jsonify({'success': True, 'message': f'Upgrade {action}d successfully'})), 200
            
        except Exception as e:
            logger.error(f"❌ Admin upgrades POST error: {e}")
            return cors_response(jsonify({'error': f'Processing failed: {str(e)}'})), 500

@app.route('/admin/api/points', methods=['POST', 'OPTIONS'])
def admin_adjust_points():
    """Manually adjust user points - Admin only"""
    if request.method == 'OPTIONS':
        return cors_response(make_response('', 204))
    if not verify_admin(request):
        return cors_response(jsonify({'error': 'Unauthorized'})), 401
    
    try:
        data = request.get_json(force=True) or {}
        uid = data.get('user_id')
        amount = int(data.get('amount', 0))
        reason = data.get('reason', 'Admin adjustment')
        
        if not uid or amount == 0:
            return cors_response(jsonify({'error': 'Invalid parameters: user_id and amount required'})), 400
        
        # Update points
        ref = firebase_db.reference(f'users/{uid}/points')
        current = ref.get() or 0
        new_value = current + amount
        ref.set(new_value)
        
        # Log the adjustment
        firebase_db.reference('logs/point_adjustments').push({
            'user_id': uid,
            'adjusted_by': ADMIN_TELEGRAM_ID,
            'amount': amount,
            'previous': current,
            'new': new_value,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
        
        # Notify user if significant change
        if abs(amount) >= 50:
            try:
                bot.send_message(
                    int(uid),
                    f"💰 <b>Points Updated</b>\n\n"
                    f"{'➕ Added' if amount > 0 else '➖ Deducted'}: <b>{abs(amount)} pts</b>\n"
                    f"📝 Reason: {reason}\n"
                    f"📊 New Balance: <b>{new_value}</b>",
                    parse_mode='HTML'
                )
            except:
                pass
        
        return cors_response(jsonify({'success': True, 'new_points': new_value})), 200
        
    except Exception as e:
        logger.error(f"❌ Admin points error: {e}")
        return cors_response(jsonify({'error': f'Adjustment failed: {str(e)}'})), 500

@app.route('/admin/api/tasks', methods=['GET', 'POST', 'OPTIONS'])
def admin_manage_tasks():
    """Manage social task links - Admin only"""
    if request.method == 'OPTIONS':
        return cors_response(make_response('', 204))
    if not verify_admin(request):
        return cors_response(jsonify({'error': 'Unauthorized'})), 401
    
    if request.method == 'GET':
        return cors_response(jsonify({'tasks': get_task_links()})), 200
    
    elif request.method == 'POST':
        try:
            data = request.get_json(force=True) or {}
            # Only allow updates to known task keys with valid URLs
            updates = {
                k: v for k, v in data.items() 
                if k in ['youtube', 'instagram', 'facebook'] and str(v).startswith('https://')
            }
            
            if not updates:
                return cors_response(jsonify({'error': 'No valid updates provided'})), 400
            
            firebase_db.reference('config/tasks').update(updates)
            
            return cors_response(jsonify({'success': True, 'updated': updates})), 200
            
        except Exception as e:
            logger.error(f"❌ Admin tasks error: {e}")
            return cors_response(jsonify({'error': f'Update failed: {str(e)}'})), 500

@app.route('/admin/api/broadcast', methods=['POST', 'OPTIONS'])
def admin_broadcast():
    """Send broadcast message to users - Admin only"""
    if request.method == 'OPTIONS':
        return cors_response(make_response('', 204))
    if not verify_admin(request):
        return cors_response(jsonify({'error': 'Unauthorized'})), 401
    
    try:
        data = request.get_json(force=True) or {}
        message = data.get('message', '').strip()
        target_plan = data.get('target_plan')  # None = all, or specific plan
        
        if not message:
            return cors_response(jsonify({'error': 'Message content is required'})), 400
        
        users = firebase_db.reference('users').get() if firebase_ready else {}
        users = users or {}
        
        sent = failed = 0
        
        for uid, udata in users.items():
            # Skip non-numeric UIDs (not Telegram users)
            if not uid.isdigit():
                continue
            # Filter by plan if specified
            if target_plan and udata.get('plan') != target_plan:
                continue
            
            try:
                bot.send_message(
                    int(uid),
                    f"📢 <b>Official Update</b>:\n\n{message}",
                    parse_mode='HTML'
                )
                sent += 1
            except Exception as e:
                logger.warning(f"⚠️ Failed to send to {uid}: {e}")
                failed += 1
        
        # Also save to notifications node for dashboard toast display
        firebase_db.reference('notifications').push({
            'title': '📢 Admin Update',
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'target_plan': target_plan or 'all',
            'sent_count': sent
        }) if firebase_ready else None
        
        return cors_response(jsonify({
            'success': True,
            'sent': sent,
            'failed': failed,
            'total': sent + failed
        })), 200
        
    except Exception as e:
        logger.error(f"❌ Admin broadcast error: {e}")
        return cors_response(jsonify({'error': f'Broadcast failed: {str(e)}'})), 500

# ============ Telegram Webhook Handler ============
@app.route('/webhook', methods=['POST', 'OPTIONS'])
def webhook():
    """Telegram webhook endpoint for bot updates"""
    if request.method == 'OPTIONS':
        return cors_response(make_response('', 204))
    
    if request.content_type != 'application/json':
        return jsonify({'error': 'Invalid content type - expected application/json'}), 400
    
    try:
        update = telebot.types.Update.de_json(request.get_json(force=True))
        bot.process_new_updates([update])
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        logger.error(f"❌ Webhook processing error: {e}")
        return jsonify({'error': 'Failed to process update'}), 500

# ============ Health Check & Utility Endpoints ============
@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    """Health check endpoint"""
    if request.method == 'OPTIONS':
        return cors_response(make_response('', 204))
    
    return cors_response(jsonify({
        'status': 'healthy',
        'firebase': firebase_ready,
        'bot_active': bot.get_me() is not None,
        'timestamp': datetime.now().isoformat()
    })), 200

@app.route('/api/config', methods=['GET', 'OPTIONS'])
def get_config():
    """Get public bot configuration"""
    if request.method == 'OPTIONS':
        return cors_response(make_response('', 204))
    
    return cors_response(jsonify({
        'upi_id': UPI_ID,
        'task_links': get_task_links(),
        'bot_username': bot.get_me().username if bot.get_me() else 'EarnBot',
        'plans': {
            'Free': {'ai_cost': 10, 'multiplier': 1},
            'Earner_Pro': {'ai_cost': 0, 'multiplier': 2, 'price': 100},
            'Influencer_Pro': {'ai_cost': 0, 'multiplier': 5, 'price': 500}
        }
    })), 200

# ============ CORS Preflight Handler (Global) ============
@app.before_request
def handle_preflight():
    """Handle CORS preflight OPTIONS requests"""
    if request.method == 'OPTIONS':
        response = make_response('', 204)
        return cors_response(response)

# ============ Error Handlers ============
@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    if request.path.startswith('/api/') or request.path.startswith('/admin/api/'):
        return cors_response(jsonify({'error': 'Endpoint not found'})), 404
    return send_from_directory('../static', 'index.html'), 200

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    logger.error(f"❌ Server error: {e}")
    if request.path.startswith('/api/') or request.path.startswith('/admin/api/'):
        return cors_response(jsonify({'error': 'Internal server error'})), 500
    return "Internal Server Error", 500

# ============ Vercel Serverless Handler ============
def handler(req, ctx=None):
    """Vercel serverless function entry point"""
    return app(req.environ, lambda status, headers, exc_info=None: None)

# ============ Local Development Entry Point ============
if __name__ == '__main__':
    # Only for local development - DO NOT use in production
    port = int(os.getenv('PORT', 8080))
    logger.info(f"🚀 Starting EarnBot server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_ENV') == 'development')
