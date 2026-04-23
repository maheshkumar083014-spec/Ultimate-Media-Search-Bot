import os
import json
import telebot
import time
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
ADMIN_SECRET_KEY = "SUPER_SECRET_ADMIN_123" # Ise apne admin.html se match karein

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
ai_client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

# --- FIREBASE INIT ---
if not firebase_admin._apps:
    fb_config = os.getenv("FIREBASE_SERVICE_ACCOUNT")
    if fb_config:
        try:
            cred = credentials.Certificate(json.loads(fb_config))
            firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})
        except Exception as e:
            print(f"Firebase Init Error: {e}")

# --- WEB & ADMIN ROUTES ---
@app.route('/')
def home(): return "Bot & Dashboard Server is Live!"

@app.route('/dashboard')
def dashboard(): return render_template('dashboard.html')

@app.route('/admin')
def admin_panel():
    users_ref = db.reference('users').get() or {}
    pending_ref = db.reference('submissions').order_by_child('status').equal_to('pending').get() or {}
    
    pending_list = []
    for sid, data in pending_ref.items():
        data['id'] = sid
        pending_list.append(data)

    stats = {
        "total_users": len(users_ref),
        "pending_reviews": len(pending_list)
    }
    return render_template('admin.html', stats=stats, pending=pending_list, admin_key=ADMIN_SECRET_KEY)

# --- ADMIN API LOGIC ---
@app.route('/api/admin/review', methods=['POST'])
def review_submission():
    if request.headers.get('X-Admin-Key') != ADMIN_SECRET_KEY:
        return jsonify({"success": False}), 403
    
    data = request.json
    sid, approved, reason = data.get('submission_id'), data.get('approved'), data.get('reason')
    
    sub_ref = db.reference(f'submissions/{sid}')
    submission = sub_ref.get()
    if not submission: return jsonify({"success": False})

    u_id = submission.get('user_id')
    if approved:
        u_ref = db.reference(f'users/{u_id}')
        u_ref.update({"points": (u_ref.child('points').get() or 0) + submission.get('points', 0)})
        try: bot.send_message(u_id, f"✅ *Task Approved!*\nPoints credited successfully.", parse_mode="Markdown")
        except: pass
    else:
        try: bot.send_message(u_id, f"❌ *Task Rejected*\nReason: {reason}", parse_mode="Markdown")
        except: pass

    sub_ref.update({"status": "approved" if approved else "rejected"})
    return jsonify({"success": True})

@app.route('/api/admin/broadcast', methods=['POST'])
def broadcast():
    if request.headers.get('X-Admin-Key') != ADMIN_SECRET_KEY: return jsonify({"success": False}), 403
    msg = request.json.get('message')
    users = db.reference('users').get() or {}
    count = 0
    for uid in users:
        try:
            bot.send_message(uid, f"📢 *Alert*\n\n{msg}", parse_mode="Markdown")
            count += 1
        except: continue
    return jsonify({"success": True, "data": {"sent": count}})

# --- BOT & AI LOGIC ---
@bot.message_handler(commands=['start'])
def start(message):
    u_id = str(message.from_user.id)
    u_ref = db.reference(f'users/{u_id}')
    user = u_ref.get() or {"points": 100, "plan": "Free", "name": message.from_user.first_name}
    if not u_ref.get(): u_ref.set(user)

    caption = f"🚀 *Hello {user['name']}!*\n\n💰 Balance: {user.get('points', 0)} Pts\n💎 Plan: {user.get('plan', 'Free')}"
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", url=f"https://{request.host}/dashboard"))
    bot.send_photo(message.chat.id, WELCOME_IMAGE, caption=caption, parse_mode="Markdown", reply_markup=markup)

@app.route('/api/index', methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "OK", 200

app = app
