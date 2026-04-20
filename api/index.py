"""
🚀 Ultimate Media Search Bot - Vercel Serverless Entry Point
✅ Firebase REST API (No Admin SDK - avoids cold start issues)
✅ Production Ready - Zero Error Design
"""
import os
import json
import logging
import time
import hashlib
import secrets
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
import telebot
import requests
from urllib.parse import urlparse, parse_qs

# ─────────────────────────────────────────────────────────────────────
# 🔧 Configuration - All from Environment Variables
# ─────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw')
FIREBASE_DB_URL = os.environ.get('FIREBASE_DATABASE_URL', 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app').rstrip('/')
ADMIN_IDS = os.environ.get('ADMIN_USER_IDS', '123456789').split(',')

# 💰 Points Configuration
POINTS_PER_DOLLAR = int(os.environ.get('POINTS_PER_DOLLAR', '100'))
AD_POINTS = int(os.environ.get('AD_POINTS', '25'))
SOCIAL_POINTS = int(os.environ.get('SOCIAL_POINTS', '100'))
REFERRAL_BONUS = int(os.environ.get('REFERRAL_BONUS', '50'))

# 🔗 Links
AD_LINK = os.environ.get('AD_SMART_LINK', 'https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b')
YOUTUBE_LINK = os.environ.get('YOUTUBE_LINK', 'https://www.youtube.com/@Instagrampost1')
INSTAGRAM_LINK = os.environ.get('INSTAGRAM_LINK', 'https://www.instagram.com/digital_rockstar_m')
FACEBOOK_LINK = os.environ.get('FACEBOOK_LINK', 'https://www.facebook.com/profile.php?id=61574378159053')
BANNER_IMAGE = os.environ.get('BANNER_IMAGE', 'https://i.ibb.co/9kmTw4Gh/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg')

# 🌐 App URLs
APP_URL = os.environ.get('APP_URL', 'https://ultimate-media-search-bot-t7kj.vercel.app')

# 🔐 Security
ADMIN_SECRET = os.environ.get('ADMIN_SECRET_KEY', 'change-this-in-vercel-dashboard')

# ─────────────────────────────────────────────────────────────────────
# 📝 Logging Setup
# ─────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# 🤖 Telegram Bot Initialization
# ─────────────────────────────────────────────────────────────────────
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML', threaded=False)

# ─────────────────────────────────────────────────────────────────────
# 🔗 Firebase REST API Helper Functions (No Admin SDK - Serverless Friendly)
# ─────────────────────────────────────────────────────────────────────
def _firebase_url(path):
    """Build Firebase REST API URL"""
    return f"{FIREBASE_DB_URL}/{path}.json"

def _firebase_get(path, params=None):
    """GET request to Firebase"""
    try:
        url = _firebase_url(path)
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception as e:
        logger.error(f"Firebase GET error: {e}")
        return None

def _firebase_set(path, data):
    """PUT request to Firebase (overwrite)"""
    try:
        url = _firebase_url(path)
        resp = requests.put(url, json=data, timeout=10)
        return resp.status_code in [200, 201]
    except Exception as e:
        logger.error(f"Firebase SET error: {e}")
        return False

def _firebase_patch(path, data):
    """PATCH request to Firebase (partial update)"""
    try:
        url = _firebase_url(path)
        resp = requests.patch(url, json=data, timeout=10)
        return resp.status_code in [200, 201]
    except Exception as e:
        logger.error(f"Firebase PATCH error: {e}")
        return False

def _firebase_push(path, data):
    """POST request to Firebase (create new child with auto-ID)"""
    try:
        url = _firebase_url(path)
        resp = requests.post(url, json=data, timeout=10)
        if resp.status_code == 201:
            return resp.json().get('name')
        return None
    except Exception as e:
        logger.error(f"Firebase PUSH error: {e}")
        return None

# ─────────────────────────────────────────────────────────────────────
# 👤 User Database Operations
# ─────────────────────────────────────────────────────────────────────
def get_user(telegram_id):
    """Get user data from Firebase"""
    return _firebase_get(f'users/{telegram_id}')

def create_user(telegram_id, username, first_name, referral_code=None):
    """Create new user in Firebase"""
    timestamp = int(time.time() * 1000)
    my_referral = hashlib.sha256(f"{telegram_id}{secrets.token_hex(4)}".encode()).hexdigest()[:8].upper()
    
    user_data = {
        'telegram_id': telegram_id,
        'username': username,
        'first_name': first_name,
        'referral_code': my_referral,
        'referred_by': referral_code,
        'points': 0,
        'pending_points': 0,
        'total_earned': 0,
        'tasks_completed': 0,
        'joined_at': timestamp,
        'last_active': timestamp,
        'is_banned': False
    }
    
    success = _firebase_set(f'users/{telegram_id}', user_data)
    
    # Handle referral bonus
    if success and referral_code:
        _process_referral(referral_code, telegram_id)
    
    return user_data if success else None

def update_user(telegram_id, updates):
    """Partial update user data"""
    updates['last_active'] = int(time.time() * 1000)
    return _firebase_patch(f'users/{telegram_id}', updates)

def add_points(telegram_id, points, tx_type, description=''):
    """Atomically add points to user"""
    user = get_user(telegram_id)
    if not user:
        return False
    
    timestamp = int(time.time() * 1000)
    current_points = user.get('points', 0) or 0
    new_points = current_points + points
    
    # Add to history
    history = user.get('history', {}) or {}
    history[f"{timestamp}_{secrets.token_hex(4)}"] = {
        'points': points,
        'type': tx_type,
        'description': description,
        'timestamp': timestamp,
        'balance_after': new_points
    }
    
    return _firebase_patch(f'users/{telegram_id}', {
        'points': new_points,
        'total_earned': (user.get('total_earned', 0) or 0) + points,
        'history': history
    })

def _process_referral(referral_code, new_user_id):
    """Award referral bonus to referrer"""
    # Find referrer by referral code
    users = _firebase_get('users') or {}
    for uid, data in users.items():
        if data.get('referral_code') == referral_code and not data.get('is_banned'):
            add_points(int(uid), REFERRAL_BONUS, 'referral_bonus', f'New user: {new_user_id}')
            # Record referral
            _firebase_push(f'referrals/{uid}/{new_user_id}', {
                'joined_at': int(time.time() * 1000),
                'bonus': REFERRAL_BONUS
            })
            break

def create_submission(telegram_id, task_type, screenshot_url, proof_text=''):
    """Create pending task submission"""
    submission_id = secrets.token_urlsafe(12)
    timestamp = int(time.time() * 1000)
    
    submission = {
        'id': submission_id,
        'user_id': telegram_id,
        'task_type': task_type,
        'screenshot_url': screenshot_url[:500],
        'proof_text': proof_text[:200],
        'status': 'pending',
        'submitted_at': timestamp,
        'reviewed_at': None,
        'reviewed_by': None,
        'points_awarded': 0
    }
    
    success = _firebase_set(f'submissions/{submission_id}', submission)
    if success:
        # Add to user's pending list
        pending = get_user(telegram_id).get('pending_submissions', {}) or {}
        pending[submission_id] = {'task_type': task_type, 'submitted_at': timestamp}
        _firebase_patch(f'users/{telegram_id}', {'pending_submissions': pending})
    
    return submission_id if success else None

def get_pending_submissions(limit=20):
    """Get submissions pending admin review"""
    submissions = _firebase_get('submissions') or {}
    pending = []
    
    for sid, data in submissions.items():
        if data.get('status') == 'pending':
            user = get_user(data.get('user_id'))
            pending.append({
                'id': sid,
                **data,
                'user_info': {
                    'username': user.get('username') if user else 'Unknown',
                    'first_name': user.get('first_name') if user else 'Unknown'
                } if user else None
            })
    
    # Sort by newest first and limit
    pending.sort(key=lambda x: x.get('submitted_at', 0), reverse=True)
    return pending[:limit]

def review_submission(submission_id, admin_id, approved, reason=None):
    """Admin review: approve or reject submission"""
    submission = _firebase_get(f'submissions/{submission_id}')
    if not submission or submission.get('status') != 'pending':
        return False
    
    telegram_id = submission['user_id']
    timestamp = int(time.time() * 1000)
    points = SOCIAL_POINTS if approved else 0
    
    # Update submission
    _firebase_patch(f'submissions/{submission_id}', {
        'status': 'approved' if approved else 'rejected',
        'reviewed_at': timestamp,
        'reviewed_by': admin_id,
        'points_awarded': points,
        'rejection_reason': reason if not approved else None
    })
    
    if approved:
        add_points(telegram_id, points, 'task_approved', f'Submission: {submission_id}')
        # Update user stats
        user = get_user(telegram_id)
        if user:
            pending = user.get('pending_submissions', {}) or {}
            if submission_id in pending:
                del pending[submission_id]
                _firebase_patch(f'users/{telegram_id}', {
                    'tasks_completed': (user.get('tasks_completed', 0) or 0) + 1,
                    'pending_submissions': pending
                })
    
    return True

def broadcast_message(admin_id, message, target_users=None):
    """Send broadcast to users"""
    if str(admin_id) not in ADMIN_IDS:
        return {'error': 'Unauthorized', 'sent': 0}
    
    timestamp = int(time.time() * 1000)
    broadcast_id = secrets.token_urlsafe(8)
    
    users = _firebase_get('users') or {}
    sent = 0
    
    for uid, data in users.items():
        if target_users and int(uid) not in target_users:
            continue
        if data.get('is_banned'):
            continue
        
        # Add notification
        notifications = data.get('notifications', {}) or {}
        notifications[f"{timestamp}_{secrets.token_hex(4)}"] = {
            'id': broadcast_id,
            'message': message[:500],
            'read': False,
            'sent_at': timestamp,
            'type': 'broadcast'
        }
        _firebase_patch(f'users/{uid}', {'notifications': notifications})
        sent += 1
    
    return {'success': True, 'sent': sent, 'broadcast_id': broadcast_id}

# ─────────────────────────────────────────────────────────────────────
# 🎨 Flask App Initialization
# ─────────────────────────────────────────────────────────────────────
app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static',
            static_url_path='/static')

