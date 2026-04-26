"""
🤖 Ultimate Media Search Bot - Complete Professional Edition
✅ UPI Payment Integration (Direct)
✅ DeepSeek AI Chat Integration
✅ Full Admin Panel Control
✅ Firebase asia-southeast1
✅ Vercel Serverless Ready
"""

import os
import sys
import json
import time
import logging
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Dict, Any
from functools import wraps
import requests
from flask import Flask, request, jsonify, render_template, render_template_string, session, redirect, url_for
from flask_cors import CORS

# ─────────────────────────────────────────────────────────────────────
# 🔧 Logging Setup
# ─────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)
logger.info("🚀 Starting Ultimate Media Search Bot v3.0...")

# ─────────────────────────────────────────────────────────────────────
# 🔐 Security Functions
# ─────────────────────────────────────────────────────────────────────
def validate_user_input(data: str, max_length: int = 1000) -> str:
    """Sanitize user input"""
    if not data:
        return ''
    sanitized = ''.join(c for c in str(data) if ord(c) < 128)
    return sanitized[:max_length].strip()

def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure token"""
    return secrets.token_hex(length)

# ─────────────────────────────────────────────────────────────────────
# 🔐 Firebase Credential Parser
# ─────────────────────────────────────────────────────────────────────
def parse_firebase_credentials(env_value: str) -> Optional[Dict[str, Any]]:
    if not env_value or env_value == 'skip':
        logger.warning("⚠️ FIREBASE_SERVICE_ACCOUNT not set")
        return None
    try:
        if isinstance(env_value, dict):
            return _fix_private_key(env_value)
        creds = json.loads(env_value)
        if not isinstance(creds, dict) or 'private_key' not in creds:
            raise ValueError("Invalid format")
        return _fix_private_key(creds)
    except Exception as e:
        logger.error(f"❌ Credential parse failed: {e}")
        return None

def _fix_private_key(creds: Dict[str, Any]) -> Dict[str, Any]:
    key = creds.get('private_key', '')
    if not key or '-----BEGIN PRIVATE KEY-----' in key:
        return creds
    key = key.replace('\\\\n', '\n').replace('\\n', '\n')
    if not key.strip().startswith('-----BEGIN PRIVATE KEY-----'):
        key = '-----BEGIN PRIVATE KEY-----\n' + key.strip()
    if not key.strip().endswith('-----END PRIVATE KEY-----'):
        key = key.strip() + '\n-----END PRIVATE KEY-----\n'
    creds['private_key'] = key
    return creds

# ─────────────────────────────────────────────────────────────────────
# 🗄️ Firebase Initialization
# ─────────────────────────────────────────────────────────────────────
def init_firebase() -> bool:
    try:
        import firebase_admin
        from firebase_admin import credentials, db
        if firebase_admin._apps:
            return True
        db_url = os.environ.get('FIREBASE_DB_URL', 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/').rstrip('/')
        sa_raw = os.environ.get('FIREBASE_SERVICE_ACCOUNT', 'skip')
        sa = parse_firebase_credentials(sa_raw)
        if not sa:
            logger.warning("⚠️ Using REST API fallback")
            return False
        firebase_admin.initialize_app(credentials.Certificate(sa), {
            'databaseURL': db_url,
            'projectId': sa.get('project_id')
        })
        logger.info("✅ Firebase Admin SDK initialized")
        return True
    except ImportError:
        logger.warning("⚠️ firebase-admin missing, using REST")
        return False
    except Exception as e:
        logger.error(f"❌ Firebase init failed: {e}")
        return False

FIREBASE_MODE = 'admin' if init_firebase() else 'rest'

class FirebaseREST:
    def __init__(self, url): self.base = url.rstrip('/')
    def _req(self, method, path, data=None):
        try:
            r = requests.request(method, f"{self.base}/{path}.json", json=data, headers={'Content-Type':'application/json'}, timeout=10)
            return r.json() if r.status_code in [200,201] else None
        except: return None
    def get(self, p): return self._req('GET', p)
    def set(self, p, d): return self._req('PUT', p, d) is not None
    def update(self, p, d): return self._req('PATCH', p, d) is not None

firebase_db = FirebaseREST(os.environ.get('FIREBASE_DB_URL', 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/')) if FIREBASE_MODE == 'rest' else None

def get_user(tid):
    return firebase_db.get(f'users/{tid}') if FIREBASE_MODE == 'rest' else db.reference(f'users/{tid}').get()
def set_user(tid, d):
    return firebase_db.set(f'users/{tid}', d) if FIREBASE_MODE == 'rest' else db.reference(f'users/{tid}').set(d)
def update_user(tid, d):
    return firebase_db.update(f'users/{tid}', d) if FIREBASE_MODE == 'rest' else db.reference(f'users/{tid}').update(d)

# ─────────────────────────────────────────────────────────────────────
# 🔧 Configuration
# ─────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8701635891:AAFmgU89KRhd2dhE-PqRY-mBmGy_SxQEGOg')
VERCEL_DOMAIN = os.environ.get('VERCEL_URL', 'ultimate-media-search-bot.vercel.app')
if not VERCEL_DOMAIN.startswith('https://'): VERCEL_DOMAIN = f"https://{VERCEL_DOMAIN}"

ADMIN_KEY = os.environ.get('ADMIN_KEY', 'UltimateAdmin2026Secure!')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')

APP_CONFIG = {
    'POINTS_PER_DOLLAR': 100, 'AD_POINTS': 25, 'SOCIAL_POINTS': 100,
    'REFERRAL_BONUS': 50, 'MIN_WITHDRAW': 100,
    'PLAN_100_PRICE': 100, 'PLAN_500_PRICE': 500,
    'AD_LINK': 'https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b',
    'YOUTUBE': 'https://youtube.com/@USSoccerPulse',
    'INSTAGRAM': 'https://instagram.com/digital_rockstar_m',
    'FACEBOOK': 'https://www.facebook.com/UltimateMediaSearch',
    'BANNER': 'https://i.ibb.co/9kmTw4Gh/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg',
    'SUPPORT_LINK': 'https://t.me/YourSupportUsername',
    'COMMUNITY_LINK': 'https://t.me/YourCommunityLink',
    'UPI_ID': '8543083014@ikwik',
    'UPI_NAME': 'Ultimate Media Search',
    'DASHBOARD_URL': f'{VERCEL_DOMAIN}/dashboard',
    'ADMIN_URL': f'{VERCEL_DOMAIN}/admin',
    'DEEPSEEK_BASE_URL': 'https://api.deepseek.com',
    'DEEPSEEK_MODEL': 'deepseek-chat'
}

FIREBASE_CONFIG = {
    'apiKey': os.environ.get('FIREBASE_API_KEY', 'AIzaSyD50eWvysruXgtgpDhhCVE2zdbSbLkFBwk'),
    'authDomain': 'ultimatemediasearch.firebaseapp.com',
    'databaseURL': os.environ.get('FIREBASE_DB_URL'),
    'projectId': 'ultimatemediasearch',
    'storageBucket': 'ultimatemediasearch.firebasestorage.app',
    'messagingSenderId': '123003124713',
    'appId': os.environ.get('FIREBASE_APP_ID', '1:123003124713:web:c738c97b2772b112822978')
}

# ─────────────────────────────────────────────────────────────────────
# 🌐 Flask App
# ─────────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = os.urandom(32).hex()
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ─────────────────────────────────────────────────────────────────────
# 🌐 Flask Routes
# ─────────────────────────────────────────────────────────────────────

@app.route('/')
def root():
    return f'''<html><body style="background:#1a202c;color:#fff;text-align:center;padding:40px;font-family:sans-serif">
    <h1>🤖 Ultimate Media Search Bot</h1><p style="color:#94a3b8;margin:20px 0">Server running! ✅</p>
    <a href="{APP_CONFIG['DASHBOARD_URL']}?id=123&name=Test" style="display:inline-block;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;padding:14px 32px;border-radius:12px;text-decoration:none;font-weight:600">🚀 Open Dashboard</a>
    <p style="margin-top:30px;font-size:0.9rem;color:#64748b">Firebase: {FIREBASE_MODE}</p></body></html>'''

@app.route('/dashboard')
def dashboard():
    tid = request.args.get('id', '123')
    name = request.args.get('name', 'User')
    tid = validate_user_input(str(tid), 50)
    name = validate_user_input(name, 100)
    try:
        if not get_user(tid):
            set_user(tid, {'uid':tid,'name':name,'username':name,'points':0,'total_earned':0,'ad_views':0,'tasks_completed':0,'joined_at':int(time.time()*1000),'last_active':int(time.time()*1000),'referral_code':'UMS'+str(tid)[-6:].upper(),'plan':'free'})
    except Exception as e: logger.error(f"User creation error: {e}")
    return render_template('dashboard.html', firebase_config=json.dumps(FIREBASE_CONFIG), app_config=json.dumps(APP_CONFIG))

@app.route('/admin')
def admin_panel():
    admin_key = request.args.get('key', ADMIN_KEY)
    return render_template('admin.html', firebase_config=json.dumps(FIREBASE_CONFIG), admin_key=admin_key)

@app.route('/health')
def health():
    return jsonify({'status':'healthy','service':'ultimate-media-search','firebase_mode':FIREBASE_MODE,'timestamp':int(time.time()*1000)}), 200

# ─────────────────────────────────────────────────────────────────────
# 🤖 DeepSeek AI Chat API
# ─────────────────────────────────────────────────────────────────────

@app.route('/api/chat', methods=['POST'])
def chat_with_deepseek():
    try:
        data = request.get_json()
        message = data.get('message', '')
        user_id = data.get('user_id', 'anonymous')
        
        if not DEEPSEEK_API_KEY:
            return jsonify({'error': 'DeepSeek API key not configured'}), 500
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}'
        }
        
        payload = {
            'model': APP_CONFIG['DEEPSEEK_MODEL'],
            'messages': [
                {'role': 'system', 'content': 'You are a helpful assistant for Ultimate Media Search Bot.'},
                {'role': 'user', 'content': message}
            ],
            'stream': False
        }
        
        response = requests.post(
            f"{APP_CONFIG['DEEPSEEK_BASE_URL']}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            reply = result['choices'][0]['message']['content']
            return jsonify({'success': True, 'reply': reply})
        else:
            return jsonify({'error': f'DeepSeek API error: {response.status_code}'}), 500
            
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({'error': str(e)}), 500

# ─────────────────────────────────────────────────────────────────────
# 💳 Payment Routes
# ─────────────────────────────────────────────────────────────────────

@app.route('/api/payment/upi')
def generate_upi_payment():
    """Generate UPI payment link"""
    try:
        amount = request.args.get('amount', 100, type=int)
        plan = request.args.get('plan', 'plan_100')
        user_id = request.args.get('user_id', '')
        
        upi_link = f"upi://pay?pa={APP_CONFIG['UPI_ID']}&pn={APP_CONFIG['UPI_NAME']}&am={amount}&cu=INR&tn=Plan Purchase: {plan} - User: {user_id}"
        
        return jsonify({
            'success': True,
            'upi_link': upi_link,
            'qr_code_url': f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={upi_link}"
        })
    except Exception as e:
        logger.error(f"UPI payment error: {e}")
        return jsonify({'error': str(e)}), 500

# ─────────────────────────────────────────────────────────────────────
# 🤖 Telegram Bot
# ─────────────────────────────────────────────────────────────────────

try:
    import telebot
    from telebot import types
    bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML', threaded=False)
    logger.info("✅ Telegram Bot initialized")
except Exception as e:
    logger.warning(f"⚠️ Bot init warning: {e}")
    bot = None

if bot:
    @bot.message_handler(commands=['start'])
    def handle_start(message):
        try:
            uid = message.from_user.id
            name = message.from_user.first_name or 'User'
            dashboard_url = f"{APP_CONFIG['DASHBOARD_URL']}?id={uid}&name={name}"
            
            welcome_text = f"""
