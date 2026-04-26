import os
import json
import hmac
import hashlib
import time
from functools import wraps
from urllib.parse import unquote

import telebot
from telebot import types
from flask import Flask, request, session, render_template, jsonify, redirect, url_for

import firebase_admin
from firebase_admin import credentials, db

# ------------------------------
# Environment variables
# ------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
FIREBASE_DB_URL = os.environ.get("FIREBASE_DB_URL")
FIREBASE_SERVICE_ACCOUNT = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")  # change in production
SECRET_KEY = os.environ.get("SECRET_KEY", "super-secret-key")
BOT_USERNAME = os.environ.get("BOT_USERNAME")  # e.g., "YourEarnBot"

# ------------------------------
# Flask app & sessions
# ------------------------------
app = Flask(__name__, template_folder="templates")
app.secret_key = SECRET_KEY

# ------------------------------
# Firebase initialization
# ------------------------------
cred_dict = json.loads(FIREBASE_SERVICE_ACCOUNT)
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred, {
    "databaseURL": FIREBASE_DB_URL
})

# ------------------------------
# Telegram Bot initialization
# ------------------------------
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)  # threaded=False for Vercel

# ------------------------------
# Task definitions
# ------------------------------
TASKS = [
    {
        "id": "yt_soccer",
        "name": "Subscribe to US Soccer Pulse",
        "url": "https://youtube.com/@USSoccerPulse",
        "points": 10,
        "button_text": "Subscribe on YouTube",
    },
    {
        "id": "ig_digital",
        "name": "Follow on Instagram",
        "url": "https://instagram.com/digital_rockstar_m",
        "points": 10,
        "button_text": "Follow on Instagram",
    },
    {
        "id": "fb_page",
        "name": "Like our Facebook page",
        "url": "https://facebook.com/YourFBPage",   # replace with actual link
        "points": 10,
        "button_text": "Like on Facebook",
    },
]

# ------------------------------
# Helper functions
# ------------------------------
def get_user_ref(user_id):
    return db.reference(f"users/{user_id}")

def register_user(user_id, username):
    """Create user if not already present."""
    ref = get_user_ref(user_id)
    if not ref.get():
        ref.set({
            "user_id": user_id,
            "points": 0,
            "status": "active",
            "username": username or str(user_id),
            "joined_at": time.time()
        })

def complete_task(user_id, task_id):
    """Mark a task as completed and add points."""
    user_ref = get_user_ref(user_id)
    user_data = user_ref.get() or {}
    completed = user_data.get("completed_tasks", {})
    if task_id not in completed:
        task_points = next(t["points"] for t in TASKS if t["id"] == task_id)
        user_ref.child("points").set(user_data.get("points", 0) + task_points)
        user_ref.child("completed_tasks").child(task_id).set(True)
        return True
    return False

def verify_telegram_login(auth_data):
    """Validate Telegram login widget data using bot token."""
    check_hash = auth_data.pop("hash", None)
    data_check_arr = [
        f"{key}={value}" for key, value in sorted(auth_data.items())
    ]
    data_check_string = "\n".join(data_check_arr)
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    hmac_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    return hmac_hash == check_hash

# ------------------------------
# Routes – Web dashboard & admin
# ------------------------------

@app.route("/webhook", methods=["POST", "GET"])
def webhook():
    if request.method == "POST":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    return "OK", 200

@app.route("/dashboard")
def dashboard():
    # Pass bot username to template for Telegram login widget
    return render_template("dashboard.html", bot_username=BOT_USERNAME)

@app.route("/auth/telegram", methods=["POST"])
def auth_telegram():
    data = request.get_json()
    if not data or not verify_telegram_login(data.copy()):
        return jsonify({"error": "Invalid authentication"}), 403
    session["user_id"] = data["id"]
    return jsonify({"success": True})

@app.route("/api/user")
def api_user():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    user_data = get_user_ref(user_id).get() or {}
    return jsonify(user_data)

@app.route("/api/tasks")
def api_tasks():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    user_data = get_user_ref(user_id).get() or {}
    completed = user_data.get("completed_tasks", {})
    for task in TASKS:
        task["completed"] = task["id"] in completed
    return jsonify(TASKS)

