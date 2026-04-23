# index.py
import os
import json
import hashlib
import hmac
import requests
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, jsonify, render_template, session
from functools import wraps
from datetime import datetime
import re

# -------------------- INITIALIZATION --------------------
app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Hardcoded Credentials
TELEGRAM_BOT_TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
DEEPSEEK_API_KEY = "sk-783d645ce9e84eb8b954786a016561ea"
FIREBASE_DB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"

# Admin password (for admin panel)
ADMIN_PASSWORD = "UltimateAdmin2025"

# Initialize Firebase Admin SDK
# For Vercel, we'll use environment variable for service account
# If not present, create a dummy one for development (but will fail in production)
firebase_initialized = False
try:
    # Check if service account info is provided via environment
    if os.environ.get('FIREBASE_SERVICE_ACCOUNT'):
        service_account_info = json.loads(os.environ.get('FIREBASE_SERVICE_ACCOUNT'))
        cred = credentials.Certificate(service_account_info)
    else:
        # For local testing, you need to download service account json
        # and set GOOGLE_APPLICATION_CREDENTIALS environment variable
        cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {
        'databaseURL': FIREBASE_DB_URL
    })
    firebase_initialized = True
    print("Firebase Admin SDK initialized successfully")
except Exception as e:
    print(f"Firebase initialization warning: {e}. Using REST API fallback.")
    # We'll use REST API with API key as fallback

# Database reference helper
def get_db_ref():
    if firebase_initialized:
        return db.reference('/')
    return None