✨ <b>Welcome to UltimateMediaSearchBot!</b> ✨

🇮🇳 <b>India's #1 Destination for Earning & Social Media Growth.</b>

Namaste! 🙏 Aapne sahi jagah kadam rakha hai. Chahe aap extra income kamana chahte ho ya apne brand ki reach badhana, hum aapke saath hain.

━━━━━━━━━━━━━━━━━━━━

💰 <b>EARNING DHAMAKA (Subscription: ₹100)</b>

Ab apne mobile ka sahi istemal karein aur rozana kamayein!

✅ <b>VIP Tasks:</b> High-paying social media tasks unlock karein.
✅ <b>Fast Payout:</b> Apni mehnat ki kamayi turant withdraw karein.
✅ <b>Refer & Earn:</b> Doston ko join karayein aur lifetime 10% commission payein.

<b>Start earning by completing these tasks:</b>
1️⃣ <b>YouTube:</b> <a href="{APP_CONFIG['YOUTUBE']}">Channel Link</a>
2️⃣ <b>Instagram:</b> <a href="{APP_CONFIG['INSTAGRAM']}">Profile Link</a>
3️⃣ <b>Facebook:</b> <a href="{APP_CONFIG['FACEBOOK']}">Official Profile</a>

━━━━━━━━━━━━━━━━━━━━