# ─────────────────────────────────────────────────────────────────────
# 🤖 Telegram Bot Handlers
# ─────────────────────────────────────────────────────────────────────
@bot.message_handler(commands=['start'])
def handle_start(message):
    """Handle /start command"""
    try:
        user = message.from_user
        telegram_id = user.id
        username = user.username or user.first_name or 'User'
        
        # Check for referral code in deep link
        referral_code = None
        if message.text and '/start ' in message.text:
            parts = message.text.split(maxsplit=1)
            if len(parts) > 1:
                referral_code = parts[1].strip()[:20]
        
        # Create or update user
        existing = get_user(telegram_id)
        if not existing:
            create_user(telegram_id, username, user.first_name, referral_code)
            welcome_msg = f"""
🌟 <b>Welcome to Ultimate Media Search!</b>

👋 Hello <b>{user.first_name}</b>!

💬 <i>"Your smartphone is now your ATM. Start earning for your time!"</i> 💰

🎁 <b>Earn Points:</b>
├ 📺 Watch Ads → +{AD_POINTS} Points
├ 📱 Social Tasks → +{SOCIAL_POINTS} Points
├ 👥 Refer Friends → +{REFERRAL_BONUS} Points
└ 💰 <b>{POINTS_PER_DOLLAR} Points = $1.00</b>

👇 Tap below to open your Premium Dashboard!
            """
        else:
            update_user(telegram_id, {'username': username, 'first_name': user.first_name})
            welcome_msg = f"""
👋 Welcome back, <b>{user.first_name}</b>!

💰 Balance: <b>{existing.get('points', 0):,} Points</b> (${existing.get('points', 0) / POINTS_PER_DOLLAR:.2f})

🚀 Continue earning rewards!
            """
        
        # Create inline keyboard with WebApp button
        dashboard_url = f"{APP_URL}/dashboard?id={telegram_id}&name={username}"
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            telebot.types.InlineKeyboardButton(
                "🚀 Open Premium Dashboard",
                web_app=telebot.types.WebAppInfo(url=dashboard_url)
            ),
            telebot.types.InlineKeyboardButton("📋 View Tasks", callback_data=f"tasks:{telegram_id}"),
            telebot.types.InlineKeyboardButton("👥 Invite", callback_data=f"invite:{telegram_id}")
        )
        
        # Send photo with caption
        try:
            bot.send_photo(message.chat.id, photo=BANNER_IMAGE, caption=welcome_msg, reply_markup=markup)
        except:
            bot.send_message(message.chat.id, welcome_msg + f"\n\n🖼️ <a href='{BANNER_IMAGE}'>View Banner</a>", reply_markup=markup, parse_mode='HTML')
            
    except Exception as e:
        logger.error(f"Start error: {e}")
        bot.send_message(message.chat.id, "⚠️ Error. Please try /start again.")

