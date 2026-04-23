from flask import Flask, request, jsonify, render_template, redirect
import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, firestore, auth
from datetime import datetime, timedelta
import os
import hashlib
import secrets

app = Flask(__name__)

# Initialize Firebase Admin
cred = credentials.Certificate({
    "type": "service_account",
    "project_id": os.environ.get('FIREBASE_PROJECT_ID'),
    "private_key_id": os.environ.get('FIREBASE_PRIVATE_KEY_ID'),
    "private_key": os.environ.get('FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),
    "client_email": os.environ.get('FIREBASE_CLIENT_EMAIL'),
    "client_id": os.environ.get('FIREBASE_CLIENT_ID'),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": os.environ.get('FIREBASE_CLIENT_X509_CERT_URL')
})
firebase_admin.initialize_app(cred)
db = firestore.client()

# Telegram Bot Configuration
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))

# Security helper
def generate_secure_token():
    return secrets.token_urlsafe(32)

def verify_telegram_data(data):
    """Verify Telegram WebApp data"""
    hash_val = data.pop('hash', None)
    if not hash_val:
        return False
    
    data_check_arr = []
    for key, value in sorted(data.items()):
        data_check_arr.append(f'{key}={value}')
    
    data_check_string = '\n'.join(data_check_arr)
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    calculated_hash = hashlib.sha256(data_check_string.encode(), secret_key).hexdigest()
    
    return calculated_hash == hash_val

# Bot Commands
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    
    # Create or update user in Firestore
    user_ref = db.collection('users').document(str(user_id))
    user_doc = user_ref.get()
    
    if not user_doc.exists:
        user_ref.set({
            'userId': str(user_id),
            'name': name,
            'username': message.from_user.username or '',
            'balance': 0,
            'adsViewed': 0,
            'totalEarned': 0,
            'joinedAt': firestore.SERVER_TIMESTAMP,
            'lastActive': firestore.SERVER_TIMESTAMP,
            'isBanned': False
        })
    else:
        user_ref.update({
            'lastActive': firestore.SERVER_TIMESTAMP,
            'name': name
        })
    
    # Send welcome photo
    photo_url = "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg"
    
    markup = types.InlineKeyboardMarkup()
    dashboard_url = f"https://ultimate-media-search-bot-t7kj.vercel.app/dashboard?id={user_id}&name={name}"
    btn = types.InlineKeyboardButton("Open Dashboard 🚀", url=dashboard_url)
    markup.add(btn)
    
    caption = (
        f"👋 <b>Welcome, {name}!</b>\n\n"
        "🎯 <b>Ultimate Media Search Bot</b>\n\n"
        "✨ Earn money by completing simple tasks:\n"
        "• View Ads: +25 points\n"
        "• Social Tasks: +100 points\n"
        "• Daily Rewards available!\n\n"
        "💰 <b>Withdrawal:</b> $1 = 100 points\n\n"
        "🚀 Click below to start earning!"
    )
    
    bot.send_photo(message.chat.id, photo_url, caption=caption, reply_markup=markup)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Access Denied")
        return
    
    markup = types.InlineKeyboardMarkup()
    admin_url = f"https://ultimate-media-search-bot-t7kj.vercel.app/admin?token={generate_secure_token()}"
    btn = types.InlineKeyboardButton("Open Admin Panel 🔧", url=admin_url)
    markup.add(btn)
    
    bot.reply_to(message, "🔧 Admin Panel Access", reply_markup=markup)

# Webhook Handler
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data(as_text=True)
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return '', 400

@app.route('/')
def index():
    return "Ultimate Media Search Bot API is running..."

# Dashboard Route
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# Admin Route
@app.route('/admin')
def admin():
    return render_template('admin.html')

# API Endpoints
@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    user_ref = db.collection('users').document(user_id)
    user_doc = user_ref.get()
    
    if user_doc.exists:
        user_data = user_doc.to_dict()
        return jsonify({
            'success': True,
            'data': user_data
        })
    return jsonify({'success': False, 'error': 'User not found'}), 404

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    tasks_ref = db.collection('tasks').where('active', '==', True).order_by('createdAt', direction=firestore.Query.DESCENDING)
    tasks = tasks_ref.stream()
    
    task_list = []
    for task in tasks:
        task_data = task.to_dict()
        task_data['id'] = task.id
        task_list.append(task_data)
    
    return jsonify({'success': True, 'tasks': task_list})

