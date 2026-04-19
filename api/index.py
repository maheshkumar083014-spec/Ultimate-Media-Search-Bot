import os
import time
import telebot
from flask import Flask, request, render_template, jsonify
import firebase_admin
from firebase_admin import credentials, db

# ---------------- ENV ----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DB_URL = os.environ.get("FIREBASE_DB_URL")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__, template_folder="../templates")

# ---------------- FIREBASE INIT ----------------
if not firebase_admin._apps:
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": os.environ.get("PROJECT_ID"),
        "private_key": os.environ.get("PRIVATE_KEY").replace('\\n', '\n'),
        "client_email": os.environ.get("CLIENT_EMAIL"),
    })
    firebase_admin.initialize_app(cred, {
        "databaseURL": DB_URL
    })

# ---------------- UTIL ----------------
def user_ref(uid):
    return db.reference(f"users/{uid}")

def log_error(e):
    print("ERROR:", e)

# ---------------- START ----------------
@bot.message_handler(commands=['start'])
def start(message):
    try:
        uid = str(message.from_user.id)
        name = message.from_user.first_name

        ref = user_ref(uid)
        if not ref.get():
            ref.set({
                "name": name,
                "points": 0,
                "referrals": 0,
                "created": int(time.time())
            })

        dashboard = f"https://ultimate-media-search-bot-t7kj.vercel.app/dashboard?id={uid}&name={name}"

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(
            telebot.types.InlineKeyboardButton("💎 Start Earning", url=dashboard)
        )

        bot.send_message(message.chat.id,
f"""🔥 Welcome {name}

💰 Earn Daily Without Investment

✔ Watch Ads
✔ Complete Tasks
✔ Invite Friends

💵 100 Points = $1

⚡ जितना ज्यादा use उतनी ज्यादा earning

👇 Click below to start
""", reply_markup=markup)

    except Exception as e:
        log_error(e)

# ---------------- WEBHOOK ----------------
@app.route("/", methods=["POST"])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
        bot.process_new_updates([update])
    except Exception as e:
        log_error(e)
    return "OK"

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

# ---------------- GET USER ----------------
@app.route("/get_user/<uid>")
def get_user(uid):
    try:
        data = user_ref(uid).get() or {}
        return jsonify(data)
    except Exception as e:
        log_error(e)
        return jsonify({"error": str(e)})

# ---------------- ADD POINTS ----------------
@app.route("/add_points", methods=["POST"])
def add_points():
    try:
        data = request.json
        uid = data["uid"]
        points = data["points"]

        ref = user_ref(uid).child("points")

        def transaction(current):
            return (current or 0) + points

        ref.transaction(transaction)

        return {"status": "ok"}
    except Exception as e:
        log_error(e)
        return {"error": str(e)}

# ---------------- REFERRAL ----------------
@app.route("/referral", methods=["POST"])
def referral():
    try:
        uid = request.json["uid"]
        ref_uid = request.json["ref"]

        if uid == ref_uid:
            return {"status": "invalid"}

        user_ref(uid).update({"referred_by": ref_uid})

        # reward referrer
        ref = user_ref(ref_uid).child("points")
        ref.transaction(lambda x: (x or 0) + 50)

        return {"status": "ok"}
    except Exception as e:
        log_error(e)
        return {"error": str(e)}

# ---------------- WITHDRAW ----------------
@app.route("/withdraw", methods=["POST"])
def withdraw():
    try:
        uid = request.json["uid"]
        upi = request.json["upi"]

        data = user_ref(uid).get()
        points = data.get("points", 0)

        if points < 1000:
            return {"status": "low_balance"}

        user_ref(uid).update({"points": 0})

        db.reference("withdraw_requests").push({
            "uid": uid,
            "upi": upi,
            "points": points,
            "time": int(time.time())
        })

        return {"status": "success"}
    except Exception as e:
        log_error(e)
        return {"error": str(e)}

# ---------------- EXPORT ----------------
app = app
