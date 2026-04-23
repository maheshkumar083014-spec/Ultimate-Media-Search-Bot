import os
import json
import time
import hashlib
import requests
from flask import Flask, request, jsonify, render_template
import telebot
from telebot import types
from firebase_admin import db, initialize_app
from openai import OpenAI

app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'))

# Credentials
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw')
FIREBASE_DB_URL = os.environ.get('FIREBASE_DATABASE_URL', 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', 'sk-783d645ce9e84eb8b954786a016561ea')
ADMIN_TELEGRAM_ID = os.environ.get('ADMIN_TELEGRAM_ID', '123456789')
UPI_ID = os.environ.get('UPI_ID', '8543083014@ikwik')
QR_CODE_URL = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={UPI_ID}"

# Initialize Firebase
try:
    initialize_app(options={'databaseURL': FIREBASE_DB_URL})
except:
    pass

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

deepseek_client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1"
)

def get_user_data(user_id):
    try:
        return db.reference(f'users/{user_id}').get()
    except:
        return None

def update_user_data(user_id, data):
    try:
        db.reference(f'users/{user_id}').update(data)
        return True
    except:
        return False

def register_user(user_id, username, first_name, referral_code=None):
    user_data = {
        'user_id': user_id,
        'username': username,
        'first_name': first_name,
        'balance': 0,
        'is_premium': False,
        'referral_code': hashlib.md5(str(user_id).encode()).hexdigest()[:8],
        'referred_by': referral_code,
        'total_messages': 0,
        'joined_at': int(time.time()),
        'last_active': int(time.time()),
        'pending_payments': []
    }
    
    if referral_code:
        try:
            all_users = db.reference('users').get() or {}
            for uid, data in all_users.items():
                if data.get('referral_code') == referral_code:
                    db.reference(f'users/{uid}').update({'balance': data.get('balance', 0) + 50})
                    user_data['balance'] = 25
                    break
        except:
            pass
    
    db.reference(f'users/{user_id}').set(user_data)
    return user_data

def generate_ai_response(message):
    try:
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are Ultimate Media Search AI Assistant."},
                {"role": "user", "content": message}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI Error: {str(e)}"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username or 'User'
        first_name = message.from_user.first_name
        
        user_data = get_user_data(user_id)
        if not user_data:
            ref = message.text.split()[1] if len(message.text.split()) > 1 else None
            user_data = register_user(user_id, username, first_name, ref)
        
        update_user_data(user_id, {'last_active': int(time.time())})
        
        balance = user_data.get('balance', 0)
        status = "🌟 PREMIUM" if user_data.get('is_premium') else "⚡ FREE"
        
        caption = f"""👋 Welcome {first_name}!

💰 Balance: {balance} pts
🎫 Status: {status}
👥 Code: <code>{user_data.get('referral_code')}</code>

/ai - Chat with AI
/dashboard - Web Dashboard
/help - Help
"""
        
        bot.send_photo(message.chat.id, "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg", 
                      caption=caption, reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add('/ai', '/dashboard'))
    except Exception as e:
        print(f"Start error: {e}")

@bot.message_handler(commands=['ai'])
def ai_chat(message):
    try:
        user_id = message.from_user.id
        user_data = get_user_data(user_id)
        
        if not user_data:
            bot.reply_to(message, "Please /start first")
            return
        
        if not user_data.get('is_premium') and user_data.get('balance', 0) < 10:
            bot.reply_to(message, "❌ Need 10 pts. /dashboard to earn!")
            return
        
        if not user_data.get('is_premium'):
            db.reference(f'users/{user_id}').update({'balance': user_data['balance'] - 10})
        
        msg = message.text.replace('/ai', '').strip()
        if not msg:
            bot.reply_to(message, "Type: /ai your question")
            return
        
        bot.send_chat_action(message.chat.id, 'typing')
        response = generate_ai_response(msg)
        bot.reply_to(message, f"🤖 {response}")
    except Exception as e:
        print(f"AI error: {e}")
        bot.reply_to(message, "Error occurred")

@bot.message_handler(commands=['dashboard'])
def dashboard_cmd(message):
    try:
        user_id = message.from_user.id
        if not get_user_data(user_id):
            bot.reply_to(message, "Please /start first")
            return
        
        vercel_url = os.environ.get('VERCEL_URL', 'localhost:5000')
        url = f"https://{vercel_url}/dashboard?uid={user_id}"
        
        bot.send_message(message.chat.id, f"🔗 Dashboard:\n{url}")
    except Exception as e:
        print(f"Dashboard error: {e}")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(message, """
📚 Commands:
/start - Start bot
/ai - Chat with AI (10 pts)
/dashboard - Web panel
/help - This message

💰 Earn: Daily tasks, referrals
🌟 Premium: Unlimited AI
""")

@app.route('/')
def home():
    return jsonify({"status": "running", "message": "Ultimate Media Search Bot API"})

@app.route('/dashboard')
def dashboard():
    try:
        user_id = request.args.get('uid')
        if not user_id:
            return jsonify({"error": "Missing uid"}), 400
        
        user_data = get_user_data(user_id)
        if not user_data:
            return jsonify({"error": "User not found"}), 404
        
        return render_template('dashboard.html', 
                             user=user_data,
                             upi_id=UPI_ID,
                             qr_code=QR_CODE_URL,
                             social_links={'youtube': '@USSoccerPulse', 'instagram': '@digital_rockstar_m', 'facebook': 'UltimateMediaSearch'})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin')
def admin():
    try:
        return render_template('admin.html', pending_payments=[], admin_id=ADMIN_TELEGRAM_ID)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def api_chat():
    try:
        data = request.json
        user_id = data.get('user_id')
        message = data.get('message')
        
        user_data = get_user_data(user_id)
        if not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        if not user_data.get('is_premium'):
            if user_data.get('balance', 0) < 10:
                return jsonify({'error': 'Insufficient balance'}), 402
            db.reference(f'users/{user_id}').update({'balance': user_data['balance'] - 10})
        
        response = generate_ai_response(message)
        return jsonify({'response': response, 'remaining_balance': get_user_data(user_id).get('balance', 0)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.get_json(force=True))
        bot.process_new_updates([update])
        return '', 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return '', 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
