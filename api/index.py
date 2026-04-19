import os
import telebot
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template

# Flask Setup
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(__file__), '../templates'))

# Bot Token & Config
TOKEN = "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
bot = telebot.TeleBot(TOKEN, threaded=False)

# Firebase Initialization
def init_firebase():
    if not firebase_admin._apps:
        try:
            raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "")
            p_key = raw_key.replace('\\n', '\n').strip('"').strip("'")
            c_email = os.getenv("FIREBASE_CLIENT_EMAIL")
            
            if p_key and c_email:
                cred = credentials.Certificate({
                    "type": "service_account",
                    "project_id": "ultimatemediasearch",
                    "private_key": p_key,
                    "client_email": c_email,
                    "token_uri": "https://oauth2.googleapis.com/token",
                })
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
                })
        except Exception as e:
            print(f"Firebase Init Error: {e}")

# --- WEBHOOK ENDPOINT (For Telegram) ---
@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == 'POST':
        update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
        bot.process_new_updates([update])
        return "OK", 200
    return "<h1>Bot is Online! 🚀</h1>", 200

# --- BOT LOGIC: WELCOME MESSAGE ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    uid = message.chat.id
    name = message.from_user.first_name
    
    # Dashboard URL with User Info
    dash_url = f"https://ultimate-media-search-bot-t7kj.vercel.app/dashboard?id={uid}&name={name}"
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", url=dash_url))
    
    welcome_text = (
        f"<b>Namaste {name}! 👋</b>\n\n"
        "Welcome to <b>Ultimate Media Search Bot</b>.\n"
        "Yahan aap social tasks poora karke aur ads\n"
        "dekh kar daily points earn kar sakte hain.\n\n"
        "💰 100 Points = $1.00\n"
        "🏦 Minimum Withdraw: $10.00\n\n"
        "Niche diye gaye button par click karke shuru karein!"
    )
    
    bot.send_message(uid, welcome_text, parse_mode="HTML", reply_markup=markup)

# --- DASHBOARD ROUTE ---
@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', 'Guest')
    user_name = request.args.get('name', 'Explorer')
    pts = 0
    ad_link = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"
    
    try:
        init_firebase()
        if firebase_admin._apps:
            u_data = db.reference(f'users/{uid}').get()
            if u_data:
                pts = u_data.get('pts', 0)
    except:
        pts = 0

    return render_template('dashboard.html', pts=pts, uid=uid, ad_link=ad_link, user_name=user_name)
