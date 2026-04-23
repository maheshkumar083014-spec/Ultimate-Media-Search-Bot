import os
import json
import telebot
from flask import Flask, request, render_template, jsonify
import firebase_admin
from firebase_admin import credentials, db
from openai import OpenAI

app = Flask(__name__)

# --- CONFIGURATION ---
BOT_TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
FB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"
DEEPSEEK_KEY = "sk-783d645ce9e84eb8b954786a016561ea"
WELCOME_IMAGE = "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg"

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
ai_client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

# --- FIREBASE INIT ---
if not firebase_admin._apps:
    fb_config = os.getenv("FIREBASE_SERVICE_ACCOUNT")
    if fb_config:
        cred = credentials.Certificate(json.loads(fb_config))
        firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})

# --- WEB ROUTES ---
@app.route('/')
def home(): return "Server Active"

@app.route('/dashboard')
def dashboard(): return render_template('dashboard.html')

@app.route('/admin')
def admin(): return render_template('admin.html')

# --- API ENDPOINTS ---
@app.route('/api/user/<user_id>')
def get_user(user_id):
    return jsonify(db.reference(f'users/{user_id}').get() or {})

@app.route('/api/admin/stats')
def admin_stats():
    users = db.reference('users').get() or {}
    return jsonify({"total_users": len(users), "revenue": "₹50,000+"})

@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    data = request.json
    u_id = data.get('user_id')
    user_ref = db.reference(f'users/{u_id}')
    user = user_ref.get()
    
    cost = 10 if user.get('plan') == "Free" else 0
    if user.get('points', 0) < cost:
        return jsonify({"success": False, "msg": "Insufficient Points!"})

    resp = ai_client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": data.get('message')}]
    )
    user_ref.update({"points": user['points'] - cost})
    return jsonify({"success": True, "response": resp.choices[0].message.content})

# --- BOT LOGIC ---
@bot.message_handler(commands=['start'])
def start(message):
    u_id = str(message.from_user.id)
    u_ref = db.reference(f'users/{u_id}')
    user = u_ref.get() or {"points": 100, "plan": "Free", "name": message.from_user.first_name}
    if not u_ref.get(): u_ref.set(user)

    caption = f"🚀 *Welcome {user['name']}!*\n\n💰 *Balance:* {user['points']} Points\n💎 *Plan:* {user['plan']}"
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", url=f"https://{request.host}/dashboard"))
    bot.send_photo(message.chat.id, WELCOME_IMAGE, caption=caption, parse_mode="Markdown", reply_markup=markup)

@app.route('/api/index', methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "OK", 200

app = app