@app.route('/api/complete-task', methods=['POST'])
def complete_task():
    data = request.json
    user_id = data.get('userId')
    task_id = data.get('taskId')
    task_type = data.get('type')  # 'ad' or 'social'
    
    if not all([user_id, task_id, task_type]):
        return jsonify({'success': False, 'error': 'Missing parameters'}), 400
    
    # Use Firestore transaction to prevent race conditions
    @firestore.transactional
    def update_in_transaction(transaction, user_ref, task_ref):
        user_doc = user_ref.get(transaction=transaction)
        if not user_doc.exists:
            return False
        
        user_data = user_doc.to_dict()
        if user_data.get('isBanned'):
            return False
        
        # Check if task already completed today
        today = datetime.now().date().isoformat()
        completed_tasks = user_data.get('completedTasks', {})
        
        if task_id in completed_tasks.get(today, []):
            return False  # Already completed today
        
        # Calculate points
        points = 25 if task_type == 'ad' else 100
        
        # Update user
        new_balance = user_data.get('balance', 0) + points
        new_total = user_data.get('totalEarned', 0) + points
        
        if task_type == 'ad':
            new_ads_viewed = user_data.get('adsViewed', 0) + 1
            transaction.update(user_ref, {
                'balance': new_balance,
                'totalEarned': new_total,
                'adsViewed': new_ads_viewed,
                'lastActive': firestore.SERVER_TIMESTAMP
            })
        else:
            transaction.update(user_ref, {
                'balance': new_balance,
                'totalEarned': new_total,
                'lastActive': firestore.SERVER_TIMESTAMP
            })
        
        # Update completed tasks
        if today not in completed_tasks:
            completed_tasks[today] = []
        completed_tasks[today].append(task_id)
        transaction.update(user_ref, {'completedTasks': completed_tasks})
        
        return True
    
    user_ref = db.collection('users').document(user_id)
    task_ref = db.collection('tasks').document(task_id)
    transaction = db.transaction()
    
    success = update_in_transaction(transaction, user_ref, task_ref)
    
    if success:
        return jsonify({'success': True, 'points': 25 if task_type == 'ad' else 100})
    return jsonify({'success': False, 'error': 'Task already completed or invalid'}), 400

@app.route('/api/withdraw', methods=['POST'])
def request_withdrawal():
    data = request.json
    user_id = data.get('userId')
    amount = data.get('amount')  # in points
    payment_method = data.get('paymentMethod')
    payment_details = data.get('paymentDetails')
    
    if not all([user_id, amount, payment_method, payment_details]):
        return jsonify({'success': False, 'error': 'Missing parameters'}), 400
    
    amount = int(amount)
    if amount < 100:  # Minimum $1
        return jsonify({'success': False, 'error': 'Minimum withdrawal is 100 points ($1)'}), 400
    
    @firestore.transactional
    def process_withdrawal(transaction, user_ref):
        user_doc = user_ref.get(transaction=transaction)
        if not user_doc.exists:
            return False
        
        user_data = user_doc.to_dict()
        if user_data.get('balance', 0) < amount:
            return False
        
        # Deduct balance
        transaction.update(user_ref, {
            'balance': user_data['balance'] - amount
        })
        
        # Create withdrawal request
        withdrawal_ref = db.collection('withdrawals').document()
        transaction.set(withdrawal_ref, {
            'userId': user_id,
            'userName': user_data.get('name', ''),
            'amount': amount,
            'amountUSD': amount / 100,
            'paymentMethod': payment_method,
            'paymentDetails': payment_details,
            'status': 'pending',
            'createdAt': firestore.SERVER_TIMESTAMP
        })
        
        return True
    
    user_ref = db.collection('users').document(user_id)
    transaction = db.transaction()
    success = process_withdrawal(transaction, user_ref)
    
    if success:
        return jsonify({'success': True, 'message': 'Withdrawal request submitted'})
    return jsonify({'success': False, 'error': 'Insufficient balance'}), 400

@app.route('/api/broadcast', methods=['POST'])
def broadcast():
    # Verify admin
    auth_header = request.headers.get('Authorization')
    if auth_header != os.environ.get('ADMIN_SECRET'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    data = request.json
    message_text = data.get('message')
    task_id = data.get('taskId')
    
    if not message_text:
        return jsonify({'success': False, 'error': 'Message required'}), 400
    
    # Get all users
    users_ref = db.collection('users').where('isBanned', '==', False).stream()
    sent_count = 0
    
    for user_doc in users_ref:
        user_data = user_doc.to_dict()
        user_id = user_data.get('userId')
        
        try:
            if task_id:
                markup = types.InlineKeyboardMarkup()
                dashboard_url = f"https://ultimate-media-search-bot-t7kj.vercel.app/dashboard?id={user_id}&task={task_id}"
                btn = types.InlineKeyboardButton("Complete Task Now 🎯", url=dashboard_url)
                markup.add(btn)
                bot.send_message(user_id, message_text, reply_markup=markup)
            else:
                bot.send_message(user_id, message_text)
            sent_count += 1
        except Exception as e:
            print(f"Failed to send to {user_id}: {e}")
            continue
    
    return jsonify({'success': True, 'sentTo': sent_count})

if __name__ == '__main__':
    # Set webhook for Vercel
    webhook_url = f"{os.environ.get('VERCEL_URL')}/webhook"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