# -------------------- HELPER FUNCTIONS --------------------
def telegram_api_call(method, params=None):
    """Make calls to Telegram Bot API"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
    try:
        response = requests.post(url, json=params) if params else requests.get(url)
        return response.json()
    except Exception as e:
        print(f"Telegram API error: {e}")
        return None

def send_telegram_message(chat_id, text, parse_mode='HTML', reply_markup=None):
    """Send message via Telegram"""
    params = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    }
    if reply_markup:
        params['reply_markup'] = json.dumps(reply_markup)
    return telegram_api_call('sendMessage', params)

def send_telegram_photo(chat_id, photo_url, caption=None, parse_mode='HTML', reply_markup=None):
    """Send photo via Telegram"""
    params = {
        'chat_id': chat_id,
        'photo': photo_url,
        'parse_mode': parse_mode
    }
    if caption:
        params['caption'] = caption
    if reply_markup:
        params['reply_markup'] = json.dumps(reply_markup)
    return telegram_api_call('sendPhoto', params)

def get_user(telegram_id):
    """Get user from Firebase"""
    ref = get_db_ref()
    if ref:
        user = ref.child(f'users/{telegram_id}').get()
        return user
    return None

def create_or_update_user(telegram_id, user_data):
    """Create or update user in Firebase"""
    ref = get_db_ref()
    if ref:
        ref.child(f'users/{telegram_id}').set(user_data)
        return True
    return False

def get_membership_plan(plan):
    """Return formatted membership plan name"""
    plans = {
        'free': 'Free',
        'earner_pro': 'Earner Pro',
        'influencer_pro': 'Influencer Pro'
    }
    return plans.get(plan, 'Free')

def get_ai_cost(user_plan):
    """Get AI message cost based on membership"""
    costs = {
        'free': 10,
        'earner_pro': 5,
        'influencer_pro': 0
    }
    return costs.get(user_plan, 10)

def deduct_points(telegram_id, points):
    """Deduct points from user"""
    ref = get_db_ref()
    if ref:
        user = get_user(telegram_id)
        if user and user.get('points', 0) >= points:
            new_points = user.get('points', 0) - points
            ref.child(f'users/{telegram_id}/points').set(new_points)
            return new_points
    return None

def add_points(telegram_id, points):
    """Add points to user"""
    ref = get_db_ref()
    if ref:
        user = get_user(telegram_id)
        current_points = user.get('points', 0) if user else 0
        new_points = current_points + points
        ref.child(f'users/{telegram_id}/points').set(new_points)
        return new_points
    return None

def complete_task(telegram_id, task_name):
    """Mark task as completed and add points if not already done"""
    ref = get_db_ref()
    if ref:
        user = get_user(telegram_id)
        if user:
            tasks_completed = user.get('tasks_completed', {})
            if not tasks_completed.get(task_name, False):
                # Mark task as completed
                tasks_completed[task_name] = True
                ref.child(f'users/{telegram_id}/tasks_completed').set(tasks_completed)
                # Add points
                add_points(telegram_id, 100)
                return True
    return False

def call_deepseek_api(messages):
    """Call DeepSeek AI API"""
    headers = {
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        'model': 'deepseek-chat',
        'messages': messages,
        'temperature': 0.7,
        'max_tokens': 500
    }
    try:
        response = requests.post('https://api.deepseek.com/v1/chat/completions', 
                                 headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"AI Error: {response.status_code}"
    except Exception as e:
        return f"AI Error: {str(e)}"

# -------------------- TELEGRAM WEBHOOK HANDLER --------------------
@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram updates"""
    update = request.json
    if not update:
        return jsonify({'status': 'ok'})
    
    # Process message
    if 'message' in update:
        message = update['message']
        chat_id = message['chat']['id']
        user_id = str(chat_id)
        first_name = message['chat'].get('first_name', 'User')
        
        # Ensure user exists
        user = get_user(user_id)
        if not user:
            user_data = {
                'id': user_id,
                'first_name': first_name,
                'points': 0,
                'plan': 'free',
                'tasks_completed': {
                    'youtube': False,
                    'instagram': False,
                    'facebook': False
                },
                'joined_at': datetime.now().isoformat()
            }
            create_or_update_user(user_id, user_data)
            user = user_data
        
        # Handle /start command
        if 'text' in message and message['text'].startswith('/start'):
            # Create inline keyboard for social tasks
            keyboard = {
                'inline_keyboard': [
                    [
                        {'text': '📺 YouTube', 'callback_data': 'task_youtube'},
                        {'text': '📸 Instagram', 'callback_data': 'task_instagram'},
                        {'text': '📘 Facebook', 'callback_data': 'task_facebook'}
                    ],
                    [
                        {'text': '🤖 AI Chat', 'callback_data': 'ai_chat'},
                        {'text': '💎 Upgrade', 'callback_data': 'upgrade'}
                    ]
                ]
            }
            
            caption = f"<b>Welcome {first_name}!</b>\n\n" \
                      f"💰 <b>Points Balance:</b> {user.get('points', 0)}\n" \
                      f"👑 <b>Membership Plan:</b> {get_membership_plan(user.get('plan', 'free'))}\n\n" \
                      f"✨ Complete social tasks to earn 100 points each!\n" \
                      f"🤖 Use /ai to chat with DeepSeek AI (10 points per message for Free users)\n" \
                      f"💎 Upgrade to Pro plans for exclusive benefits!"
            
            send_telegram_photo(chat_id, 
                              "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg",
                              caption=caption,
                              reply_markup=keyboard)
        
        # Handle /ai command
        elif 'text' in message and message['text'].startswith('/ai'):
            # Extract query (remove /ai command)
            query = message['text'].replace('/ai', '').strip()
            if not query:
                send_telegram_message(chat_id, "🤖 Please provide a message after /ai command.\nExample: `/ai What is AI?`")
                return jsonify({'status': 'ok'})
            
            # Check points and deduct
            cost = get_ai_cost(user.get('plan', 'free'))
            if user.get('points', 0) < cost:
                send_telegram_message(chat_id, f"❌ Insufficient points! You need {cost} points for AI chat.\nComplete social tasks to earn points!")
                return jsonify({'status': 'ok'})
            
            # Deduct points
            deduct_points(user_id, cost)
            
            # Call DeepSeek API
            send_telegram_message(chat_id, "🤔 Thinking...")
            ai_response = call_deepseek_api([{"role": "user", "content": query}])
            
            # Send response
            response_text = f"🤖 <b>AI Response:</b>\n\n{ai_response}\n\n💎 <i>Points deducted: {cost}</i>"
            send_telegram_message(chat_id, response_text)
    
    # Handle callback queries (inline button clicks)
    elif 'callback_query' in update:
        callback = update['callback_query']
        chat_id = callback['message']['chat']['id']
        user_id = str(chat_id)
        data = callback['data']
        
        # Answer callback query to remove loading state
        telegram_api_call('answerCallbackQuery', {'callback_query_id': callback['id']})
        
        # Get user
        user = get_user(user_id)
        
        if data == 'task_youtube':
            if complete_task(user_id, 'youtube'):
                send_telegram_message(chat_id, "✅ YouTube task completed! +100 points added!")
            else:
                send_telegram_message(chat_id, "⚠️ You've already completed the YouTube task!")
        
        elif data == 'task_instagram':
            if complete_task(user_id, 'instagram'):
                send_telegram_message(chat_id, "✅ Instagram task completed! +100 points added!")
            else:
                send_telegram_message(chat_id, "⚠️ You've already completed the Instagram task!")
        
        elif data == 'task_facebook':
            if complete_task(user_id, 'facebook'):
                send_telegram_message(chat_id, "✅ Facebook task completed! +100 points added!")
            else:
                send_telegram_message(chat_id, "⚠️ You've already completed the Facebook task!")
        
        elif data == 'ai_chat':
            send_telegram_message(chat_id, "🤖 Use /ai <your message> to chat with AI!\nExample: `/ai What is the weather?`")
        
        elif data == 'upgrade':
            keyboard = {
                'inline_keyboard': [
                    [{'text': '💰 Earner Pro - ₹100', 'callback_data': 'upgrade_100'}],
                    [{'text': '👑 Influencer Pro - ₹500', 'callback_data': 'upgrade_500'}],
                    [{'text': '❌ Cancel', 'callback_data': 'cancel_upgrade'}]
                ]
            }
            send_telegram_message(chat_id, 
                                "💎 <b>Upgrade Your Membership</b>\n\n"
                                "🔹 <b>Earner Pro (₹100)</b>\n"
                                "   • 500 bonus points\n"
                                "   • 50% discount on AI (5 points/message)\n\n"
                                "🔹 <b>Influencer Pro (₹500)</b>\n"
                                "   • 2000 bonus points\n"
                                "   • Free AI chat (0 points)\n\n"
                                "📤 <b>Payment Instructions:</b>\n"
                                "UPI ID: <code>8543083014@ikwik</code>\n\n"
                                "After payment, visit our web dashboard to submit your transaction ID and screenshot.\n"
                                "🔗 Dashboard: <your-vercel-url>/dashboard",
                                reply_markup=keyboard)
        
        elif data == 'upgrade_100':
            send_telegram_message(chat_id, 
                                "💰 <b>Earner Pro Upgrade - ₹100</b>\n\n"
                                "Please pay ₹100 to UPI ID: <code>8543083014@ikwik</code>\n\n"
                                "After payment, go to our web dashboard and submit:\n"
                                "• Transaction ID\n"
                                "• Payment Screenshot\n\n"
                                "🔗 Dashboard: <your-vercel-url>/dashboard\n\n"
                                "Our admin will approve your upgrade within 24 hours.")
        
        elif data == 'upgrade_500':
            send_telegram_message(chat_id, 
                                "👑 <b>Influencer Pro Upgrade - ₹500</b>\n\n"
                                "Please pay ₹500 to UPI ID: <code>8543083014@ikwik</code>\n\n"
                                "After payment, go to our web dashboard and submit:\n"
                                "• Transaction ID\n"
                                "• Payment Screenshot\n\n"
                                "🔗 Dashboard: <your-vercel-url>/dashboard\n\n"
                                "Our admin will approve your upgrade within 24 hours.")
        
        elif data == 'cancel_upgrade':
            send_telegram_message(chat_id, "❌ Upgrade cancelled.")
    
    return jsonify({'status': 'ok'})