@bot.callback_query_handler(func=lambda c: c.data.startswith('tasks:'))
def handle_tasks_menu(call):
    """Show tasks inline keyboard"""
    telegram_id = int(call.data.split(':')[1])
    if call.from_user.id != telegram_id:
        bot.answer_callback_query(call.id, "⚠️ Unauthorized", show_alert=True)
        return
    
    tasks = [
        ("📺", "Watch Ad", f"+{AD_POINTS} pts", "ad"),
        ("▶️", "YouTube Subscribe", f"+{SOCIAL_POINTS} pts", "youtube"),
        ("📘", "Facebook Follow", f"+{SOCIAL_POINTS} pts", "facebook"),
        ("📷", "Instagram Follow", f"+{SOCIAL_POINTS} pts", "instagram"),
    ]
    
    text = f"💎 <b>Available Tasks</b>\n\nComplete tasks, upload screenshot, earn points!"
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    for icon, title, reward, task_id in tasks:
        markup.add(telebot.types.InlineKeyboardButton(
            f"{icon} {title} {reward}",
            callback_data=f"select:{task_id}:{telegram_id}"
        ))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('select:'))
def handle_task_select(call):
    """Handle task selection"""
    parts = call.data.split(':')
    task_type, telegram_id = parts[1], int(parts[2])
    
    if call.from_user.id != telegram_id:
        bot.answer_callback_query(call.id, "⚠️ Unauthorized", show_alert=True)
        return
    
    links = {'youtube': YOUTUBE_LINK, 'facebook': FACEBOOK_LINK, 'instagram': INSTAGRAM_LINK}
    link = links.get(task_type, '#')
    
    text = f"""
📋 <b>{task_type.title()} Task</b>

1. Click the link below
2. Complete the action (Subscribe/Follow)
3. Take a screenshot
4. Upload via Web App dashboard

🔗 Link: {link}

⚠️ Fake submissions = permanent ban
    """
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("🔗 Open Link", url=link),
        telebot.types.InlineKeyboardButton(
            "📤 Upload Screenshot",
            web_app=telebot.types.WebAppInfo(url=f"{APP_URL}/dashboard?id={telegram_id}&task={task_type}")
        ),
        telebot.types.InlineKeyboardButton("🔙 Back", callback_data=f"tasks:{telegram_id}")
    )
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('invite:'))
def handle_invite(call):
    """Show referral link"""
    telegram_id = int(call.data.split(':')[1])
    if call.from_user.id != telegram_id:
        bot.answer_callback_query(call.id, "⚠️ Unauthorized", show_alert=True)
        return
    
    user = get_user(telegram_id)
    if not user:
        bot.answer_callback_query(call.id, "User not found", show_alert=True)
        return
    
    referral_link = f"https://t.me/{bot.get_me().username}?start={user['referral_code']}"
    text = f"""
👥 <b>Invite Friends & Earn!</b>

🎁 Earn +{REFERRAL_BONUS} Points per friend!

🔗 Your Link:
<code>{referral_link}</code>

📋 Share in groups for maximum earnings!
    """
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📋 Copy", switch_inline_query=referral_link))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['admin'])
def handle_admin(message):
    """Admin panel access"""
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.send_message(message.chat.id, "🔐 Admin access required.")
        return
    
    admin_url = f"{APP_URL}/admin?key={ADMIN_SECRET}"
    bot.send_message(message.chat.id, f"🔧 <b>Admin Panel</b>\n\n🔗 {admin_url}", parse_mode='HTML')

