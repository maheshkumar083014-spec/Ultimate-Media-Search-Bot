import os
import json
import logging
import time
import hashlib
from flask import Flask, request, jsonify, render_template, redirect, url_for
import telebot
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='../templates')

# 🔐 Configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw')
FIREBASE_DATABASE_URL = os.environ.get('FIREBASE_DATABASE_URL', 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/').rstrip('/')
ADMIN_UID = os.environ.get('ADMIN_UID', '0')  # Your Telegram UID as admin
USER_PHOTO_URL = os.environ.get('USER_PHOTO_URL', 'https://i.imgur.com/placeholder.jpg')

# 💰 Monetization & Social Links
AD_SMART_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"
SOCIAL_LINKS = {
    'youtube': 'https://www.youtube.com/@Instagrampost1',
    'instagram': 'https://www.instagram.com/digital_rockstar_m',
    'facebook': 'https://www.facebook.com/profile.php?id=61574378159053'
}
SOCIAL_LOGOS = {
    'youtube': 'https://upload.wikimedia.org/wikipedia/commons/e/ef/Youtube_logo.png',
    'instagram': 'https://upload.wikimedia.org/wikipedia/commons/e/e7/Instagram_logo_2016.svg',
    'facebook': 'https://upload.wikimedia.org/wikipedia/commons/5/51/Facebook_f_logo_%282019%29.svg'
}

# 📊 Point System
POINTS_PER_DOLLAR = 100
AD_POINTS = 25
SOCIAL_POINTS = 100

# Initialize Bot
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML', threaded=False)


def _firebase_request(method, path, data=None):
    """Internal Firebase REST API helper"""
    url = f"{FIREBASE_DATABASE_URL}/{path}.json"
    headers = {'Content-Type': 'application/json'}
    try:
        if method == 'GET':
            resp = requests.get(url, headers=headers, timeout=10)
        elif method == 'PUT':
            resp = requests.put(url, json=data, headers=headers, timeout=10)
        elif method == 'PATCH':
            resp = requests.patch(url, json=data, headers=headers, timeout=10)
        elif method == 'POST':
            resp = requests.post(url, json=data, headers=headers, timeout=10)
        elif method == 'DELETE':
            resp = requests.delete(url, headers=headers, timeout=10)
        else:
            return None, "Invalid method"
        if resp.status_code in [200, 201]:
            return resp.json(), None
        logger.error(f"Firebase {resp.status_code}: {resp.text[:200]}")
        return None, f"Firebase error: {resp.status_code}"
    except Exception as e:
        logger.error(f"Firebase request failed: {e}")
        return None, str(e)


def get_user_data(user_id):
    """Fetch user data from Firebase"""
    data, _ = _firebase_request('GET', f'users/{user_id}')
    return data


def update_user_points(user_id, points, transaction_type='earn'):
    """Update user points with history tracking"""
    current = get_user_data(user_id)
    timestamp = int(time.time() * 1000)
    
    if not current:
        new_user = {
            'uid': user_id, 'points': points,
            'history': {f"{timestamp}": {'points': points, 'type': transaction_type, 'timestamp': timestamp}},
            'joined': timestamp, 'last_active': timestamp
        }
        result, _ = _firebase_request('PUT', f'users/{user_id}', new_user)
        return result is not None
    
    current_points = current.get('points', 0) or 0
    history = current.get('history', {}) or {}
    history[f"{timestamp}"] = {'points': points, 'type': transaction_type, 'timestamp': timestamp}
    
    update_payload = {'points': current_points + points, 'history': history, 'last_active': timestamp}
    result, _ = _firebase_request('PATCH', f'users/{user_id}', update_payload)
    return result is not None


def get_all_users():
    """Admin: Fetch all users"""
    data, _ = _firebase_request('GET', 'users')
    return data if data else {}


def get_admin_tasks():
    """Fetch active admin-created tasks"""
    data, _ = _firebase_request('GET', 'admin_tasks')
    return data if data else {}


def create_admin_task(title, description, reward, link, task_type='custom'):
    """Admin: Create a new task"""
    timestamp = int(time.time() * 1000)
    task_id = hashlib.md5(f"{title}{timestamp}".encode()).hexdigest()[:12]
    task = {
        'id': task_id, 'title': title, 'description': description,
        'reward': reward, 'link': link, 'type': task_type,
        'active': True, 'created': timestamp, 'completions': 0
    }
    result, _ = _firebase_request('PUT', f'admin_tasks/{task_id}', task)
    return result is not None


@bot.message_handler(commands=['start'])
def handle_start(message):
    """Professional /start with photo & elegant welcome"""
    try:
        user_id = message.from_user.id
        first_name = message.from_user.first_name or 'Valued User'
        username = message.from_user.username or ''
        
        # Initialize user
        user_data = get_user_data(user_id)
        timestamp = int(time.time() * 1000)
        
        if not user_data:
            new_user = {
                'uid': user_id, 'name': first_name, 'username': username,
                'points': 0, 'photo_seen': False,
                'joined': timestamp, 'last_active': timestamp
            }
            _firebase_request('PUT', f'users/{user_id}', new_user)
        else:
            _firebase_request('PATCH', f'users/{user_id}', {'last_active': timestamp})
        
        # Dashboard URL
        dashboard_url = f"https://ultimate-media-search-bot-t7kj.vercel.app/dashboard?id={user_id}&name={first_name}"
        
        # Professional Welcome Message with Photo
        welcome_photo = USER_PHOTO_URL  # Your photo URL from env
        
        welcome_caption = f"""
✨ <b>Welcome to Ultimate Media Search</b> ✨

👤 Hello <b>{first_name}</b>!

🎯 <b>Your Earning Journey Starts Now</b>

💎 <b>Reward Structure:</b>
├ 📺 Watch Ads → +{AD_POINTS} Points
├ 📱 Social Tasks → +{SOCIAL_POINTS} Points  
├ 🎁 Custom Tasks → Variable Rewards
└ 💰 <b>100 Points = $1.00 USD</b>

🔐 Secure • Instant • Trusted

👇 Tap below to access your premium dashboard
        """
        
        # Inline Keyboard
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        dashboard_btn = telebot.types.InlineKeyboardButton("🚀 Open Premium Dashboard", url=dashboard_url)
        help_btn = telebot.types.InlineKeyboardButton("❓ How It Works", callback_data='help')
        markup.add(dashboard_btn, help_btn)
        
        # Send photo with caption
        try:
            bot.send_photo(message.chat.id, photo=welcome_photo, caption=welcome_caption, 
                          reply_markup=markup, parse_mode='HTML')
        except:
            # Fallback if photo fails
            bot.send_message(message.chat.id, welcome_caption, reply_markup=markup, parse_mode='HTML')
            bot.send_photo(message.chat.id, photo=welcome_photo)
        
    except Exception as e:
        logger.error(f"Start error: {e}")
        bot.send_message(message.chat.id, "⚠️ Welcome! Please try opening your dashboard again.", parse_mode='HTML')


@bot.message_handler(commands=['admin'])
def handle_admin(message):
    """Admin panel access via Telegram"""
    user_id = message.from_user.id
    if str(user_id) != ADMIN_UID:
        bot.send_message(message.chat.id, "🔐 Admin access denied.", parse_mode='HTML')
        return
    
    admin_url = f"https://ultimate-media-search-bot-t7kj.vercel.app/admin?token={hashlib.md5(f'{ADMIN_UID}{BOT_TOKEN}'.encode()).hexdigest()}"
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🎛️ Open Admin Panel", url=admin_url))
    
    bot.send_message(message.chat.id, f"👑 <b>Admin Panel</b>\n\nManage tasks, users & analytics:", 
                    reply_markup=markup, parse_mode='HTML')


@bot.callback_query_handler(func=lambda call: call.data == 'help')
def handle_help(call):
    """Help callback"""
    help_text = """
📚 <b>How to Earn:</b>

1️⃣ <b>Watch Ads</b>
   • Click "Watch Ad" button
   • Wait 30 seconds
   • Earn +25 Points instantly

2️⃣ <b>Social Tasks</b>  
   • Follow our social accounts
   • YouTube • Instagram • Facebook
   • Earn +100 Points per platform

3️⃣ <b>Custom Tasks</b>
   • Check dashboard for special offers
   • Rewards vary by task complexity

💰 <b>Withdrawal:</b>
• Minimum: 100 Points ($1.00)
• Payouts via Telegram/UPI/PayPal
• Processing: 24-48 hours

❓ Need help? Contact @SupportBot
    """
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, help_text, parse_mode='HTML')


