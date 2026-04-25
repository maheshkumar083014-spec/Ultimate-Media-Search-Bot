import os
import telebot
from flask import Flask, request, render_template, jsonify
import firebase_admin
from firebase_admin import credentials, db
import requests
import json

# ---------------------------
# ENVIRONMENT VARIABLES
# ---------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0000"))

WELCOME_PHOTO = "[i.ibb.co](https://i.ibb.co/h1m0cc1W/6a74f155-a6b7-499f-ad34-c1a3989433e0.jpg)"

# ---------------------------
# FLASK + TELEGRAM BOT
# ---------------------------
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)

cred = credentials.Certificate("firebase-service-account.json")
firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})

users_ref = db.reference("users")
plans_ref = db.reference("plans")
uploads_ref = db.reference("uploads")
verification_ref = db.reference("verification")

# ---------------------------
#   AI SUPPORT (DeepSeek)
# ---------------------------
def deepseek_chat(message):
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": message}]
    }
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    r = requests.post("[api.deepseek.com](https://api.deepseek.com/chat/completions)", headers=headers, json=payload)
    return r.json()["choices"][0]["message"]["content"]


# ---------------------------
# TELEGRAM BOT: /start
# ---------------------------
@bot.message_handler(commands=["start"])
def start(msg):
    uid = str(msg.from_user.id)
    name = msg.from_user.first_name

    # Create User in Firebase
    users_ref.child(uid).update({
        "name": name,
        "points": 0,
        "plan": "free",
        "verified": False,
        "referrals": 0
    })

    dashboard_url = f"[{os.getenv(](https://{os.getenv()'VERCEL_URL')}/dashboard?id={uid}&name={name}"

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("Open Dashboard", url=dashboard_url))

    bot.send_photo(
        msg.chat.id,
        WELCOME_PHOTO,
        caption="Welcome to Ultimate Media Search & Earn Bot!\nTap below to open your Dashboard.",
        reply_markup=markup
    )


# ---------------------------
# YT / IG / FACEBOOK VERIFICATION
# ---------------------------
@bot.message_handler(commands=["verify"])
def verify_user(msg):
    uid = str(msg.from_user.id)

    verification_ref.child(uid).set({
        "youtube": False,
        "instagram": False,
        "facebook": False
    })

    text = (
        "Complete all 3 verification steps:\n\n"
        "1️⃣ Subscribe YouTube: @USSoccerPulse\n"
        "2️⃣ Follow Instagram: @digital_rockstar_m\n"
        "3️⃣ Follow Facebook (Official)\n\n"
        "Send: done"
    )

    bot.reply_to(msg, text)


@bot.message_handler(func=lambda m: m.text.lower()=="done")
def verify_done(msg):
    uid = str(msg.from_user.id)

    verification_ref.child(uid).update({
        "youtube": True,
        "instagram": True,
        "facebook": True
    })

    users_ref.child(uid).update({"verified": True})

    bot.reply_to(msg, "🎉 Verification Complete! You can now earn points.")


# ---------------------------
# PAYMENT SCREENSHOT HANDLING
# ---------------------------
@bot.message_handler(content_types=["photo"])
def payment_upload(msg):
    uid = str(msg.from_user.id)

    if msg.caption and msg.caption.lower().startswith("plan"):
        file_id = msg.photo[-1].file_id
        plans_ref.child(uid).set({"file_id": file_id})

        bot.reply_to(msg, "Your payment screenshot was submitted. Admin will verify soon.")

        # Notify Admin
        bot.send_message(
            ADMIN_ID,
            f"New Payment Submitted by {uid}. Check /admin panel."
        )


# ---------------------------
# FLASK ROUTES (DASHBOARD + ADMIN)
# ---------------------------

@app.route("/dashboard")
def dashboard():
    uid = request.args.get("id")
    name = request.args.get("name")

    user = users_ref.child(uid).get() or {}

    return render_template("dashboard.html", uid=uid, name=name, user=user)


@app.route("/admin")
def admin():
    data = plans_ref.get() or {}
    return render_template("admin.html", data=data)


@app.route("/approve", methods=["POST"])
def approve():
    uid = request.json["uid"]
    plan = request.json["plan"]

    users_ref.child(uid).update({"plan": plan})
    return jsonify({"status": "ok"})


# ---------------------------
# TELEGRAM WEBHOOK ENDPOINT
# ---------------------------
@app.route("/", methods=["POST"])
def webhook():
    json_data = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_data)
    bot.process_new_updates([update])
    return "ok"


@app.route("/", methods=["GET"])
def home():
    return "Bot Running Successfully"


# ---------------------------
# LOCAL TESTING
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)