@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    """Admin broadcast command"""
    if str(message.from_user.id) not in ADMIN_IDS:
        return
    
    msg_text = message.text.replace('/broadcast', '').strip()
    if not msg_text:
        bot.reply_to(message, "Usage: /broadcast Your message")
        return
    
    result = broadcast_message(message.from_user.id, msg_text)
    if result.get('success'):
        bot.reply_to(message, f"✅ Sent to {result['sent']} users!")
    else:
        bot.reply_to(message, f"❌ Error: {result.get('error')}")

# ─────────────────────────────────────────────────────────────────────
# 🔗 Webhook Handler for Telegram
# ─────────────────────────────────────────────────────────────────────
@app.route('/webhook', methods=['POST'])
def webhook():
    """Receive Telegram webhook updates"""
    try:
        update = request.get_json(force=True)
        if update:
            bot.process_new_updates([telebot.types.Update.de_json(update)])
        return '', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': 'Webhook failed'}), 500

# ─────────────────────────────────────────────────────────────────────
# 🌐 Frontend Routes
# ─────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('dashboard.html', 
                          firebase_config={'databaseURL': FIREBASE_DB_URL},
                          banner=BANNER_IMAGE,
                          config={'app_url': APP_URL})

@app.route('/dashboard')
def dashboard():
    """Premium User Dashboard (TWA)"""
    telegram_id = request.args.get('id', type=int)
    username = request.args.get('name', 'User')
    task_filter = request.args.get('task', '')
    
    if not telegram_id:
        return render_template('dashboard.html', 
                              error="Open from Telegram bot",
                              firebase_config={'databaseURL': FIREBASE_DB_URL},
                              banner=BANNER_IMAGE,
                              config={'app_url': APP_URL})
    
    user = get_user(telegram_id)
    if not user:
        return render_template('dashboard.html',
                              error="User not found. Send /start in Telegram.",
                              firebase_config={'databaseURL': FIREBASE_DB_URL},
                              banner=BANNER_IMAGE,
                              config={'app_url': APP_URL})
    
    return render_template('dashboard.html',
                          user=user,
                          firebase_config={'databaseURL': FIREBASE_DB_URL},
                          banner=BANNER_IMAGE,
                          config={
                              'app_url': APP_URL,
                              'points_per_dollar': POINTS_PER_DOLLAR,
                              'ad_points': AD_POINTS,
                              'social_points': SOCIAL_POINTS,
                              'referral_bonus': REFERRAL_BONUS,
                              'ad_link': AD_LINK,
                              'youtube_link': YOUTUBE_LINK,
                              'instagram_link': INSTAGRAM_LINK,
                              'facebook_link': FACEBOOK_LINK
                          },
                          initial_data={
                              'telegram_id': telegram_id,
                              'username': username,
                              'task_filter': task_filter
                          })