# ─────────────────────────────────────────────────────────────────────────────
# 🔗 Webhook Handler
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    try:
        update = request.get_json(force=True)
        if update:
            bot.process_new_updates([telebot.types.Update.de_json(update)])
        return '', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': 'Webhook failed'}), 500


# ─────────────────────────────────────────────────────────────────────────────
# 🌐 Frontend Routes
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/dashboard')
def serve_dashboard():
    return render_template('dashboard.html', 
                          photo_url=USER_PHOTO_URL,
                          social_links=SOCIAL_LINKS,
                          social_logos=SOCIAL_LOGOS)


@app.route('/admin')
def serve_admin():
    token = request.args.get('token')
    expected_token = hashlib.md5(f'{ADMIN_UID}{BOT_TOKEN}'.encode()).hexdigest()
    if token != expected_token:
        return jsonify({'error': 'Unauthorized'}), 401
    return render_template('admin.html', admin_uid=ADMIN_UID)


# ─────────────────────────────────────────────────────────────────────────────
# 🔌 API Endpoints
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/user/<int:user_id>', methods=['GET'])
def api_get_user(user_id):
    try:
        user_data = get_user_data(user_id)
        if user_data:
            user_data['balance_usd'] = (user_data.get('points', 0) or 0) / POINTS_PER_DOLLAR
            user_data['photo_url'] = USER_PHOTO_URL
            return jsonify(user_data)
        return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return jsonify({'error': 'Internal error'}), 500


