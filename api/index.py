import os
import json
import logging
import requests
import telebot
from flask import Flask, request, jsonify, render_template_string, redirect

# 1. Setup Logging (Vercel ke liye zaroori)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 2. Configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw')
FIREBASE_DB_URL = os.environ.get('FIREBASE_DATABASE_URL', 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/').rstrip('/')

# Telegram Bot Setup
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML', threaded=False)

# Flask App Setup
app = Flask(__name__, static_folder='../static', template_folder='../templates')

# Banner Image URL
BANNER_IMAGE = "https://i.ibb.co/9kmTw4Gh/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg"

# 3. Database Helpers (Firebase REST API)
def fb_get(path):
    try:
        r = requests.get(f"{FIREBASE_DB_URL}/{path}.json", timeout=10)
        return r.json() if r.status_code == 200 else None
    except: return None

def fb_set(path, data):
    try:
        r = requests.put(f"{FIREBASE_DB_URL}/{path}.json", json=data, timeout=10)
        return r.status_code in [200, 201]
    except: return False

def fb_update(path, data):
    try:
        r = requests.patch(f"{FIREBASE_DB_URL}/{path}.json", json=data, timeout=10)
        return r.status_code in [200, 201]
    except: return False

def create_user(uid, name):
    # User create karna
    user = {'uid': uid, 'name': name, 'points': 0, 'total_earned': 0}
    fb_set(f'users/{uid}', user)
    return user

# 4. Telegram /start Handler
@bot.message_handler(commands=['start'])
def handle_start(message):
    uid = message.from_user.id
    name = message.from_user.first_name or "User"
    
    # User ko database mein save karo
    if not fb_get(f'users/{uid}'):
        create_user(uid, name)
    
    # Welcome Message + Photo
    caption = f"""🌟 Welcome back, <b>{name}</b>!

💬 <i>"Your smartphone is now your ATM. Stop scrolling for free—start earning for your time! 💰✨"</i>

📊 <b>YOUR AD-EARNING DASHBOARD</b>

🎁 <b>How to Earn:</b>
├ 📺 Ads → +25 pts
├ 📱 Social → +100 pts
└ 💰 <b>100 pts = $1.00</b>

👇 Open Dashboard Below!"""

    # Inline Keyboard Button
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    btn = telebot.types.InlineKeyboardButton("🚀 Open Premium Dashboard", url="/dashboard?id={}&name={}".format(uid, name))
    markup.add(btn)
    
    # Photo + Text Send karna
    try:
        bot.send_photo(message.chat.id, photo=BANNER_IMAGE, caption=caption, reply_markup=markup)
    except Exception as e:
        logger.error(f"Photo send error: {e}")
        bot.send_message(message.chat.id, caption, reply_markup=markup)

# 5. Flask Routes

# Webhook Route
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        update = telebot.types.Update.de_json(request.get_json(force=True))
        bot.process_new_updates([update])
        return '', 200

# Dashboard Route (HTML Inline taaki koi error na aaye)
@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    
    # Premium Dashboard HTML
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ultimate Media Search</title>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-database-compat.js"></script>
<style>
body{font-family:sans-serif;background:linear-gradient(180deg,#fef3c7,#f59e0b 40%,#92400e);color:#292524;margin:0;padding:20px;text-align:center}
.card{background:rgba(255,255,255,0.9);border-radius:20px;padding:20px;margin:20px 0;box-shadow:0 10px 30px rgba(0,0,0,0.2)}
h1{font-size:24px;color:#78350f}
.stat{font-size:32px;font-weight:bold;color:#d97706}
.btn{background:#78350f;color:white;padding:12px 24px;border-radius:12px;text-decoration:none;font-weight:bold;display:inline-block;margin:10px}
</style>
</head>
<body>
<div class="card">
<img src="https://i.ibb.co/9kmTw4Gh/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg" style="width:100%;border-radius:15px;margin-bottom:15px">
<h1>Welcome, {{ name }}!</h1>
<p>Your smartphone is now your ATM 💰</p>
<div class="stat" id="points">Loading...</div>
<p>Total Points</p>
<a href="#" class="btn">💸 Request Payout</a>
<a href="#" class="btn" style="background:#2563eb">📺 Watch Ad</a>
</div>
<script>
const fbConfig = { apiKey: "AIzaSyD50eWvysruXgtgpDhhCVE2zdbSbLkFBwk", authDomain: "ultimatemediasearch.firebaseapp.com", databaseURL: "{{ db_url }}", projectId: "ultimatemediasearch", storageBucket: "ultimatemediasearch.firebasestorage.app", messagingSenderId: "123003124713", appId: "1:123003124713:web:c738c97b2772b112822978" };
firebase.initializeApp(fbConfig);
const db = firebase.database();
db.ref('users/{{ uid }}/points').on('value', snap => {
    document.getElementById('points').innerText = (snap.val() || 0).toLocaleString();
});
</script>
</body>
</html>"""
    
    return render_template_string(html, name=name, uid=uid, db_url=FIREBASE_DB_URL)

# Welcome Route
@app.route('/welcome')
def welcome():
    return """<h1 style="text-align:center;margin-top:50px">Welcome to Ultimate Media Search! 🚀</h1>"""

# Admin Route
@app.route('/admin')
def admin():
    return """<h1 style="text-align:center;margin-top:50px">🔒 Admin Panel Locked</h1>"""

# API Route
@app.route('/api/earn', methods=['POST'])
def api_earn():
    data = request.get_json()
    uid = data.get('user_id')
    if uid:
        # Points add karna
        user = fb_get(f'users/{uid}')
        if user:
            new_pts = (user.get('points', 0) or 0) + 25
            fb_update(f'users/{uid}', {'points': new_pts})
            return jsonify({'success': True, 'points': new_pts})
    return jsonify({'success': False})

# Health Check
@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

# Vercel ke liye entry point
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
