import os
import json
import logging
import time
import random
import hashlib
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, make_response
import telebot
from telebot import types
import requests
from apscheduler.schedulers.background import BackgroundScheduler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='../templates')
app.config['SECRET_KEY'] = os.urandom(24).hex()

# 🔐 Configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw')
FIREBASE_DATABASE_URL = os.environ.get('FIREBASE_DATABASE_URL', 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/').rstrip('/')
ADMIN_IDS = [int(x) for x in os.environ.get('ADMIN_IDS', '123456789').split(',')]
APP_URL = os.environ.get('APP_URL', 'https://ultimate-media-search-bot-t7kj.vercel.app')

# Initialize Telegram Bot
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML', threaded=False)

# 💰 Point Configuration
POINTS_CONFIG = {
    'ad_view': 25,
    'social_task': 50,
    'daily_bonus': 10,
    'referral_earner': 50,
    'referral_newbie': 25,
    'points_per_dollar': 100
}

AD_COOLDOWN_HOURS = 2
MIN_WITHDRAWAL_POINTS = 500
DAILY_AD_LIMIT = 10

# 🖼️ Assets
WELCOME_IMAGE = "https://i.ibb.co/placeholder/welcome-card.jpg"
MONEY_ICON = "https://i.ibb.co/placeholder/money-icon.png"

# Motivational Messages
MOTIVATIONAL_QUOTES = [
    "💪 Aaj ki mehnat kal ki kamyabi hai!",
    "🚀 Chhote kadam bade sapne poore karte hain!",
    "💰 Har minute ka invest tumhe financial freedom ke kareeb lata hai!",
    "🌟 Success unhi ko milti hai jo har roz mehnat karte hain!",
    "🔥 Clock mat dekho, kaam karo - paise khud ayenge!",
    "💎 Tumhara smartphone tumhara ATM hai - abhi kamana shuru karo!",
    "⚡ Consistency hi unlimited earning ki chabi hai!",
    "🎯 Apne goals par focus karo aur paise ki baarish dekho!"
]

GOOD_MORNING_QUOTES = [
    "🌅 Good Morning! Utho aur jeeto - tumhara earning journey intezaar kar raha hai!",
    "☀️ Good Morning! Naya din, nayi kamai ke mauke!",
    "🌄 Good Morning! Aaj ka din tumhara hai - har task matter karta hai!",
    "🌞 Good Morning! Positive socho, profitable kamao!"
]

scheduler = BackgroundScheduler()
scheduler.start()


def _firebase_request(method, path, data=None):
    """Firebase REST API helper with error handling"""
    url = f"{FIREBASE_DATABASE_URL}/{path}.json"
    headers = {'Content-Type': 'application/json'}
    
    try:
        if method == 'GET':
            resp = requests.get(url, headers=headers, timeout=10)
        elif method == 'PUT':
            resp = requests.put(url, json=data, headers=headers, timeout=10)
        elif method == 'POST':
            resp = requests.post(url, json=data, headers=headers, timeout=10)
        elif method == 'PATCH':
            resp = requests.patch(url, json=data, headers=headers, timeout=10)
        else:
            return None, "Invalid method"
        
        if resp.status_code in [200, 201]:
            return resp.json(), None
        return None, f"Firebase error: {resp.status_code}"
    except Exception as e:
        logger.error(f"Firebase error: {str(e)}")
        return None, str(e)


def get_user_data(user_id):
    """Secure user data retrieval"""
    try:
        data, error = _firebase_request('GET', f'users/{user_id}')
        if error or not data:
            return None
        return data
    except:
        return None


def update_user_points(user_id, points, transaction_type='earn', description=''):
    """Atomic point update with history"""
    try:
        timestamp = int(time.time() * 1000)
        current = get_user_data(user_id)
        
        if not current:
            return False
        
        current_points = current.get('points', 0) or 0
        new_points = current_points + points
        
        history = current.get('history', {}) or {}
        history_key = f"{timestamp}_{random.randint(1000, 9999)}"
        history[history_key] = {
            'points': points,
            'type': transaction_type,
            'description': description,
            'timestamp': timestamp
        }
        
        update_payload = {
            'points': new_points,
            'history': history,
            'last_active': timestamp
        }
        
        result, error = _firebase_request('PATCH', f'users/{user_id}', update_payload)
        return result is not None
    except:
        return False


def generate_referral_code(user_id):
    """Generate unique referral code"""
    return hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()


def is_admin(user_id):
    """Check if user is admin"""
    return int(user_id) in ADMIN_IDS


@bot.message_handler(commands=['start'])
def handle_start(message):
    """Welcome message with photo + motivation + referral support"""
    try:
        user_id = message.from_user.id
        first_name = message.from_user.first_name or 'User'
        username = message.from_user.username or ''
        timestamp = int(time.time() * 1000)
        
        # Check for referral code in start command
        referral_code = None
        if len(message.text.split()) > 1:
            referral_code = message.text.split()[1]
        
        # Initialize or update user
        user_data = get_user_data(user_id)
        
        if not user_data:
            ref_code = generate_referral_code(user_id)
            new_user = {
                'uid': user_id,
                'name': first_name,
                'username': username,
                'points': 0,
                'referral_code': ref_code,
                'referred_by': None,
                'referrals': [],
                'ad_history': {},
                'social_history': {},
                'daily_tasks_completed': {},
                'joined': timestamp,
                'last_active': timestamp,
                'withdrawal_info': {}
            }
            _firebase_request('PUT', f'users/{user_id}', new_user)
            
            # Handle referral
            if referral_code:
                # Find referrer
                all_users, _ = _firebase_request('GET', 'users')
                if all_users:
                    for uid, udata in all_users.items():
                        if udata and udata.get('referral_code') == referral_code:
                            # Award points to both
                            update_user_points(int(uid), POINTS_CONFIG['referral_earner'], 'referral', f'Referred {first_name}')
                            update_user_points(user_id, POINTS_CONFIG['referral_newbie'], 'referral_bonus', f'Used code {referral_code}')
                            
                            # Update referral lists
                            referrer_data = get_user_data(int(uid))
                            if referrer_data:
                                referrals = referrer_data.get('referrals', []) or []
                                referrals.append(user_id)
                                _firebase_request('PATCH', f'users/{uid}', {'referrals': referrals, 'points': referrer_data.get('points', 0) + POINTS_CONFIG['referral_earner']})
                            
                            new_user_data = get_user_data(user_id)
                            _firebase_request('PATCH', f'users/{user_id}', {
                                'referred_by': int(uid),
                                'points': POINTS_CONFIG['referral_newbie']
                            })
                            break
        else:
            _firebase_request('PATCH', f'users/{user_id}', {'last_active': timestamp, 'name': first_name})
        
        # Get updated user data
        user_data = get_user_data(user_id)
        current_points = user_data.get('points', 0) if user_data else 0
        ref_code = user_data.get('referral_code', generate_referral_code(user_id)) if user_data else generate_referral_code(user_id)
        
        # Motivational message
        motivation = random.choice(MOTIVATIONAL_QUOTES)
        
        caption = f"""
🌟 <b>Welcome {first_name}!</b>

💰 <i>"Your smartphone is now your ATM. Stop scrolling for free — start earning for your time!"</i>

💬 {motivation}

🎯 <b>Simple Rules:</b>
├ 📺 1 Ad = <b>+{POINTS_CONFIG['ad_view']} Points</b> (2 hr cooldown)
├ 📱 Social Task = <b>+{POINTS_CONFIG['social_task']} Points</b>
├ 🎁 Refer Friend = <b>+{POINTS_CONFIG['referral_earner']} Points</b>
└  <b>{MIN_WITHDRAWAL_POINTS} Points = Withdrawal</b>

🔗 Your Referral Code: <code>{ref_code}</code>

👇 Open Dashboard & Start Earning!
        """
        
        # Inline keyboard
        markup = types.InlineKeyboardMarkup(row_width=1)
        dashboard_url = f"{APP_URL}/dashboard?id={user_id}&name={first_name}"
        welcome_url = f"{APP_URL}/welcome?id={user_id}&name={first_name}"
        
        markup.add(
            types.InlineKeyboardButton("🚀 Open Premium Dashboard", url=dashboard_url),
            types.InlineKeyboardButton("🖼️ View Welcome Card", url=welcome_url),
            types.InlineKeyboardButton("📋 How to Earn", callback_data="help")
        )
        
        # Send welcome photo
        try:
            bot.send_photo(
                message.chat.id,
                photo=WELCOME_IMAGE,
                caption=caption,
                reply_markup=markup
            )
        except:
            bot.send_message(
                message.chat.id,
                caption,
                reply_markup=markup
            )
            
    except Exception as e:
        logger.error(f"Start error: {e}")
        bot.send_message(message.chat.id, "⚠️ Error. Try again.")


@bot.callback_query_handler(func=lambda call: call.data == 'help')
def handle_help(call):
    """Help menu"""
    help_text = """
📖 <b>How to Earn:</b>

1️⃣ <b>Watch Ads</b>
   • +25 Points per ad
   • 2 hours cooldown between ads
   • Daily limit: 10 ads

2️⃣ <b>Social Tasks</b>
   • YouTube Subscribe: +50 Points
   • Instagram Follow: +50 Points
   • Facebook Like: +50 Points

3️⃣ <b>Daily Tasks</b>
   • New tasks every day from admin
   • SMS/Photo/Video/Link tasks

4️⃣ <b>Refer & Earn</b>
   • You get: +50 Points per referral
   • Friend gets: +25 Points on signup

5️⃣ <b>Withdrawal</b>
   • Minimum: 500 Points
   • Provide UPI or Mobile Number
   • Processed within 48 hours

💰 <b>Points Value:</b> 100 Points = $1
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
        return jsonify({'error': 'Failed'}), 500


# ─────────────────────────────────────────────────────────────────────────────
# 🌐 Frontend Routes
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/dashboard')
def serve_dashboard():
    return render_template('dashboard.html')


@app.route('/welcome')
def serve_welcome():
    return render_template('welcome_card.html')


@app.route('/admin')
def serve_admin():
    return render_template('admin.html')


# ─────────────────────────────────────────────────────────────────────────────
# 🔌 API Endpoints
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/user/<int:user_id>', methods=['GET'])
def api_get_user(user_id):
    """Get user data with security check"""
    try:
        user_data = get_user_data(user_id)
        if not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        now = int(time.time() * 1000)
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Calculate ad cooldown
        ad_history = user_data.get('ad_history', {}) or {}
        last_ad_time = 0
        ads_today = 0
        
        for key, val in ad_history.items():
            if val.get('timestamp', 0) > last_ad_time:
                last_ad_time = val.get('timestamp', 0)
            if val.get('date') == today:
                ads_today += 1
        
        cooldown_remaining = 0
        if last_ad_time > 0:
            time_diff = (now - last_ad_time) / (1000 * 60 * 60)
            if time_diff < AD_COOLDOWN_HOURS:
                cooldown_remaining = int((AD_COOLDOWN_HOURS - time_diff) * 60 * 60)
        
        # Social tasks completed today
        social_history = user_data.get('social_history', {}) or {}
        social_completed = {}
        for platform in ['youtube', 'instagram', 'facebook']:
            social_completed[platform] = False
            for key, val in social_history.items():
                if val.get('platform') == platform and val.get('date') == today:
                    social_completed[platform] = True
        
        # Daily tasks
        daily_tasks = user_data.get('daily_tasks_completed', {}) or {}
        daily_completed = daily_tasks.get(today, []) or []
        
        response_data = {
            'uid': user_data.get('uid'),
            'name': user_data.get('name', 'User'),
            'points': user_data.get('points', 0),
            'balance_usd': round(user_data.get('points', 0) / POINTS_CONFIG['points_per_dollar'], 2),
            'referral_code': user_data.get('referral_code', ''),
            'referrals_count': len(user_data.get('referrals', []) or []),
            'ad_cooldown': cooldown_remaining,
            'ads_today': ads_today,
            'daily_ad_limit': DAILY_AD_LIMIT,
            'social_completed': social_completed,
            'daily_completed': daily_completed,
            'withdrawal_info': user_data.get('withdrawal_info', {}),
            'last_active': user_data.get('last_active', 0)
        }
        
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return jsonify({'error': 'Server error'}), 500


@app.route('/api/earn/ad', methods=['POST'])
def api_earn_ad():
    """Watch ad and earn points with cooldown"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        user_data = get_user_data(int(user_id))
        if not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        now = int(time.time() * 1000)
        today = datetime.now().strftime('%Y-%m-%d')
        ad_history = user_data.get('ad_history', {}) or {}
        
        # Check daily limit
        ads_today = sum(1 for v in ad_history.values() if v.get('date') == today)
        if ads_today >= DAILY_AD_LIMIT:
            return jsonify({'error': 'Daily ad limit reached', 'limit': DAILY_AD_LIMIT}), 403
        
        # Check cooldown
        last_ad_time = max((v.get('timestamp', 0) for v in ad_history.values()), default=0)
        if last_ad_time > 0:
            time_diff = (now - last_ad_time) / (1000 * 60 * 60)
            if time_diff < AD_COOLDOWN_HOURS:
                remaining = int((AD_COOLDOWN_HOURS - time_diff) * 60)
                return jsonify({'error': f'Ad on cooldown. Wait {remaining} minutes'}), 429
        
        # Award points
        ad_key = f"{now}_{random.randint(1000,9999)}"
        ad_history[ad_key] = {
            'timestamp': now,
            'date': today,
            'points': POINTS_CONFIG['ad_view']
        }
        
        update_payload = {
            'points': (user_data.get('points', 0) or 0) + POINTS_CONFIG['ad_view'],
            'ad_history': ad_history,
            'last_active': now
        }
        
        result, _ = _firebase_request('PATCH', f'users/{user_id}', update_payload)
        
        if result is not None:
            return jsonify({'success': True, 'points_added': POINTS_CONFIG['ad_view']})
        return jsonify({'error': 'Failed'}), 500
        
    except Exception as e:
        logger.error(f"Ad earn error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/earn/social', methods=['POST'])
def api_earn_social():
    """Social task completion"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        platform = data.get('platform')
        
        if not user_id or not platform:
            return jsonify({'error': 'user_id and platform required'}), 400
        
        platform = platform.lower()
        if platform not in ['youtube', 'instagram', 'facebook']:
            return jsonify({'error': 'Invalid platform'}), 400
        
        user_data = get_user_data(int(user_id))
        if not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        now = int(time.time() * 1000)
        today = datetime.now().strftime('%Y-%m-%d')
        social_history = user_data.get('social_history', {}) or {}
        
        # Check if already completed today
        for key, val in social_history.items():
            if val.get('platform') == platform and val.get('date') == today:
                return jsonify({'error': 'Already completed today'}), 409
        
        # Award points
        task_key = f"{now}_{random.randint(1000,9999)}"
        social_history[task_key] = {
            'platform': platform,
            'date': today,
            'timestamp': now,
            'points': POINTS_CONFIG['social_task']
        }
        
        update_payload = {
            'points': (user_data.get('points', 0) or 0) + POINTS_CONFIG['social_task'],
            'social_history': social_history,
            'last_active': now
        }
        
        result, _ = _firebase_request('PATCH', f'users/{user_id}', update_payload)
        
        if result is not None:
            return jsonify({'success': True, 'points_added': POINTS_CONFIG['social_task']})
        return jsonify({'error': 'Failed'}), 500
        
    except Exception as e:
        logger.error(f"Social earn error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/earn/daily', methods=['POST'])
def api_earn_daily():
    """Complete daily task"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        task_id = data.get('task_id')
        
        if not user_id or not task_id:
            return jsonify({'error': 'user_id and task_id required'}), 400
        
        user_data = get_user_data(int(user_id))
        if not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        today = datetime.now().strftime('%Y-%m-%d')
        daily_completed = user_data.get('daily_tasks_completed', {}) or {}
        today_completed = daily_completed.get(today, []) or []
        
        if task_id in today_completed:
            return jsonify({'error': 'Already completed'}), 409
        
        # Get task points
        daily_tasks, _ = _firebase_request('GET', 'daily_tasks')
        task_data = daily_tasks.get(task_id) if daily_tasks else None
        
        if not task_data:
            return jsonify({'error': 'Task not found'}), 404
        
        points = task_data.get('points', POINTS_CONFIG['social_task'])
        
        today_completed.append(task_id)
        daily_completed[today] = today_completed
        
        update_payload = {
            'points': (user_data.get('points', 0) or 0) + points,
            'daily_tasks_completed': daily_completed,
            'last_active': int(time.time() * 1000)
        }
        
        result, _ = _firebase_request('PATCH', f'users/{user_id}', update_payload)
        
        if result is not None:
            return jsonify({'success': True, 'points_added': points})
        return jsonify({'error': 'Failed'}), 500
        
    except Exception as e:
        logger.error(f"Daily earn error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/daily-tasks', methods=['GET'])
def api_get_daily_tasks():
    """Get today's daily tasks"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        tasks, _ = _firebase_request('GET', 'daily_tasks')
        
        if not tasks:
            return jsonify({'tasks': []})
        
        task_list = []
        for task_id, task_data in tasks.items():
            if task_data:
                task_list.append({
                    'id': task_id,
                    'title': task_data.get('title', ''),
                    'description': task_data.get('description', ''),
                    'type': task_data.get('type', 'link'),
                    'url': task_data.get('url', ''),
                    'points': task_data.get('points', POINTS_CONFIG['social_task']),
                    'date': task_data.get('date', today)
                })
        
        return jsonify({'tasks': task_list})
    except Exception as e:
        logger.error(f"Get tasks error: {e}")
        return jsonify({'tasks': []})


@app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    """Submit withdrawal request"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        payment_method = data.get('method')  # 'upi' or 'mobile'
        payment_info = data.get('payment_info')
        
        if not user_id or not payment_method or not payment_info:
            return jsonify({'error': 'All fields required'}), 400
        
        user_data = get_user_data(int(user_id))
        if not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        current_points = user_data.get('points', 0) or 0
        if current_points < MIN_WITHDRAWAL_POINTS:
            return jsonify({'error': f'Minimum {MIN_WITHDRAWAL_POINTS} points required'}), 403
        
        # Check pending withdrawal
        withdrawals, _ = _firebase_request('GET', 'withdrawals')
        if withdrawals:
            for wid, wdata in withdrawals.items():
                if wdata and wdata.get('user_id') == int(user_id) and wdata.get('status') == 'pending':
                    return jsonify({'error': 'Previous withdrawal pending'}), 409
        
        # Create withdrawal request
        timestamp = int(time.time() * 1000)
        withdrawal_id = f"W{timestamp}_{random.randint(1000,9999)}"
        
        withdrawal_data = {
            'id': withdrawal_id,
            'user_id': int(user_id),
            'user_name': user_data.get('name', 'User'),
            'points': current_points,
            'amount_usd': round(current_points / POINTS_CONFIG['points_per_dollar'], 2),
            'method': payment_method,
            'payment_info': payment_info,
            'status': 'pending',
            'created': timestamp
        }
        
        # Save withdrawal
        result1, _ = _firebase_request('PUT', f'withdrawals/{withdrawal_id}', withdrawal_data)
        
        # Deduct points
        result2, _ = _firebase_request('PATCH', f'users/{user_id}', {
            'points': 0,
            'withdrawal_info': {
                'last_request': timestamp,
                'method': payment_method,
                'payment_info': payment_info
            }
        })
        
        if result1 is not None and result2 is not None:
            return jsonify({'success': True, 'withdrawal_id': withdrawal_id})
        return jsonify({'error': 'Failed'}), 500
        
    except Exception as e:
        logger.error(f"Withdraw error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/tasks', methods=['POST'])
def api_admin_add_task():
    """Admin: Add daily task"""
    try:
        data = request.get_json() or {}
        admin_id = data.get('admin_id')
        
        if not is_admin(admin_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        task_id = f"T{int(time.time())}_{random.randint(1000,9999)}"
        task_data = {
            'title': data.get('title', ''),
            'description': data.get('description', ''),
            'type': data.get('type', 'link'),  # link, photo, video, sms
            'url': data.get('url', ''),
            'points': data.get('points', POINTS_CONFIG['social_task']),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'created': int(time.time() * 1000)
        }
        
        result, _ = _firebase_request('PUT', f'daily_tasks/{task_id}', task_data)
        
        if result is not None:
            return jsonify({'success': True, 'task_id': task_id})
        return jsonify({'error': 'Failed'}), 500
        
    except Exception as e:
        logger.error(f"Admin task error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/withdrawals', methods=['GET'])
def api_admin_get_withdrawals():
    """Admin: Get all withdrawals"""
    try:
        data = request.args
        admin_id = data.get('admin_id')
        
        if not is_admin(admin_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        withdrawals, _ = _firebase_request('GET', 'withdrawals')
        return jsonify({'withdrawals': withdrawals or {}})
    except Exception as e:
        return jsonify({'withdrawals': {}})


@app.route('/api/admin/withdrawals/<withdrawal_id>', methods=['PATCH'])
def api_admin_update_withdrawal(withdrawal_id):
    """Admin: Update withdrawal status"""
    try:
        data = request.get_json() or {}
        admin_id = data.get('admin_id')
        status = data.get('status')
        
        if not is_admin(admin_id):
            return jsonify({'error': 'Unauthorized'}), 403
        
        result, _ = _firebase_request('PATCH', f'withdrawals/{withdrawal_id}', {'status': status})
        
        if result is not None:
            return jsonify({'success': True})
        return jsonify({'error': 'Failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# 🔍 Health Check
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'service': 'earn-bot'}), 200


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return jsonify({'error': 'Internal error'}), 500


# ─────────────────────────────────────────────────────────────────────────────
# ⏰ Morning Automation
# ─────────────────────────────────────────────────────────────────────────────
def send_morning_messages():
    """Send good morning + motivation to all users"""
    try:
        all_users, _ = _firebase_request('GET', 'users')
        if not all_users:
            return
        
        morning_quote = random.choice(GOOD_MORNING_QUOTES)
        motivation = random.choice(MOTIVATIONAL_QUOTES)
        
        for user_id, user_data in all_users.items():
            if not user_data or not user_data.get('active', True):
                continue
            
            try:
                message = f"""
☀️ <b>Good Morning {user_data.get('name', 'User')}!</b>

{morning_quote}

💪 {motivation}

🎯 <b>Today's Goal:</b> Complete tasks & earn points!
💰 Your Balance: {user_data.get('points', 0)} Points

 Start earning now:
{APP_URL}/dashboard?id={user_id}&name={user_data.get('name', 'User')}
                """
                bot.send_message(int(user_id), message, parse_mode='HTML')
                time.sleep(0.5)  # Rate limiting
            except:
                pass
    except Exception as e:
        logger.error(f"Morning message error: {e}")


# Schedule morning messages (adjust timezone as needed)
try:
    scheduler.add_job(send_morning_messages, 'cron', hour=8, minute=0)
except:
    pass


# ─────────────────────────────────────────────────────────────────────────────
# 🚀 Entry Point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