# -------------------- API ENDPOINTS --------------------
@app.route('/api/auth_telegram', methods=['POST'])
def auth_telegram():
    """Verify Telegram Login Widget data"""
    data = request.json
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'})
    
    # Verify hash
    hash_string = data.get('hash')
    if not hash_string:
        return jsonify({'success': False, 'error': 'No hash provided'})
    
    # Check required fields
    required_fields = ['id', 'first_name', 'auth_date', 'hash']
    for field in required_fields:
        if field not in data:
            return jsonify({'success': False, 'error': f'Missing field: {field}'})
    
    # Prepare check string
    check_list = []
    for key in sorted(data.keys()):
        if key != 'hash':
            check_list.append(f"{key}={data[key]}")
    check_string = "\n".join(check_list)
    
    # Compute hash
    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode()).digest()
    computed_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    
    if computed_hash != hash_string:
        return jsonify({'success': False, 'error': 'Invalid hash'})
    
    # Get user data from Firebase
    user_id = str(data['id'])
    user = get_user(user_id)
    
    if not user:
        # Create new user
        user_data = {
            'id': user_id,
            'first_name': data.get('first_name', 'User'),
            'points': 0,
            'plan': 'free',
            'tasks_completed': {
                'youtube': False,
                'instagram': False,
                'facebook': False
            },
            'joined_at': datetime.now().isoformat()
        }
        create_or_update_user(user_id, user_data)
        user = user_data
    
    return jsonify({
        'success': True,
        'user': {
            'id': user_id,
            'first_name': user.get('first_name'),
            'points': user.get('points', 0),
            'plan': user.get('plan', 'free'),
            'membership_name': get_membership_plan(user.get('plan', 'free')),
            'tasks_completed': user.get('tasks_completed', {})
        }
    })