# ------------------------------
# Admin panel (simple login)
# ------------------------------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))
        return render_template("admin.html", error="Wrong password")
    if not session.get("admin_logged_in"):
        return render_template("admin.html", login=True)
    return render_template("admin.html", logged_in=True)

# Admin API endpoints
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route("/admin/api/users")
@admin_required
def admin_users():
    users_ref = db.reference("users").get()
    return jsonify(users_ref if users_ref else {})

@app.route("/admin/api/update_points", methods=["POST"])
@admin_required
def admin_update_points():
    data = request.get_json()
    user_id = data.get("user_id")
    points = data.get("points")
    if not user_id or points is None:
        return jsonify({"error": "Missing user_id or points"}), 400
    get_user_ref(user_id).child("points").set(int(points))
    return jsonify({"success": True})

@app.route("/admin/api/broadcast", methods=["POST"])
@admin_required
def admin_broadcast():
    data = request.get_json()
    message = data.get("message")
    if not message:
        return jsonify({"error": "Message required"}), 400
    users = db.reference("users").get()
    if not users:
        return jsonify({"error": "No users found"}), 404
    # Send to all users (careful with serverless timeout)
    for uid in users:
        try:
            bot.send_message(uid, message)
        except Exception as e:
            print(f"Failed to send to {uid}: {e}")
    return jsonify({"success": True})

@app.route("/admin/api/set_webhook", methods=["POST"])
@admin_required
def admin_set_webhook():
    base = request.url_root.rstrip("/")
    webhook_url = f"{base}/webhook"
    try:
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        return jsonify({"success": True, "webhook_url": webhook_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin"))

# ------------------------------
# Telegram bot handlers
# ------------------------------
@bot.message_handler(commands=["start"])
def send_welcome(message):
    user = message.from_user
    user_id = user.id
    username = user.username or user.first_name
    register_user(user_id, username)

    text = (
        f"✨ <b>Welcome, {username}!</b> ✨\n\n"
        f"🚀 <b>Earn Bot</b> – Complete simple tasks and earn points!\n"
        f"<b>Your current points:</b> {get_user_ref(user_id).get().get('points', 0)}\n\n"
        f"👇 Use the buttons below to start earning or visit your dashboard."
    )
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("📋 Tasks", callback_data="tasks"),
        types.InlineKeyboardButton("📊 Dashboard", url=f"{request.url_root}dashboard")
    )
    bot.send_message(user_id, text, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(commands=["tasks"])
def show_tasks(message):
    user_id = message.from_user.id
    user_ref = get_user_ref(user_id)
    if not user_ref.get():
        register_user(user_id, message.from_user.username or message.from_user.first_name)
    text = "📋 <b>Available Tasks</b>\n\n"
    markup = types.InlineKeyboardMarkup()
    for task in TASKS:
        text += f"• {task['name']} – <b>+{task['points']} points</b>\n"
        markup.add(types.InlineKeyboardButton(
            task['button_text'], callback_data=f"claim_{task['id']}"
        ))
    text += "\nTap a button to complete the task (you must have done the action)."
    bot.send_message(user_id, text, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("claim_"))
def handle_task_claim(call):
    user_id = call.from_user.id
    task_id = call.data.split("_", 1)[1]
    user_ref = get_user_ref(user_id)
    if not user_ref.get():
        register_user(user_id, call.from_user.username or call.from_user.first_name)

    if complete_task(user_id, task_id):
        points = user_ref.child("points").get()
        bot.answer_callback_query(call.id, "✅ Task completed! Points added.")
        bot.edit_message_text(
            f"✅ Task completed!\nYour total points: {points}",
            call.message.chat.id, call.message.message_id
        )
    else:
        bot.answer_callback_query(call.id, "You have already completed this task.", show_alert=True)

@bot.message_handler(commands=["points"])
def show_points(message):
    user_id = message.from_user.id
    user_data = get_user_ref(user_id).get()
    if not user_data:
        register_user(user_id, message.from_user.username or message.from_user.first_name)
        points = 0
    else:
        points = user_data.get("points", 0)
    bot.send_message(user_id, f"💰 Your points: <b>{points}</b>", parse_mode="HTML")

# Set webhook on first request if not already configured (optional).
# The admin panel has a dedicated button for it.

# ------------------------------
# Vercel requires the 'app' object
# ------------------------------
if __name__ == "__main__":
    app.run(debug=True)