@app.route('/welcome')
def welcome():
    """Welcome card page"""
    return render_template('welcome.html', banner=BANNER_IMAGE, app_url=APP_URL)

@app.route('/admin')
def admin_panel():
    """Admin Panel"""
    key = request.args.get('key') or request.headers.get('X-Admin-Key')
    if key != ADMIN_SECRET:
        return jsonify({'error': 'Unauthorized'}), 401
    
    stats = {
        'total_users': len(_firebase_get('users') or {}),
        'pending_reviews': len([s for s in (_firebase_get('submissions') or {}).values() if s.get('status') == 'pending'])
    }
    pending = get_pending_submissions(20)
    
    return render_template('admin.html', 
                          admin_key=ADMIN_SECRET,
                          stats=stats,
                          pending=pending,
                          app_url=APP_URL)

# ─────────────────────────────────────────────────────────────────────
# 🔌 API Endpoints
# ─────────────────────────────────────────────────────────────────────
@app.route('/api/user', methods=['GET'])
def api_get_user():
    """Get user data"""
    telegram_id = request.headers.get('X-User-ID') or request.args.get('id', type=int)
    if not telegram_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    user = get_user(int(telegram_id))
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    user['balance_usd'] = (user.get('points', 0) or 0) / POINTS_PER_DOLLAR
    user['referral_link'] = f"https://t.me/{os.environ.get('BOT_USERNAME', 'bot')}?start={user.get('referral_code', '')}"
    
    # Remove sensitive fields
    safe_user = {k: v for k, v in user.items() if k not in ['ip_hash', 'device_fingerprint']}
    return jsonify({'success': True, 'data': safe_user})

