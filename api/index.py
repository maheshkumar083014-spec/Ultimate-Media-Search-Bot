import os
import json
import telebot
from flask import Flask, request, render_template, jsonify
import firebase_admin
from firebase_admin import credentials, db
from openai import OpenAI

# --- PATH & FLASK CONFIG ---
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
template_path = os.path.join(base_dir, 'templates')
app = Flask(__name__, template_folder=template_path)

# --- CONFIGURATION ---
BOT_TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
FB_URL = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"
DEEPSEEK_KEY = "sk-783d645ce9e84eb8b954786a016561ea"

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
ai_client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

# --- FIREBASE INITIALIZATION ---
if not firebase_admin._apps:
    fb_config = os.getenv("FIREBASE_SERVICE_ACCOUNT")
    if fb_config:
        try:
            cred_dict = json.loads(fb_config)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {'databaseURL': FB_URL})
        except Exception as e:
            print(f"Firebase Init Error: {e}")

# --- DASHBOARD & API ROUTES ---

@app.route('/')
def index():
    return "Bot & Dashboard Server is Live!"

@app.route('/dashboard')
def dashboard():
    # Frontend ke liye empty config bhej rahe hain kyunki hum direct API use karenge
    return render_template('dashboard.html', firebase_config="{}")

# 1. API: Get User Data for Dashboard
@app.route('/api/user/<user_id>', methods=['GET'])
def get_user_data(user_id):
    user_ref = db.reference(f'users/{user_id}')
    user = user_ref.get()
    if not user:
        # Agar user nahi milta toh default data bhejenge
        return jsonify({
            "user_id": user_id, "points": 0, "plan": "Free", 
            "tasks_completed": [], "username": "Guest"
        })
    return jsonify(user)

# 2. API: Handle AI Chat from Dashboard
@app.route('/api/ai/chat', methods=['POST'])
def ai_chat_api():
    data = request.json
    user_id = data.get('user_id')
    user_msg = data.get('message')
    
    user_ref = db.reference(f'users/{user_id}')
    user = user_ref.get()
    
    if not user: return jsonify({"success": False, "response": "User not found"})

    # Point deduction logic
    cost = 10 if user.get('plan') == "Free" else 0
    if user.get('points', 0) < cost:
        return jsonify({"success": False, "response": "Points khatam! Task karein."})

    try:
        response = ai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": user_msg}]
        )
        ai_resp = response.choices[0].message.content
        
        # Update Points
        new_balance = user['points'] - cost
        user_ref.update({"points": new_balance})
        
        return jsonify({"success": True, "response": ai_resp, "cost": cost, "balance": new_balance})
    except:
        return jsonify({"success": False, "response": "AI is busy. Try later."})

# 3. API: Complete Tasks
@app.route('/api/tasks/complete', methods=['POST'])
def complete_task_api():
    data = request.json
    user_id = data.get('user_id')
    task_id = data.get('task_id')
    
    user_ref = db.reference(f'users/{user_id}')
    user = user_ref.get()
    
    if not user: return jsonify({"success": False})
    
    completed = user.get('tasks_completed', [])
    if task_id in completed:
        return jsonify({"success": False, "message": "Already done"})
    
    completed.append(task_id)
    new_balance = user.get('points', 0) + 100
    user_ref.update({"points": new_balance, "tasks_completed": completed})
    
    return jsonify({"success": True, "points_earned": 100, "new_balance": new_balance})

# --- TELEGRAM WEBHOOK ---
@app.route('/api/index', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    return "Forbidden", 403

# --- BOT LOGIC ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    user_ref = db.reference(f'users/{user_id}')
    user_data = user_ref.get()
    
    if not user_data:
        user_data = {"user_id": user_id, "points": 100, "plan": "Free", "username": message.from_user.first_name, "tasks_completed": []}
        user_ref.set(user_data)
    
    # Dashboard Link with UserID
    dashboard_url = f"https://{request.host}/dashboard"
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", url=dashboard_url))
    
    bot.send_message(message.chat.id, f"Hello {user_data['username']}! Dashboard check karein.", reply_markup=markup)

app = app
