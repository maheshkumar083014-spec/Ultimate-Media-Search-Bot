import os
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template_string
from telegram import Update, Bot, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

app = Flask(__name__)

# --- CONFIGURATION ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = "8678211883"  # Aapki Telegram ID jahan notification aayega
bot = Bot(token=TOKEN)

WELCOME_IMG = "https://i.ibb.co/zWJHms9p/image.jpg"
YT = "https://www.youtube.com/@USSoccerPulse"
FB = "https://www.facebook.com/61574378159053"
INSTA = "https://www.instagram.com/digital_rockstar_m"

# --- FIREBASE SETUP ---
def init_fb():
    if not firebase_admin._apps:
        try:
            # Cleaning the private key for Vercel environment
            raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n').strip().strip('"').strip("'")
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": raw_key,
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
            })
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
            })
            return True
        except Exception as e:
            print(f"Firebase Init Error: {e}")
            return False
    return True

# --- MAIN BOT WEBHOOK ---
@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == "POST":
        try:
            data = request.get_json(force=True)
            update = Update.de_json(data, bot)
            
            if update.message and update.message.text:
                chat_id = str(update.message.chat_id)
                user_name = update.effective_user.first_name
                
                init_fb()
                # User entry in Firebase if new
                try:
                    ref = db.reference(f'users/{chat_id}')
                    if not ref.get():
                        ref.set({"name": user_name, "pts": 10, "refs": 0})
                except: pass

                # Link for the Dashboard Button
                dash_url = f"https://{request.host}/dashboard?id={chat_id}&name={user_name}"
                kb = ReplyKeyboardMarkup([[KeyboardButton("📊 Open Dashboard", web_app=WebAppInfo(url=dash_url))]], resize_keyboard=True)
                
                bot.send_photo(
                    chat_id, WELCOME_IMG, 
                    caption=f"🔥 *Welcome {user_name}!*\n\nTasks complete karein aur points earn karein. Withdraw ke liye niche Dashboard button dabayein.",
                    parse_mode="Markdown", reply_markup=kb
                )
            return "ok", 200
        except Exception as e:
            return str(e), 200
    return "Bot Engine is Active!"

# --- DASHBOARD PAGE ---
@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    init_fb()

    # If user submits the withdraw form
    success_msg = ""
    if request.args.get('submit') == '1':
        phone = request.args.get('phone')
        upi = request.args.get('upi')
        try:
            # Save request to Firebase
            db.reference(f'withdrawals/{uid}').set({
                "name": name, "phone": phone, "upi": upi, "status": "Pending"
            })
            # Notify Admin on Telegram
            bot.send_message(ADMIN_ID, f"💰 *NEW WITHDRAWAL REQUEST*\n\n👤 Name: {name}\n📱 Phone: {phone}\n💳 UPI: {upi}\n🆔 ID: {uid}", parse_mode="Markdown")
            success_msg = "✅ Details sent to Admin! Wait for payment."
        except:
            success_msg = "❌ Error. Try again."

    # Fetch User Points
    try:
        user_data = db.reference(f'users/{uid}').get() or {"pts": 10}
        pts = user_data.get('pts', 10)
    except: pts = 0

    return render_template_string("""
    <!DOCTYPE html>
    <html><head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { background: #0f172a; color: white; font-family: sans-serif; text-align: center; padding: 15px; margin: 0; }
            .card { background: linear-gradient(145deg, #1e293b, #0f172a); border-radius: 20px; padding: 25px; border: 1px solid #334155; margin-bottom: 20px; }
            .pts { font-size: 45px; color: #fbbf24; font-weight: bold; margin: 10px 0; }
            .task-box { background: #161b22; border-radius: 15px; padding: 15px; text-align: left; border: 1px solid #30363d; margin-top: 15px; }
            .btn-task { display: flex; justify-content: space-between; align-items: center; background: #21262d; padding: 12px; border-radius: 10px; margin-bottom: 10px; text-decoration: none; color: white; border: 1px solid #30363d; font-size: 14px; }
            .go { background: #238636; padding: 5px 12px; border-radius: 6px; font-weight: bold; }
            .btn-main { background: #fbbf24; color: black; padding: 15px; border-radius: 12px; width: 100%; border: none; font-weight: bold; font-size: 16px; cursor: pointer; margin-top: 10px; }
            input { width: 100%; padding: 12px; margin: 8px 0; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: white; box-sizing: border-box; }
            .form-box { display: none; margin-top: 20px; padding: 15px; border: 1px solid #fbbf24; border-radius: 15px; background: #1e293b; }
        </style>
    </head>
    <body>
        <div class="card">
            <p style="margin:0; color:#94a3b8;">Total Points</p>
            <div class="pts">{{pts}} pts</div>
            <button class="btn-main" onclick="document.getElementById('wform').style.display='block'">💰 WITHDRAW NOW</button>
        </div>

        {% if msg %}<p style="color:#10b981; font-weight:bold;">{{msg}}</p>{% endif %}

        <div id="wform" class="form-box">
            <h3 style="margin-top:0;">Payment Details</h3>
            <form method="GET">
                <input type="hidden" name="id" value="{{uid}}">
                <input type="hidden" name="name" value="{{name}}">
                <input type="hidden" name="submit" value="1">
                <input type="number" name="phone" placeholder="WhatsApp Number" required>
                <input type="text" name="upi" placeholder="UPI ID (e.g. name@paytm)" required>
                <button type="submit" class="btn-main" style="background:#10b981; color:white;">Submit Claim</button>
            </form>
        </div>

        <div class="task-box">
            <span style="color:#58a6ff; font-weight:bold;">🎯 DAILY EARNING TASKS</span><br><br>
            <a href="{{yt}}" class="btn-task"><span>🔴 YouTube Sub</span> <span class="go">GO +5</span></a>
            <a href="{{insta}}" class="btn-task"><span>🟣 Instagram Follow</span> <span class="go">GO +5</span></a>
            <a href="https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b" class="btn-task"><span>📺 Watch Ad</span> <span class="go">GO +10</span></a>
        </div>
    </body></html>
    """, pts=pts, uid=uid, name=name, yt=YT, insta=INSTA, msg=success_msg)

if __name__ == "__main__":
    app.run(debug=True)