📢 <b>PROMOTION HUB (Plan: ₹500)</b>

Kya aap apna YouTube, Instagram ya Facebook viral karna chahte hain?

🚀 <b>Real Traffic:</b> Koi bot nahi, sirf asli users.
🚀 <b>Instant Reach:</b> Apne link par dheron likes aur followers payein.
🔗 <b>Join our Network:</b> <a href="{APP_CONFIG['COMMUNITY_LINK']}">UltimateMediaSearch Community</a>

━━━━━━━━━━━━━━━━━━━━

🔥 <b>AAJ KA MOTIVATION</b>

<i>"Zamaana badal raha hai, ab mehnat ke saath-saath smart work karne ka time hai. Aaj ka ₹100 ka chota sa investment aapki kal ki badi kamyabi ban sakta hai. Der mat kijiye!"</i>

━━━━━━━━━━━━━━━━━━━━

👇 <b>Neeche diye gaye buttons par click karke shuru karein!</b>
            """
            
            # ✅ UPDATED BUTTONS - Only 3 Buttons
            markup = types.InlineKeyboardMarkup(row_width=1)
            
            # 1. DeepSeek AI Chat Button
            markup.add(types.InlineKeyboardButton("🤖 DeepSeek AI Chat", url="https://chat.deepseek.com"))
            
            # 2. Buy Plans Buttons (Direct UPI Payment)
            markup.add(
                types.InlineKeyboardButton("⭐ Buy ₹100 Plan", callback_data="buy_100"),
                types.InlineKeyboardButton("🚀 Buy ₹500 Plan", callback_data="buy_500")
            )
            
            # Send Photo + Message
            try:
                img_resp = requests.get(APP_CONFIG['BANNER'], timeout=10)
                bot.send_photo(
                    message.chat.id, 
                    photo=img_resp.content,
                    caption=welcome_text, 
                    reply_markup=markup, 
                    parse_mode="HTML"
                )
                logger.info(f"✅ Photo + Message sent to {uid}")
            except Exception as e:
                logger.error(f"Photo send error: {e}")
                bot.send_message(
                    message.chat.id, 
                    f"🖼️ Image: {APP_CONFIG['BANNER']}\n\n{welcome_text}", 
                    reply_markup=markup, 
                    parse_mode="HTML"
                )
                
        except Exception as e:
            logger.error(f"Start error: {e}")
            bot.send_message(message.chat.id, "⚠️ Error. Try /start again.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
    def handle_buy_plan(call):
        try:
            plan = call.data.split('_')[1]
            amount = 100 if plan == '100' else 500
            user_id = call.from_user.id
            
            # Generate Direct UPI Payment Link
            upi_link = f"upi://pay?pa={APP_CONFIG['UPI_ID']}&pn={APP_CONFIG['UPI_NAME']}&am={amount}&cu=INR&tn=Plan Purchase: {plan} - User: {user_id}"
            
            # Save payment request to Firebase
            payment_data = {
                'user_id': user_id,
                'username': call.from_user.username or 'Unknown',
                'amount': amount,
                'plan': f'plan_{plan}',
                'status': 'pending',
                'timestamp': int(time.time() * 1000),
                'upi_link': upi_link
            }
            
            try:
                db.reference(f'payments/{user_id}/{int(time.time() * 1000)}').set(payment_data)
            except:
                firebase_db.set(f'payments/{user_id}/{int(time.time() * 1000)}', payment_data)
            
            # Send payment message with UPI link
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton("💳 Pay Now via UPI", url=upi_link))
            markup.add(types.InlineKeyboardButton("📞 Contact Admin", url=APP_CONFIG['SUPPORT_LINK']))
            
            plan_name = "₹100 - Earning Booster" if plan == '100' else "₹500 - Promotion Hub"
            
            bot.edit_message_text(
                f"💳 <b>Payment Details</b>\n\n"
                f"Plan: {plan_name}\n"
                f"Amount: ₹{amount}\n\n"
                f"UPI ID: <code>{APP_CONFIG['UPI_ID']}</code>\n\n"
                f"✅ Direct UPI payment link neeche hai:\n"
                f"🔗 <a href='{upi_link}'>Click here to Pay</a>\n\n"
                f"📱 Ya UPI app mein ye ID daalein:\n<code>{APP_CONFIG['UPI_ID']}</code>\n\n"
                f"✅ Payment ke baad screenshot admin ko bhejein.",
                call.message.chat.id, call.message.message_id,
                reply_markup=markup, parse_mode="HTML"
            )
            bot.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Buy plan error: {e}")
            bot.answer_callback_query(call.id, "Error processing payment", show_alert=True)

# ─────────────────────────────────────────────────────────────────────
# 🔗 Webhook
# ─────────────────────────────────────────────────────────────────────

@app.route('/webhook', methods=['POST'])
def webhook():
    if not bot: return 'Bot unavailable', 503
    try:
        update = request.get_json(force=True)
        if update: bot.process_new_updates([types.Update.de_json(update)])
        return '', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': str(e)}), 500

WEBHOOK_SET = False
@app.before_request
def set_webhook_once():
    global WEBHOOK_SET
    if not WEBHOOK_SET and bot and request.path == '/webhook':
        try:
            bot.set_webhook(f"{request.host_url.rstrip('/')}/webhook")
            logger.info(f"✅ Webhook set")
        except: pass
        WEBHOOK_SET = True

@app.errorhandler(404)
def not_found(e): return jsonify({'error':'Not found'}), 404
@app.errorhandler(500)
def server_error(e): 
    logger.error(f"Server error: {e}")
    return jsonify({'error':'Internal server error'}), 500

logger.info(f"✅ Server ready | Firebase: {FIREBASE_MODE}")
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)
