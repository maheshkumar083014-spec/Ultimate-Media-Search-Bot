from flask import Flask, request, jsonify
import requests
import firebase_admin
from firebase_admin import credentials, db
import time

app = Flask(__name__)

# ================= CONFIG =================
BOT_TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
FIREBASE_DB = "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"

# ⚠️ IMPORTANT: Use your real service account JSON here
cred = credentials.Certificate("serviceAccountKey.json")

firebase_admin.initialize_app(cred, {
    'databaseURL': FIREBASE_DB
})

# ================= TELEGRAM SEND =================

def send_photo(chat_id, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    requests.post(url, json={
        "chat_id": chat_id,
        "photo": "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg",
        "caption": caption,
        "parse_mode": "HTML"
    })

# ================= WEBHOOK =================

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if "message" not in data:
        return "ok"

    msg = data["message"]
    chat_id = str(msg["chat"]["id"])
    user_name = msg["from"].get("first_name", "User")

    text = msg.get("text", "")

    user_ref = db.reference(f"users/{chat_id}")
    user = user_ref.get()

    # ================= CREATE USER =================
    if not user:
        user = {
            "name": user_name,
            "points": 0,
            "plan": "Free",
            "joined": int(time.time() * 1000)
        }
        user_ref.set(user)

    # ================= /START =================
    if text == "/start":

        dashboard_link = f"https://your-domain.vercel.app/dashboard?uid={chat_id}"

        caption = f"""
<b>🚀 Welcome {user_name}!</b>

💰 <b>Points:</b> {user['points']}
💎 <b>Plan:</b> {user['plan']}

🎯 Complete tasks & earn rewards
🤖 Use AI assistant
📈 Upgrade for premium benefits

👇 <b>Open Dashboard:</b>
{dashboard_link}
"""

        send_photo(chat_id, caption)

    return "ok"

# ================= AI CHAT API =================

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message")

    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": "Bearer sk-783d645ce9e84eb8b954786a016561ea"
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": message}]
            }
        )

        reply = response.json()["choices"][0]["message"]["content"]

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)})

# ================= ROOT =================

@app.route("/", methods=["GET"])
def home():
    return "Bot Running 🚀"

# ================= RUN =================

if __name__ == "__main__":
    app.run()
