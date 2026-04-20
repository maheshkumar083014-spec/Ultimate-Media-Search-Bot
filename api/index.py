import os
import json
import logging
import time
import hashlib
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, redirect
import telebot
from telebot import types
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='../templates')

# 🔐 Configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw')
FIREBASE_URL = os.environ.get('FIREBASE_DATABASE_URL', 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/').rstrip('/')
ADMIN_ID = os.environ.get('ADMIN_ID', '0')

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML', threaded=False)

# 💰 Configuration
POINTS_PER_AD = 25
POINTS_PER_SOCIAL = 50
POINTS_PER_REFERRAL_OWNER = 50
POINTS_PER_REFERRAL_NEW = 25
AD_COOLDOWN_HOURS = 2
MIN_WITHDRAWAL_POINTS = 500
WITHDRAWAL_RATE = 10  # 10 points = $1

# Welcome Image URL (Money/Cash photo)
WELCOME_MONEY_IMAGE = "https://i.ibb.co/placeholder/money-welcome.jpg"
ADMIN_PHOTO_URL = "https://i.ibb.co/placeholder/admin-photo.jpg"  # Your photo

def _firebase_request(method, path, data=None):
    """Firebase REST API helper"""
    url = f"{FIREBASE_URL}/{path}.json"
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
        logger.error(f"Firebase error: {e}")
        return None, str(e)

def get_user(user_id):
    """Get user data"""
    data, _ = _firebase_request('GET', f'users/{user_id}')
    return data

def update_user(user_id, data):
    """Update user data"""
    result, _ = _firebase_request('PATCH', f'users/{user_id}', data)
    return result is not None

def create_user(user_id, first_name, username=None, referral_code=None):
    """Create new user with referral system"""
    timestamp = int(time.time() * 1000)
    
    # Generate unique referral code
    user_ref_code = hashlib.md5(f"{user_id}{timestamp}".encode()).hexdigest()[:8].upper()
    
    user_data = {
        'uid': user_id,
        'name': first_name,
        'username': username or '',
        'points': 0,
        'earnings': 0.0,
        'referrals': 0,
        'referral_code': user_ref_code,
        'referred_by': None,
        'joined': timestamp,
        'last_active': timestamp,
        'last_ad_time': 0,
        'daily_tasks_completed': 0,
        'last_task_date': '',
        'social_tasks': {
            'youtube': False,
            'instagram': False,
            'facebook': False
        },
        'withdrawal_info': {
            'mobile': '',
            'upi': '',
            'status': 'not_set'
        }
    }
    
    # Handle referral
    if referral_code:
        # Find referrer
        users_ref, _ = _firebase_request('GET', 'users')
        if users_ref:
            for uid, udata in users_ref.items():
                if udata.get('referral_code') == referral_code.upper():
                    # Award points to referrer
                    referrer_points = udata.get('points', 0) + POINTS_PER_REFERRAL_OWNER
                    _firebase_request('PATCH', f'users/{uid}', {
                        'points': referrer_points,
                        'referrals': udata.get('referrals', 0) + 1
                    })
                    # Award points to new user
                    user_data['points'] = POINTS_PER_REFERRAL_NEW
                    user_data['referred_by'] = uid
                    break
    
    result, _ = _firebase_request('PUT', f'users/{user_id}', user_data)
    return result is not None

def can_watch_ad(user_id):
    """Check if user can watch ad (2 hour cooldown)"""
    user = get_user(user_id)
    if not user:
        return True, 0
    
    last_ad_time = user.get('last_ad_time', 0)
    if last_ad_time == 0:
        return True, 0
    
    cooldown_seconds = AD_COOLDOWN_HOURS * 3600
    time_passed = time.time() - (last_ad_time / 1000)
    remaining = cooldown_seconds - time_passed
    
    if remaining <= 0:
        return True, 0
    return False, int(remaining / 60)  # Return remaining minutes

def award_points(user_id, points, task_type):
    """Award points to user"""
    user = get_user(user_id)
    if not user:
        return False
    
    current_points = user.get('points', 0)
    earnings = (current_points + points) / WITHDRAWAL_RATE
    
    timestamp = int(time.time() * 1000)
    history = user.get('history', {})
    history[f"{timestamp}"] = {
        'points': points,
        'type': task_type,
        'timestamp': timestamp
    }
    
    update_data = {
        'points': current_points + points,
        'earnings': earnings,
        'history': history,
        'last_active': timestamp
    }
    
    if task_type == 'ad':
        update_data['last_ad_time'] = timestamp
    
    return update_user(user_id, update_data)

def get_daily_tasks():
    """Get daily tasks from admin"""
    tasks, _ = _firebase_request('GET', 'daily_tasks')
    return tasks if tasks else {}

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Handle /start with welcome card"""
    try:
        user_id = message.from_user.id
        first_name = message.from_user.first_name or 'User'
        username = message.from_user.username or ''
        
        # Extract referral code if present
        referral_code = None
        if len(message.text.split()) > 1:
            referral_code = message.text.split()[1]
        
        # Create or update user
        user = get_user(user_id)
        if not user:
            create_user(user_id, first_name, username, referral_code)
            user = get_user(user_id)
        else:
            update_user(user_id, {'last_active': int(time.time() * 1000), 'name': first_name})
        
        # Welcome message with money image
        caption = f"""
💰 <b>Welcome to EarnFlow, {first_name}!</b> 💰

 <i>"Your smartphone is now your ATM. Stop scrolling for free—start earning for your time!"</i> 💎

📊 <b>Your ID:</b> <code>{user_id}</code>
🎁 <b>Referral Code:</b> <code>{user.get('referral_code', 'N/A')}</code>

🎯 <b>Simple Rules:</b>
├ 📺 Watch Ad → +{POINTS_PER_AD} Points (Every {AD_COOLDOWN_HOURS} hours)
├ 📱 Social Tasks → +{POINTS_PER_SOCIAL} Points Each
├ 👥 Refer Friend → +{POINTS_PER_REFERRAL_OWNER} Points
└ 💵 {WITHDRAWAL_RATE} Points = $1.00

💰 <b>Withdraw at {MIN_WITHDRAWAL_POINTS} points = ${MIN_WITHDRAWAL_POINTS//WITHDRAWAL_RATE}!</b>

👇 Tap below to start earning NOW!
        """
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        dashboard_url = f"https://your-app.vercel.app/dashboard?id={user_id}&name={first_name}"
        markup.add(
            types.InlineKeyboardButton("🚀 Open Dashboard & Start Earning", url=dashboard_url),
            types.InlineKeyboardButton("📋 How to Earn", callback_data="how_to_earn")
        )
        
        try:
            bot.send_photo(
                message.chat.id,
                photo=WELCOME_MONEY_IMAGE,
                caption=caption,
                reply_markup=markup
            )
        except:
            bot.send_message(message.chat.id, caption, reply_markup=markup)
        
        # Send daily good morning if it's morning time
        send_morning_motivation(user_id, first_name)
        
    except Exception as e:
        logger.error(f"Start error: {e}")
        bot.send_message(message.chat.id, "⚠️ Something went wrong. Try /start again.")

def send_morning_motivation(user_id, name):
    """Send morning motivation message"""
    current_hour = datetime.now().hour
    if 6 <= current_hour <= 10:  # Morning time
        motivations = [
            "🌅 Good Morning! Today is your day to earn big! 💪",
            "☀️ Rise and shine! Your earning journey starts now! 🚀",
            "🌄 Morning! Every ad you watch brings you closer to your goals! 💰"
        ]
        import random
        bot.send_message(user_id, f"{random.choice(motivations)}\n\nOpen your dashboard to claim daily tasks! ")

@bot.callback_query_handler(func=lambda call: call.data == "how_to_earn")
def handle_how_to_earn(call):
    """Show earning instructions"""
    text = """
📚 <b>How to Earn on EarnFlow:</b>

1️⃣ <b>Watch Ads</b> 📺
   • Earn {ad_points} points per ad
   • Available every {cooldown} hours
   • Watch for 30 seconds

2️⃣ <b>Social Tasks</b> 📱
   • YouTube Subscribe: {social_points} pts
   • Instagram Follow: {social_points} pts
   • Facebook Like: {social_points} pts

3️⃣ <b>Daily Tasks</b> 🎁
   • New tasks every morning
   • Good morning motivation
   • Extra earning opportunities

4️⃣ <b>Refer & Earn</b> 👥
   • You get: {ref_owner} points
   • Friend gets: {ref_new} points
   • Share your unique code

💵 <b>Withdrawal:</b>
   • Minimum: {min_pts} points (${min_usd})
   • 10 Points = $1.00
   • Add UPI/Mobile in dashboard

Start earning now! 🚀
    """.format(
        ad_points=POINTS_PER_AD,
        cooldown=AD_COOLDOWN_HOURS,
        social_points=POINTS_PER_SOCIAL,
        ref_owner=POINTS_PER_REFERRAL_OWNER,
        ref_new=POINTS_PER_REFERRAL_NEW,
        min_pts=MIN_WITHDRAWAL_POINTS,
        min_usd=MIN_WITHDRAWAL_POINTS//WITHDRAWAL_RATE
    )
    bot.answer_callback_query(call.id, "Earning Guide Sent!")
    bot.send_message(call.message.chat.id, text)

# ─────────────────────────────────────────────────────────────────────────────
# 🔗 Webhook Handler
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Receive Telegram webhook updates"""
    try:
        update = request.get_json(force=True)
        if update:
            bot.process_new_updates([types.Update.de_json(update)])
        return '', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': 'Webhook failed'}), 500

# ─────────────────────────────────────────────────────────────────────────────
# 🌐 Frontend Routes
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/dashboard')
def serve_dashboard():
    """Serve user dashboard"""
    return render_template('dashboard.html')

@app.route('/admin')
def serve_admin():
    """Serve admin panel"""
    admin_id = request.args.get('admin_id')
    if admin_id != ADMIN_ID:
        return "<h1>Unauthorized</h1>", 403
    return render_template('admin.html')

# ─────────────────────────────────────────────────────────────────────────────
# 🔌 API Endpoints
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/user/<int:user_id>', methods=['GET'])
def api_get_user(user_id):
    """Get user data"""
    try:
        user = get_user(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Calculate withdrawal eligibility
        user['can_withdraw'] = user.get('points', 0) >= MIN_WITHDRAWAL_POINTS
        user['withdrawal_amount'] = user.get('points', 0) / WITHDRAWAL_RATE
        
        # Check ad availability
        can_ad, remaining_mins = can_watch_ad(user_id)
        user['can_watch_ad'] = can_ad
        user['ad_cooldown_mins'] = remaining_mins
        
        return jsonify(user)
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/earn/ad', methods=['POST'])
def api_earn_ad():
    """Award points for ad view"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        can_watch, remaining = can_watch_ad(int(user_id))
        if not can_watch:
            return jsonify({
                'error': f'Ad on cooldown. Try after {remaining} minutes',
                'cooldown': remaining
            }), 429
        
        if award_points(int(user_id), POINTS_PER_AD, 'ad'):
            return jsonify({
                'success': True,
                'points_added': POINTS_PER_AD,
                'next_ad_in': AD_COOLDOWN_HOURS * 60  # minutes
            })
        return jsonify({'error': 'Failed to award points'}), 500
    except Exception as e:
        logger.error(f"Ad earn error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/earn/social', methods=['POST'])
def api_earn_social():
    """Award points for social task"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        platform = data.get('platform')  # youtube, instagram, facebook
        
        if not user_id or not platform:
            return jsonify({'error': 'user_id and platform required'}), 400
        
        user = get_user(int(user_id))
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if already completed
        social_tasks = user.get('social_tasks', {})
        if social_tasks.get(platform):
            return jsonify({'error': 'Already completed', 'claimed': True}), 400
        
        # Award points
        if award_points(int(user_id), POINTS_PER_SOCIAL, f'social_{platform}'):
            # Mark as completed
            social_tasks[platform] = True
            update_user(int(user_id), {'social_tasks': social_tasks})
            return jsonify({
                'success': True,
                'points_added': POINTS_PER_SOCIAL
            })
        return jsonify({'error': 'Failed to award points'}), 500
    except Exception as e:
        logger.error(f"Social earn error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    """Handle withdrawal request"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        mobile = data.get('mobile')
        upi = data.get('upi')
        
        if not all([user_id, mobile, upi]):
            return jsonify({'error': 'All fields required'}), 400
        
        user = get_user(int(user_id))
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        points = user.get('points', 0)
        if points < MIN_WITHDRAWAL_POINTS:
            return jsonify({
                'error': f'Minimum {MIN_WITHDRAWAL_POINTS} points required',
                'current': points
            }), 400
        
        # Save withdrawal info
        withdrawal_info = {
            'mobile': mobile,
            'upi': upi,
            'status': 'pending',
            'requested_at': int(time.time() * 1000),
            'amount': points / WITHDRAWAL_RATE,
            'points': points
        }
        
        update_user(int(user_id), {
            'withdrawal_info': withdrawal_info,
            'points': 0,  # Deduct points
            'earnings': 0
        })
        
        # Notify admin
        admin_text = f"""
💰 <b>New Withdrawal Request!</b>

👤 User: {user.get('name')} ({user_id})
📱 Mobile: {mobile}
💳 UPI: {upi}
💵 Amount: ${withdrawal_info['amount']}
🎯 Points: {points}

Process this withdrawal ASAP! ✅
        """
        try:
            bot.send_message(ADMIN_ID, admin_text)
        except:
            pass
        
        return jsonify({
            'success': True,
            'message': 'Withdrawal request submitted!'
        })
    except Exception as e:
        logger.error(f"Withdrawal error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/daily-tasks', methods=['GET'])
def api_get_daily_tasks():
    """Get daily tasks"""
    try:
        tasks = get_daily_tasks()
        return jsonify(tasks)
    except Exception as e:
        logger.error(f"Get tasks error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/referral/<int:user_id>', methods=['GET'])
def api_get_referral(user_id):
    """Get referral stats"""
    try:
        user = get_user(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'referral_code': user.get('referral_code'),
            'total_referrals': user.get('referrals', 0),
            'referral_link': f"https://t.me/your_bot_username?start={user.get('referral_code')}"
        })
    except Exception as e:
        logger.error(f"Referral error: {e}")
        return jsonify({'error': str(e)}), 500

# ─────────────────────────────────────────────────────────────────────────────
# 🔧 Admin API
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/admin/add-task', methods=['POST'])
def api_add_task():
    """Admin: Add daily task"""
    try:
        data = request.get_json() or {}
        admin_id = data.get('admin_id')
        
        if str(admin_id) != ADMIN_ID:
            return jsonify({'error': 'Unauthorized'}), 403
        
        task = {
            'title': data.get('title'),
            'description': data.get('description'),
            'type': data.get('type'),  # text, photo, video, link
            'content': data.get('content'),
            'points': int(data.get('points', 50)),
            'active': True,
            'created_at': int(time.time() * 1000)
        }
        
        tasks = get_daily_tasks()
        task_id = f"task_{int(time.time())}"
        tasks[task_id] = task
        
        result, _ = _firebase_request('PUT', 'daily_tasks', tasks)
        
        if result:
            # Notify all users about new task
            users, _ = _firebase_request('GET', 'users')
            if users:
                for uid, udata in users.items():
                    try:
                        bot.send_message(
                            uid,
                            f"🎁 <b>New Daily Task Available!</b>\n\n{task['title']}\n\nEarn {task['points']} points! 🚀",
                            parse_mode='HTML'
                        )
                    except:
                        pass
        
        return jsonify({'success': True, 'task_id': task_id})
    except Exception as e:
        logger.error(f"Add task error: {e}")
        return jsonify({'error': str(e)}), 500

# ─────────────────────────────────────────────────────────────────────────────
# 🔍 Health Check
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'service': 'earnflow-bot'}), 200

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

# ─────────────────────────────────────────────────────────────────────────────
# 🚀 Entry Point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting EarnFlow server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
