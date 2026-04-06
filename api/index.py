import os, time, firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template_string
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup

app = Flask(__name__)

# --- CONFIG ---
ADMIN_ID = "8701635891"
WELCOME_IMG = "https://i.ibb.co/zWJHms9p/image.jpg"
YT = "https://www.youtube.com/@USSoccerPulse"
FB = "fb://facewebmodal/f?href=https://www.facebook.com/61574378159053"
INSTA = "instagram://user?username=digital_rockstar_m"
AD_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"
MOTIVATION = "\n\n🚀 *Mehnat rang layegi! Roz earning karo aur doston ko bulao!*"

# --- FIREBASE ---
if not firebase_admin._apps:
    raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n').strip().strip('"').strip("'")
    cred = credentials.Certificate({"type": "service_account", "project_id": "ultimatemediasearch", "private_key": raw_key, "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"), "token_uri": "https://oauth2.googleapis.com/token"})
    firebase_admin.initialize_app(cred, {'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'})

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

# --- BOT LOGIC ---
@app.route('/api/index', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    if not update: return "ok", 200

    if update.message:
        chat_id = str(update.message.chat_id)
        user_ref = db.reference(f'users/{chat_id}')
        data = user_ref.get()

        if update.message.text.startswith("/start"):
            if not data:
                # Referral Logic
                ref_by = update.message.text.split()[1] if " " in update.message.text else None
                if ref_by and ref_by != chat_id:
                    r_ref = db.reference(f'users/{ref_by}')
                    r_data = r_ref.get()
                    if r_data: r_ref.update({"pts": r_data.get('pts', 0) + 15, "refs": r_data.get('refs', 0) + 1})
                
                user_ref.set({"pts": 10, "refs": 0, "last_ad": 0, "name": update.message.from_user.first_name})
            
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📱 Open Dashboard", url=f"https://{request.host}/dashboard?id={chat_id}")],
                [InlineKeyboardButton("📺 Watch Ad", url=AD_LINK)],
                [InlineKeyboardButton("✅ Confirm View", callback_data="conf_ad")]
            ])
            bot.send_photo(chat_id, WELCOME_IMG, caption=f"💎 *EARNPRO DASHBOARD* 💎\n\nWelcome back! Click below to manage your earnings." + MOTIVATION, reply_markup=kb, parse_mode="Markdown")

    elif update.callback_query:
        query = update.callback_query
        chat_id = str(query.message.chat_id)
        user_ref = db.reference(f'users/{chat_id}')
        data = user_ref.get()

        if query.data == "conf_ad":
            now = time.time()
            if now - data.get('last_ad', 0) > 35: # Security Timer
                user_ref.update({"pts": data['pts'] + 5, "last_ad": now})
                query.answer("✅ +5 Points Added!", show_alert=True)
            else:
                query.answer("⏳ Ad 30 seconds tak watch karein!", show_alert=True)

    return "ok", 200

# --- PROFESSIONAL WEB DASHBOARD (HTML/CSS) ---
@app.route('/dashboard')
def dashboard():
    user_id = request.args.get('id')
    user_data = db.reference(f'users/{user_id}').get() or {"pts": 0, "refs": 0, "name": "User"}
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { background: #0b0e14; color: white; font-family: sans-serif; margin: 0; padding: 20px; text-align: center; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
            .logo { background: #2563eb; padding: 10px; border-radius: 8px; font-weight: bold; }
            .balance-card { background: #161b22; border: 1px solid #30363d; border-radius: 20px; padding: 40px 20px; margin-bottom: 20px; }
            .balance-card h2 { font-size: 50px; margin: 10px 0; color: #fbbf24; }
            .task-card { background: #161b22; border-radius: 15px; padding: 15px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 15px; border-left: 4px solid #2563eb; }
            .btn-watch { background: #fbbf24; color: black; border: none; padding: 10px 20px; border-radius: 20px; font-weight: bold; cursor: pointer; }
            .promo-box { margin-top: 30px; background: rgba(37,99,235,0.1); border: 1px dashed #2563eb; padding: 20px; border-radius: 15px; }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo">E EARNPRO</div>
            <div style="font-size: 12px; color: #8b949e;">ID: EP-{{user_id[:4]}}</div>
        </div>
        
        <div class="balance-card">
            <div style="color: #8b949e; text-size: 14px;">AVAILABLE COINS</div>
            <h2>{{user_data.pts}}.00</h2>
            <div style="background: rgba(255,255,255,0.1); display: inline-block; padding: 5px 15px; border-radius: 15px; font-size: 12px;">MIN. PAYOUT: 100</div>
        </div>

        <div class="task-card">
            <div style="text-align: left;">
                <div style="font-weight: bold;">Daily Reward</div>
                <div style="font-size: 12px; color: #8b949e;">+5.00 Coins</div>
            </div>
            <div style="color: #8b949e;">Claimed</div>
        </div>

        <div class="task-card" style="border-left-color: #fbbf24;">
            <div style="text-align: left;">
                <div style="font-weight: bold;">Video Ad Task</div>
                <div style="font-size: 12px; color: #8b949e;">+10.00 Coins</div>
            </div>
            <button class="btn-watch" onclick="window.location.href='{{ad_link}}'">Watch</button>
        </div>

        <div class="promo-box">
            <div style="color: #8b949e; font-size: 12px;">YOUR INVITATION CODE</div>
            <h3 style="color: #2563eb; letter-spacing: 2px;">EP - {{user_id[:6]}}</h3>
            <button style="background: transparent; border: 1px solid #30363d; color: white; padding: 10px; width: 100%; border-radius: 10px;">SHARE ON WHATSAPP (+15)</button>
        </div>
    </body>
    </html>
    """, user_id=user_id, user_data=user_data, ad_link=AD_LINK)

@app.route('/')
def home():
    return "<h1>EarnPro Server Active</h1>"