@app.route('/api/user_data', methods=['GET'])
def user_data():
    """Get user data by telegram_id"""
    telegram_id = request.args.get('telegram_id')
    if not telegram_id:
        return jsonify({'success': False, 'error': 'No telegram_id provided'})
    
    user = get_user(telegram_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'})
    
    return jsonify({
        'success': True,
        'user': {
            'id': telegram_id,
            'first_name': user.get('first_name'),
            'points': user.get('points', 0),
            'plan': user.get('plan', 'free'),
            'membership_name': get_membership_plan(user.get('plan', 'free')),
            'tasks_completed': user.get('tasks_completed', {})
        }
    })

@app.route('/api/complete_task', methods=['POST'])
def api_complete_task():
    """Complete a social task via web"""
    data = request.json
    telegram_id = data.get('telegram_id')
    task_name = data.get('task_name')
    
    if not telegram_id or not task_name:
        return jsonify({'success': False, 'error': 'Missing parameters'})
    
    if task_name not in ['youtube', 'instagram', 'facebook']:
        return jsonify({'success': False, 'error': 'Invalid task'})
    
    if complete_task(telegram_id, task_name):
        user = get_user(telegram_id)
        return jsonify({
            'success': True,
            'message': 'Task completed! +100 points',
            'points': user.get('points', 0)
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Task already completed'
        })

@app.route('/api/submit_payment', methods=['POST'])
def submit_payment():
    """Submit payment proof for upgrade"""
    data = request.json
    telegram_id = data.get('telegram_id')
    amount = data.get('amount')
    transaction_id = data.get('transaction_id')
    screenshot = data.get('screenshot')  # base64 string
    
    if not telegram_id or not amount or not transaction_id:
        return jsonify({'success': False, 'error': 'Missing required fields'})
    
    if amount not in [100, 500]:
        return jsonify({'success': False, 'error': 'Invalid amount'})
    
    ref = get_db_ref()
    if ref:
        payment_data = {
            'user_id': telegram_id,
            'amount': amount,
            'transaction_id': transaction_id,
            'screenshot': screenshot,
            'status': 'pending',
            'submitted_at': datetime.now().isoformat()
        }
        payment_ref = ref.child('payments').push(payment_data)
        
        return jsonify({
            'success': True,
            'message': 'Payment submitted successfully! Admin will review shortly.',
            'payment_id': payment_ref.key
        })
    
    return jsonify({'success': False, 'error': 'Database error'})

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """AI Chat endpoint with points deduction"""
    data = request.json
    telegram_id = data.get('telegram_id')
    message = data.get('message')
    
    if not telegram_id or not message:
        return jsonify({'success': False, 'error': 'Missing parameters'})
    
    user = get_user(telegram_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'})
    
    cost = get_ai_cost(user.get('plan', 'free'))
    
    if user.get('points', 0) < cost:
        return jsonify({
            'success': False,
            'error': f'Insufficient points! Need {cost} points.',
            'points': user.get('points', 0)
        })
    
    # Deduct points
    new_points = deduct_points(telegram_id, cost)
    
    # Get AI response
    ai_response = call_deepseek_api([{"role": "user", "content": message}])
    
    return jsonify({
        'success': True,
        'response': ai_response,
        'points_deducted': cost,
        'remaining_points': new_points
    })

# -------------------- ADMIN ENDPOINTS --------------------
def admin_required(f):
    """Decorator to check admin authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/admin/login', methods=['POST'])
def admin_login():
    """Admin login endpoint"""
    data = request.json
    password = data.get('password')
    
    if password == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Invalid password'})

@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    return jsonify({'success': True})

@app.route('/admin/payments', methods=['GET'])
@admin_required
def admin_get_payments():
    """Get all pending payments"""
    ref = get_db_ref()
    if ref:
        payments = ref.child('payments').get()
        if payments:
            pending = []
            for pid, payment in payments.items():
                if payment.get('status') == 'pending':
                    # Get user details
                    user = ref.child(f'users/{payment["user_id"]}').get()
                    pending.append({
                        'id': pid,
                        'user_id': payment['user_id'],
                        'user_name': user.get('first_name', 'Unknown') if user else 'Unknown',
                        'amount': payment['amount'],
                        'transaction_id': payment['transaction_id'],
                        'screenshot': payment.get('screenshot', ''),
                        'submitted_at': payment['submitted_at']
                    })
            return jsonify({'success': True, 'payments': pending})
    return jsonify({'success': True, 'payments': []})

@app.route('/admin/approve_payment', methods=['POST'])
@admin_required
def admin_approve_payment():
    """Approve a payment and upgrade user"""
    data = request.json
    payment_id = data.get('payment_id')
    
    ref = get_db_ref()
    if ref:
        payment = ref.child(f'payments/{payment_id}').get()
        if payment:
            user_id = payment['user_id']
            amount = payment['amount']
            
            # Update payment status
            ref.child(f'payments/{payment_id}/status').set('approved')
            
            # Upgrade user based on amount
            if amount == 100:
                ref.child(f'users/{user_id}/plan').set('earner_pro')
                # Add bonus points
                current_points = ref.child(f'users/{user_id}/points').get() or 0
                ref.child(f'users/{user_id}/points').set(current_points + 500)
                plan_name = "Earner Pro"
                bonus = 500
            else:
                ref.child(f'users/{user_id}/plan').set('influencer_pro')
                current_points = ref.child(f'users/{user_id}/points').get() or 0
                ref.child(f'users/{user_id}/points').set(current_points + 2000)
                plan_name = "Influencer Pro"
                bonus = 2000
            
            # Send notification to user via Telegram
            send_telegram_message(int(user_id), 
                                f"✅ <b>Payment Approved!</b>\n\n"
                                f"Your upgrade to <b>{plan_name}</b> has been approved!\n"
                                f"🎁 You received {bonus} bonus points!\n\n"
                                f"Thank you for upgrading! 🎉")
            
            return jsonify({'success': True, 'message': 'Payment approved and user upgraded'})
    
    return jsonify({'success': False, 'error': 'Payment not found'})

@app.route('/admin/reject_payment', methods=['POST'])
@admin_required
def admin_reject_payment():
    """Reject a payment"""
    data = request.json
    payment_id = data.get('payment_id')
    
    ref = get_db_ref()
    if ref:
        payment = ref.child(f'payments/{payment_id}').get()
        if payment:
            ref.child(f'payments/{payment_id}/status').set('rejected')
            user_id = payment['user_id']
            
            send_telegram_message(int(user_id), 
                                f"❌ <b>Payment Rejected</b>\n\n"
                                f"Your payment could not be approved. Please check your transaction details and submit again.\n\n"
                                f"Contact support for assistance.")
            
            return jsonify({'success': True, 'message': 'Payment rejected'})
    
    return jsonify({'success': False, 'error': 'Payment not found'})

@app.route('/admin/broadcast', methods=['POST'])
@admin_required
def admin_broadcast():
    """Send broadcast message to all users"""
    data = request.json
    message = data.get('message')
    
    if not message:
        return jsonify({'success': False, 'error': 'No message provided'})
    
    ref = get_db_ref()
    if ref:
        users = ref.child('users').get()
        if users:
            sent_count = 0
            for user_id, user in users.items():
                try:
                    send_telegram_message(int(user_id), f"📢 <b>Broadcast Message</b>\n\n{message}")
                    sent_count += 1
                except:
                    pass
            return jsonify({'success': True, 'sent': sent_count, 'total': len(users)})
    
    return jsonify({'success': False, 'error': 'No users found'})

@app.route('/admin/task_links', methods=['GET'])
@admin_required
def admin_get_task_links():
    """Get current task links"""
    ref = get_db_ref()
    if ref:
        links = ref.child('config/task_links').get() or {}
        return jsonify({'success': True, 'links': links})
    return jsonify({'success': True, 'links': {}})

@app.route('/admin/task_links', methods=['POST'])
@admin_required
def admin_update_task_links():
    """Update task links"""
    data = request.json
    youtube = data.get('youtube')
    instagram = data.get('instagram')
    facebook = data.get('facebook')
    
    ref = get_db_ref()
    if ref:
        links = {}
        if youtube:
            links['youtube'] = youtube
        if instagram:
            links['instagram'] = instagram
        if facebook:
            links['facebook'] = facebook
        
        ref.child('config/task_links').set(links)
        return jsonify({'success': True, 'message': 'Links updated'})
    
    return jsonify({'success': False, 'error': 'Database error'})

# -------------------- WEB PAGES --------------------
@app.route('/dashboard')
def dashboard():
    """Serve dashboard HTML"""
    return render_template('dashboard.html')

@app.route('/admin')
def admin_panel():
    """Serve admin panel HTML"""
    return render_template('admin.html')

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    """Set Telegram webhook to current URL"""
    # Get the base URL from request
    base_url = request.url_root.rstrip('/')
    webhook_url = f"{base_url}/webhook"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
    response = requests.post(url, json={'url': webhook_url})
    
    if response.status_code == 200:
        return jsonify({'success': True, 'message': f'Webhook set to {webhook_url}', 'response': response.json()})
    else:
        return jsonify({'success': False, 'error': response.text})

@app.route('/')
def index():
    """Root endpoint"""
    return jsonify({
        'name': 'Ultimate Media Search Bot',
        'version': '1.0.0',
        'endpoints': {
            'webhook': '/webhook',
            'dashboard': '/dashboard',
            'admin': '/admin',
            'set_webhook': '/set_webhook'
        }
    })

# -------------------- MAIN --------------------
if __name__ == '__main__':
    app.run(debug=True, port=5000)
