"""
🤖 Ultimate Media Search Bot - Production Ready
✅ Fixed: Payment Error Logic
✅ UPI Direct Payment Integration
✅ DeepSeek AI Chat API
✅ Full Admin Panel Control
✅ Firebase REST Fallback (No Crash)
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
import requests
from flask import Flask, request, jsonify, render_template

# ─────────────────────────────────────────────────────────────────────
# 🔧 Logging & Setup
# ─────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)
logger.info("🚀 Starting Ultimate Media Search Bot v3.1 (Fixed Payment)...")

# ─────────────────────────────────────────────────────────────────────
# 🔐 Utils
# ─────────────────────────────────────────────────────────────────────
def validate_input(data: str, max_len: int = 1000) -> str:
    return ''.join(c for c in str(data) if ord(c) < 128)[:max_len].strip() if data else ''

# ─────────────────────────────────────────────────────────────────────
# 🗄️ Firebase Init & REST Fallback
# ─────────────────────────────────────────────────────────────────────
def parse_firebase_creds(env_val: str) -> Optional[Dict]:
    if not env_val or env_val == 'skip': return None
    try:
        creds = json.loads(env_val) if isinstance(env_val, str) else env_val
        key = creds.get('private_key', '')
        if key and '-----BEGIN PRIVATE KEY-----' not in key:
            key = key.replace('\\\\n', '\n').replace('\\n', '\n')
            if not key.startswith('-----BEGIN'): key = '-----BEGIN PRIVATE KEY-----\n' + key.strip()
            if not key.endswith('-----END PRIVATE KEY-----'): key = key.strip() + '\n-----END PRIVATE KEY-----\n'
            creds['private_key'] = key
        return creds
    except Exception as e:
        logger.error(f"❌ Firebase creds parse failed: {e}")
        return None

FIREBASE_MODE = 'unknown'
db = None
firebase_db = None

def init_firebase() -> bool:
    global FIREBASE_MODE, db, firebase_db
    try:
        import firebase_admin
        from firebase_admin import credentials
        
        if firebase_admin._apps: 
            FIREBASE_MODE = 'admin'
            from firebase_admin import db as fb_db
            db = fb_db
            return True
            
        db_url = os.environ.get('FIREBASE_DB_URL', 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/').rstrip('/')
        sa = parse_firebase_creds(os.environ.get('FIREBASE_SERVICE_ACCOUNT', 'skip'))
        
        if not sa:
            logger.warning("⚠️ No service account, using REST fallback")
            FIREBASE_MODE = 'rest'
            return False
            
        firebase_admin.initialize_app(credentials.Certificate(sa), {'databaseURL': db_url, 'projectId': sa.get('project_id')})
        from firebase_admin import db as fb_db
        db = fb_db
        FIREBASE_MODE = 'admin'
        logger.info("✅ Firebase Admin SDK initialized")
        return True
    except ImportError:
        logger.warning("⚠️ firebase-admin missing, using REST")
        FIREBASE_MODE = 'rest'
        return False
    except Exception as e:
        logger.error(f"❌ Firebase init failed: {e}")
        FIREBASE_MODE = 'rest'
        return False

init_firebase()

# REST Fallback Class
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

if FIREBASE_MODE == 'rest':
    firebase_db = FirebaseREST(os.environ.get('FIREBASE_DB_URL', 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'))

def get_user(tid): return firebase_db.get(f'users/{tid}') if FIREBASE_MODE == 'rest' else db.reference(f'users/{tid}').get()
def set_user(tid, d): return firebase_db.set(f'users/{tid}', d) if FIREBASE_MODE == 'rest' else db.reference(f'users/{tid}').set(d)
def update_user(tid, d): return firebase_db.update(f'users/{tid}', d) if FIREBASE_MODE == 'rest' else db.reference(f'users/{tid}').update(d)

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
# Vercel safe template path
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'templates')
app = Flask(__name__, template_folder=template_dir)
app.config['SECRET_KEY'] = os.urandom(32).hex()
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# ─────────────────────────────────────────────────────────────────────
# 🌐 Routes
# ─────────────────────────────────────────────────────────────────────
@app.route('/')
def root():
    return f'''<html><body style="background:#1a202c;color:#fff;text-align:center;padding:40px;font-family:sans-serif">
    <h1>🤖 Ultimate Media Search Bot</h1><p style="color:#94a3b8;margin:20px 0">Server running! ✅</p>
    <a href="{APP_CONFIG['DASHBOARD_URL']}?id=123&name=Test" style="display:inline-block;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;padding:14px 32px;border-radius:12px;text-decoration:none;font-weight:600">🚀 Open Dashboard</a>
    <p style="margin-top:30px;font-size:0.9rem;color:#64748b">Firebase: {FIREBASE_MODE}</p></body></html>'''

@app.route('/dashboard')
def dashboard():
    tid = validate_input(request.args.get('id', '123'), 50)
    name = validate_input(request.args.get('name', 'User'), 100)
    try:
        if not get_user(tid):
            set_user(tid, {'uid':tid,'name':name,'username':name,'points':0,'total_earned':0,'ad_views':0,'tasks_completed':0,'joined_at':int(time.time()*1000),'last_active':int(time.time()*1000),'referral_code':'UMS'+str(tid)[-6:].upper(),'plan':'free'})
    except Exception as e: logger.error(f"User creation error: {e}")
    return render_template('dashboard.html', firebase_config=json.dumps(FIREBASE_CONFIG), app_config=json.dumps(APP_CONFIG))

@app.route('/admin')
def admin_panel():
    return render_template('admin.html', firebase_config=json.dumps(FIREBASE_CONFIG), admin_key=request.args.get('key', ADMIN_KEY))

@app.route('/health')
def health():
    return jsonify({'status':'healthy','service':'ultimate-media-search','firebase_mode':FIREBASE_MODE,'timestamp':int(time.time()*1000)}), 200

# ─────────────────────────────────────────────────────────────────────
# 🤖 DeepSeek Chat API
# ─────────────────────────────────────────────────────────────────────
@app.route('/api/chat', methods=['POST'])
def chat_with_deepseek():
    try:
        data = request.get_json() or {}
        message = data.get('message', '')
        if not DEEPSEEK_API_KEY:
            return jsonify({'error': 'DeepSeek API key not configured'}), 500
        
        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {DEEPSEEK_API_KEY}'}
        payload = {
            'model': APP_CONFIG['DEEPSEEK_MODEL'],
            'messages': [
                {'role': 'system', 'content': 'You are a helpful assistant for Ultimate Media Search Bot.'},
                {'role': 'user', 'content': message}
            ],
            'stream': False
        }
        
        resp = requests.post(f"{APP_CONFIG['DEEPSEEK_BASE_URL']}/v1/chat/completions", headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            return jsonify({'success': True, 'reply': resp.json()['choices'][0]['message']['content']})
        return jsonify({'error': f'API error: {resp.status_code}'}), 500
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({'error': str(e)}), 500

# ─────────────────────────────────────────────────────────────────────
# 💳 UPI Payment API
# ─────────────────────────────────────────────────────────────────────
@app.route('/api/payment/upi')
def generate_upi_payment():
    try:
        amount = request.args.get('amount', 100, type=int)
        plan = request.args.get('plan', 'plan_100')
        user_id = request.args.get('user_id', '')
        upi_link = f"upi://pay?pa={APP_CONFIG['UPI_ID']}&pn={APP_CONFIG['UPI_NAME']}&am={amount}&cu=INR&tn=Plan:{plan}-User:{user_id}"
        return jsonify({'success': True, 'upi_link': upi_link, 'qr_url': f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={upi_link}"})
    except Exception as e:
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
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton("🤖 DeepSeek AI Chat", url="https://chat.deepseek.com"))
            markup.add(
                types.InlineKeyboardButton("⭐ Buy ₹100 Plan", callback_data="buy_100"),
                types.InlineKeyboardButton("🚀 Buy ₹500 Plan", callback_data="buy_500")
            )
            
            try:
                img_resp = requests.get(APP_CONFIG['BANNER'], timeout=10)
                bot.send_photo(message.chat.id, photo=img_resp.content, caption=welcome_text, reply_markup=markup, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Photo send error: {e}")
                bot.send_message(message.chat.id, f"🖼️ Image: {APP_CONFIG['BANNER']}\n\n{welcome_text}", reply_markup=markup, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Start error: {e}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
    def handle_buy_plan(call):
        try:
            plan = call.data.split('_')[1]
            amount = 100 if plan == '100' else 500
            user_id = call.from_user.id
            username = call.from_user.username or 'Unknown'
            
            # Generate Direct UPI Link
            upi_link = f"upi://pay?pa={APP_CONFIG['UPI_ID']}&pn={APP_CONFIG['UPI_NAME']}&am={amount}&cu=INR&tn=Plan:{plan}-User:{user_id}"
            
            # Prepare Data
            payment_data = {
                'user_id': user_id,
                'username': username,
                'amount': amount,
                'plan': f'plan_{plan}',
                'status': 'pending',
                'timestamp': int(time.time() * 1000),
                'upi_link': upi_link
            }
            
            # ✅ FIXED: Safe Database Save
            # This block will NOT crash the bot if DB fails.
            try:
                if FIREBASE_MODE == 'admin' and db is not None:
                    db.reference(f'payments/{user_id}/{int(time.time() * 1000)}').set(payment_data)
                elif FIREBASE_MODE == 'rest' and firebase_db is not None:
                    firebase_db.set(f'payments/{user_id}/{int(time.time() * 1000)}', payment_data)
                logger.info(f"✅ Payment request saved for user {user_id}")
            except Exception as db_err:
                # Log error but continue - User MUST get the link
                logger.error(f"⚠️ DB Save Warning (Ignoring): {db_err}")
            
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
            # Fallback message in case of total crash
            bot.answer_callback_query(call.id, "Error processing payment", show_alert=True)

# ─────────────────────────────────────────────────────────────────────
# 🔗 Webhook & Error Handlers
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
