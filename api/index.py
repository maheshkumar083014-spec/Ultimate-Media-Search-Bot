import os, time, firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template_string
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

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
        dashboard_url = f"https://{request.host}/dashboard?id={chat_id}"

        if update.message.text and update.message.text.startswith("/start"):
            if not data:
                # Referral Logic
                ref_by = update.message.text.split()[1] if " " in update.message.text else None
                if ref_by and ref_by != chat_id:
                    r_ref = db.reference(f'users/{ref_by}')
                    r_data = r_ref.get()
                    if r_data: r_ref.update({"pts": r_data.get('pts', 0) + 15, "refs": r_data.get('refs', 0) + 1})
                user_ref.set({"pts": 10, "refs": 0, "last_ad": 0, "name": update.message.from_user.first_name})

            # Blue Menu Button (Niche wala Dashboard)
            menu_kb = ReplyKeyboardMarkup([[KeyboardButton("📊 Dashboard", web_app=WebAppInfo(url=dashboard_url))]], resize_keyboard=True)
            
            # Inline Buttons for Tasks
            inline_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📺 Watch Video Ad", url=AD_LINK)],
                [InlineKeyboardButton("✅ Confirm Ad Points", callback_data="conf_ad")],
                [InlineKeyboardButton("🔴 YouTube", url=YT)],
                [InlineKeyboardButton("🔵 Facebook", url=FB), InlineKeyboardButton("🟣 Instagram", url=INSTA)],
                [InlineKeyboardButton("💰 Claim Social (15 pts)", callback_data="claim_soc")],
                [InlineKeyboardButton("👫 Invite Link", callback_data="invite")]
            ])

            bot.send_photo(chat_id, WELCOME_IMG, caption=f"💎 *EARNPRO PREMIUM* 💎\n\nNiche diye gaye tasks poore karein aur blue 'Dashboard' button se apni income check karein." + MOTIVATION, reply_markup=inline_kb, parse_mode="Markdown")
            bot.send_message(chat_id, "Tap below to open your Wallet:", reply_markup=menu_kb)

    elif update.callback_query:
        query = update.callback_query
        chat_id = str(query.message.chat_id)
        user_ref = db.reference(f'users/{chat_id}')
        data = user_ref.get()

        if query.data == "conf_ad":
            now = time.time()
            if now - data.get('last_ad', 0) > 35:
                user_ref.update({"pts": data['pts'] + 5, "last_ad": now})
                query.answer("✅ +5 Points Added!", show_alert=True)
            else:
                query.answer("⏳ Ad 30s tak watch karein!", show_alert=True)
        
        elif query.data == "claim_soc":
            if not data.get('soc_done'):
                user_ref.update({"pts": data['pts'] + 15, "soc_done": True})
                query.answer("🎉 15 Social Points Added!", show_alert=True)
            else:
                query.answer("❌ Already claimed!", show_alert=True)

        elif query.data == "invite":
            link = f"https://t.me/{bot.get_me().username}?start={chat_id}"
            bot.send_message(chat_id, f"🤝 *REFER & EARN*\n\nShare this link. Per refer: 15 points!\n`{link}`", parse_mode="Markdown")

    return "ok", 200

# --- PROFESSIONAL WEB DASHBOARD ---
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
            body { background: #0b0e14; color: white; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; text-align: center; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; }
            .logo { background: linear-gradient(45deg, #2563eb, #7c3aed); padding: 8px 15px; border-radius: 10px; font-weight: bold; font-size: 14px; }
            .balance-card { background: #161b22; border: 1px solid #30363d; border-radius: 24px; padding: 35px 20px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
            .balance-card h2 { font-size: 55px; margin: 10px 0; color: #fbbf24; text-shadow: 0 0 15px rgba(251,191,36,0.3); }
            .stats-row { display: flex; gap: 10px; margin-bottom: 20px; }
            .stat-box { background: #161b22; flex: 1; padding: 15px; border-radius: 15px; border: 1px solid #30363d; }
            .promo-box { background: rgba(37,99,235,0.05); border: 1px dashed #2563eb; padding: 20px; border-radius: 20px; margin-top: 20px; }
            .btn-share { background: #2563eb; color: white; border: none; padding: 12px; width: 100%; border-radius: 12px; font-weight: bold; margin-top: 10px; }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo">EARNPRO</div>
            <div style="font-size: 12px; color: #8b949e;">ID: EP-{{user_id[:6]}}</div>
        </div>
        <div class="balance-card">
            <div style="color: #8b949e; font-size: 14px; letter-spacing: 1px;">AVAILABLE COINS</div>
            <h2>{{user_data.pts}}.00</h2>
            <div style="background: rgba(255,255,255,0.05); display: inline-block; padding: 6px 16px; border-radius: 20px; font-size: 12px; color: #fbbf24;">MIN. PAYOUT: 100</div>
        </div>
        <div class="stats-row">
            <div class="stat-box">
                <div style="font-size: 12px; color: #8b949e;">REFERRALS</div>
                <div style="font-size: 18px; font-weight: bold;">{{user_data.refs}}</div>
            </div>
            <div class="stat-box">
                <div style="font-size: 12px; color: #8b949e;">EARNING</div>
                <div style="font-size: 18px; font-weight: bold; color: #10b981;">₹{{user_data.pts/10}}</div>
            </div>
        </div>
        <div class="promo-box">
            <div style="color: #8b949e; font-size: 12px;">YOUR INVITATION CODE</div>
            <h3 style="color: #2563eb; letter-spacing: 3px; font-size: 22px; margin: 10px 0;">EP-{{user_id[:6]}}</h3>
            <button class="btn-share">SHARE ON WHATSAPP (+15)</button>
        </div>
        <p style="font-size: 11px; color: #484f58; margin-top: 30px;">🚀 Keep earning, Rockstar!</p>
    </body>
    </html>
    """, user_id=user_id, user_data=user_data)

@app.route('/')
def home():
    return "Bot is Running Perfectly!"