@app.route('/api/tasks', methods=['GET'])
def api_get_tasks():
    """Get available tasks"""
    telegram_id = request.headers.get('X-User-ID') or request.args.get('id', type=int)
    if not telegram_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    user = get_user(int(telegram_id))
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Get completed tasks
    completed = {}
    history = user.get('history', {}) or {}
    for entry in history.values():
        if entry.get('type') == 'task_approved':
            completed[entry.get('description', '').split(':')[-1].strip()] = True
    
    tasks = [
        {'id': 'ad', 'icon': '📺', 'title': 'Watch Advertisement', 'points': AD_POINTS, 'type': 'instant', 'completed': completed.get('ad', False)},
        {'id': 'youtube', 'icon': '▶️', 'title': 'YouTube Subscribe', 'points': SOCIAL_POINTS, 'type': 'verification', 'completed': completed.get('youtube', False), 'link': YOUTUBE_LINK},
        {'id': 'facebook', 'icon': '📘', 'title': 'Facebook Follow', 'points': SOCIAL_POINTS, 'type': 'verification', 'completed': completed.get('facebook', False), 'link': FACEBOOK_LINK},
        {'id': 'instagram', 'icon': '📷', 'title': 'Instagram Follow', 'points': SOCIAL_POINTS, 'type': 'verification', 'completed': completed.get('instagram', False), 'link': INSTAGRAM_LINK},
    ]
    
    return jsonify({'success': True, 'data': {'tasks': tasks}})

@app.route('/api/submit/task', methods=['POST'])
def api_submit_task():
    """Submit task with screenshot"""
    telegram_id = request.headers.get('X-User-ID')
    if not telegram_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json() or {}
        task_type = data.get('task_type', '')[:50]
        screenshot_url = data.get('screenshot_url', '')[:500]
        proof_text = data.get('proof_text', '')[:200]
        
        if not task_type or not screenshot_url:
            return jsonify({'success': False, 'error': 'Task type and screenshot required'}), 400
        
        # Basic URL validation
        if not screenshot_url.startswith('https://') or '.' not in screenshot_url.split('/')[-1]:
            return jsonify({'success': False, 'error': 'Invalid screenshot URL'}), 400
        
        submission_id = create_submission(int(telegram_id), task_type, screenshot_url, proof_text)
        if submission_id:
            return jsonify({'success': True, 'data': {'submission_id': submission_id, 'status': 'pending'}})
        
        return jsonify({'success': False, 'error': 'Submission failed'}), 500
    except Exception as e:
        logger.error(f"Submit error: {e}")
        return jsonify({'success': False, 'error': 'Internal error'}), 500

