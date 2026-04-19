import os
import json
import logging
import time
from flask import Flask, request, jsonify, render_template
import telebot
import requests

# Configure logging for Vercel
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='../templates')

# 🔐 Configuration - Use environment variables in production!
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw')
FIREBASE_DATABASE_URL = os.environ.get('FIREBASE_DATABASE_URL', 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/').rstrip('/')

# Initialize Telegram Bot
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML', threaded=False)

# 💰 Monetization Links
AD_SMART_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"
YOUTUBE_LINK = "https://www.youtube.com/@Instagrampost1"
INSTAGRAM_LINK = "https://www.instagram.com/digital_rockstar_m"
FACEBOOK_LINK = "https://www.facebook.com/profile.php?id=61574378159053"

# 📊 Point System: 100 Points = $1.00
POINTS_PER_DOLLAR = 100
AD_POINTS = 25
SOCIAL_POINTS = 100


def _firebase_request(method, path, data=None):
    """Internal: Make REST API calls to Firebase Realtime Database"""
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
        elif method == 'DELETE':
            resp = requests.delete(url, headers=headers, timeout=10)
        else:
            return None, "Invalid method"
            
        if resp.status_code in [200, 201]:
            return resp.json(), None
        logger.error(f"Firebase API {resp.status_code}: {resp.text[:200]}")
        return None, f"Firebase error: {resp.status_code}"
    except requests.Timeout:
        return None, "Firebase request timeout"
    except Exception as e:
        logger.error(f"Firebase request failed: {str(e)}")
        return None, str(e)


def get_user_data(user_id):
    """Fetch user data from Firebase"""
    data, error = _firebase_request('GET', f'users/{user_id}')
    if error:
        logger.warning(f"Could not fetch user {user_id}: {error}")
    return data


def update_user_points(user_id, points, transaction_type='earn'):
    """
    Update user points with simple atomic operation.
    Note: For high-concurrency production, implement proper transactions via Cloud Functions.
    """
    current = get_user_data(user_id)
    timestamp = int(time.time() * 1000)
    
    if not current:
        # Create new user record
        new_user = {
            'uid': user_id,
            'points': points,
            'history': {
                f"{timestamp}": {
                    'points': points,
                    'type': transaction_type,
                    'timestamp': timestamp
                }
            },
            'joined': timestamp,
            'last_active': timestamp
        }
        result, error = _firebase_request('PUT', f'users/{user_id}', new_user)
        return result is not None
    
    # Update existing user
    current_points = current.get('points', 0) or 0
    new_points = current_points + points
    
    # Append to history
    history = current.get('history', {}) or {}
    history[f"{timestamp}"] = {
        'points': points,
        'type': transaction_type,
        'timestamp': timestamp
    }
    
    update_payload = {
        'points': new_points,
        'history': history,
        'last_active': timestamp
    }
    
    result, error = _firebase_request('PATCH', f'users/{user_id}', update_payload)
    return result is not None


@bot.message_handler(commands=['start'])
def handle_start(message):
    """Handle /start command - creates user & sends dashboard link"""
    try:
        user_id = message.from_user.id
        first_name = message.from_user.first_name or 'User'
        username = message.from_user.username or ''
        
        # Initialize or update user in Firebase
        user_data = get_user_data(user_id)
        timestamp = int(time.time() * 1000)
        
        if not user_data:
            new_user = {
                'uid': user_id,
                'name': first_name,
                'username': username,
                'points': 0,
                'joined': timestamp,
                'last_active': timestamp
            }
            _firebase_request('PUT', f'users/{user_id}', new_user)
        else:
            _firebase_request('PATCH', f'users/{user_id}', {'last_active': timestamp, 'name': first_name})
        
        # Generate dashboard URL
        dashboard_url = f"https://ultimate-media-search-bot-t7kj.vercel.app/dashboard?id={user_id}&name={first_name}"
        
        # Create inline keyboard
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        dashboard_btn = telebot.types.InlineKeyboardButton("🚀 Open Premium Dashboard", url=dashboard_url)
        markup.add(dashboard_btn)
        
        # Send welcome message
        welcome_msg = f"""
👋 Hello <b>{first_name}</b>!

✨ Welcome to <b>Ultimate Media Search Bot</b> 💎

🎁 <b>Earn Rewards:</b>
├ 📺 Watch Ads: +{AD_POINTS} Points
├ 📱 Social Tasks: +{SOCIAL_POINTS} Points
└ 💰 <b>100 Points = $1.00 USD</b>

🔗 Tap below to open your dashboard and start earning!
        """
        
        bot.send_message(message.chat.id, welcome_msg, reply_markup=markup, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Start command error: {e}")
        bot.send_message(message.chat.id, "⚠️ Something went wrong. Please try again.", parse_mode='HTML')


# ─────────────────────────────────────────────────────────────────────────────
# 🔗 Webhook Handler (Telegram)
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Receive Telegram webhook updates"""
    try:
        update = request.get_json(force=True)
        if update:
            bot.process_new_updates([telebot.types.Update.de_json(update)])
        return '', 200
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return jsonify({'error': 'Webhook failed'}), 500


# ─────────────────────────────────────────────────────────────────────────────
# 🌐 Frontend Routes
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/dashboard')
def serve_dashboard():
    """Serve the premium dashboard HTML"""
    return render_template('dashboard.html')


# ─────────────────────────────────────────────────────────────────────────────
# 🔌 API Endpoints (Frontend ↔ Backend)
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/user/<int:user_id>', methods=['GET'])
def api_get_user(user_id):
    """Get user data for dashboard"""
    try:
        user_data = get_user_data(user_id)
        if user_data:
            user_data['balance_usd'] = (user_data.get('points', 0) or 0) / POINTS_PER_DOLLAR
            return jsonify(user_data)
        return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        logger.error(f"Get user API error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/earn/ad', methods=['POST'])
def api_earn_ad():
    """Award points for ad view"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        if update_user_points(int(user_id), AD_POINTS, 'ad_view'):
            return jsonify({'success': True, 'points_added': AD_POINTS})
        return jsonify({'error': 'Failed to update points'}), 500
        
    except Exception as e:
        logger.error(f"Ad earn API error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/earn/social', methods=['POST'])
def api_earn_social():
    """Award points for social task completion"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        task = data.get('task')  # youtube, instagram, facebook
        
        if not user_id or not task:
            return jsonify({'error': 'user_id and task required'}), 400
        
        if update_user_points(int(user_id), SOCIAL_POINTS, f'social_{task}'):
            return jsonify({'success': True, 'points_added': SOCIAL_POINTS})
        return jsonify({'error': 'Failed to update points'}), 500
        
    except Exception as e:
        logger.error(f"Social earn API error: {e}")
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# 🔍 Health & Utility
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/health')
def health_check():
    """Vercel health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'ultimate-media-search-bot'}), 200


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
    # For local development only - Vercel handles webhook via config
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