@app.route('/api/earn/ad', methods=['POST'])
def api_earn_ad():
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        if update_user_points(int(user_id), AD_POINTS, 'ad_view'):
            return jsonify({'success': True, 'points_added': AD_POINTS})
        return jsonify({'error': 'Update failed'}), 500
    except Exception as e:
        logger.error(f"Ad earn error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/earn/social', methods=['POST'])
def api_earn_social():
    try:
        data = request.get_json() or {}
        user_id, task = data.get('user_id'), data.get('task')
        if not user_id or not task:
            return jsonify({'error': 'user_id and task required'}), 400
        if update_user_points(int(user_id), SOCIAL_POINTS, f'social_{task}'):
            return jsonify({'success': True, 'points_added': SOCIAL_POINTS})
        return jsonify({'error': 'Update failed'}), 500
    except Exception as e:
        logger.error(f"Social earn error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/tasks', methods=['GET', 'POST'])
def api_admin_tasks():
    """Admin: Manage custom tasks"""
    token = request.headers.get('X-Admin-Token')
    expected = hashlib.md5(f'{ADMIN_UID}{BOT_TOKEN}'.encode()).hexdigest()
    if token != expected:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if request.method == 'GET':
        tasks = get_admin_tasks()
        return jsonify({'tasks': tasks})
    
    elif request.method == 'POST':
        data = request.get_json() or {}
        required = ['title', 'description', 'reward', 'link']
        if not all(k in data for k in required):
            return jsonify({'error': 'Missing fields'}), 400
        if create_admin_task(data['title'], data['description'], int(data['reward']), data['link'], data.get('type','custom')):
            return jsonify({'success': True})
        return jsonify({'error': 'Creation failed'}), 500


@app.route('/api/admin/users', methods=['GET'])
def api_admin_users():
    """Admin: Get all users"""
    token = request.headers.get('X-Admin-Token')
    expected = hashlib.md5(f'{ADMIN_UID}{BOT_TOKEN}'.encode()).hexdigest()
    if token != expected:
        return jsonify({'error': 'Unauthorized'}), 401
    
    users = get_all_users()
    # Transform for admin view
    user_list = []
    for uid, data in users.items():
        if data:
            user_list.append({
                'uid': uid,
                'name': data.get('name','Unknown'),
                'points': data.get('points',0),
                'joined': data.get('joined',0),
                'last_active': data.get('last_active',0)
            })
    return jsonify({'users': user_list})


# ─────────────────────────────────────────────────────────────────────────────
# 🔍 Health & Errors
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/health')
def health_check():
    return jsonify({'status':'healthy','service':'ultimate-media-search-bot'}), 200

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error':'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return jsonify({'error':'Internal server error'}), 500


# ─────────────────────────────────────────────────────────────────────────────
# 🚀 Entry Point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