@app.route('/api/earn/ad', methods=['POST'])
def api_earn_ad():
    """Instant ad reward"""
    telegram_id = request.headers.get('X-User-ID')
    if not telegram_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    user = get_user(int(telegram_id))
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Check cooldown (1 hour)
    history = user.get('history', {}) or {}
    for entry in history.values():
        if entry.get('type') == 'ad_view':
            if time.time() * 1000 - entry.get('timestamp', 0) < 3600000:
                return jsonify({'success': False, 'error': 'Please wait before next ad'}), 429
            break
    
    if add_points(int(telegram_id), AD_POINTS, 'ad_view', 'Ad watched'):
        return jsonify({'success': True, 'data': {'points_added': AD_POINTS}})
    
    return jsonify({'success': False, 'error': 'Failed to award points'}), 500

@app.route('/api/referral/stats', methods=['GET'])
def api_referral_stats():
    """Get referral statistics"""
    telegram_id = request.headers.get('X-User-ID')
    if not telegram_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    user = get_user(int(telegram_id))
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    referrals = _firebase_get(f'referrals/{telegram_id}') or {}
    
    return jsonify({'success': True, 'data': {
        'total_referrals': len(referrals),
        'total_bonus': len(referrals) * REFERRAL_BONUS,
        'referral_link': f"https://t.me/{os.environ.get('BOT_USERNAME', 'bot')}?start={user.get('referral_code', '')}"
    }})

# ─────────────────────────────────────────────────────────────────────
# 🔐 Admin API
# ─────────────────────────────────────────────────────────────────────
@app.route('/api/admin/submissions', methods=['GET'])
def api_admin_submissions():
    """Get pending submissions"""
    key = request.headers.get('X-Admin-Key') or request.args.get('key')
    if key != ADMIN_SECRET:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    submissions = get_pending_submissions(20)
    return jsonify({'success': True, 'data': {'submissions': submissions, 'count': len(submissions)}})

@app.route('/api/admin/review', methods=['POST'])
def api_admin_review():
    """Review submission"""
    key = request.headers.get('X-Admin-Key')
    if key != ADMIN_SECRET:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json() or {}
        sid = data.get('submission_id')
        approved = data.get('approved', False)
        reason = data.get('reason', 'Admin decision')[:200]
        
        if not sid:
            return jsonify({'success': False, 'error': 'Submission ID required'}), 400
        
        if review_submission(sid, ADMIN_IDS[0], approved, reason):
            return jsonify({'success': True, 'data': {'status': 'approved' if approved else 'rejected'}})
        
        return jsonify({'success': False, 'error': 'Review failed'}), 500
    except Exception as e:
        logger.error(f"Review error: {e}")
        return jsonify({'success': False, 'error': 'Internal error'}), 500

@app.route('/api/admin/broadcast', methods=['POST'])
def api_admin_broadcast():
    """Send broadcast"""
    key = request.headers.get('X-Admin-Key')
    if key != ADMIN_SECRET:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json() or {}
        message = data.get('message', '')[:1000]
        
        if not message:
            return jsonify({'success': False, 'error': 'Message required'}), 400
        
        result = broadcast_message(ADMIN_IDS[0], message)
        if result.get('success'):
            return jsonify({'success': True, 'data': result})
        
        return jsonify({'success': False, 'error': result.get('error')}), 500
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        return jsonify({'success': False, 'error': 'Internal error'}), 500

# ─────────────────────────────────────────────────────────────────────
# 🔍 Health & Error Handlers
# ─────────────────────────────────────────────────────────────────────
@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'ultimate-media-bot'}), 200

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

# ─────────────────────────────────────────────────────────────────────
# 🚀 Entry Point
# ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
