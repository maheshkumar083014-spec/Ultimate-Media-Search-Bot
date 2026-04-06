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
MOTIVATION = "\n\n🚀 *Mehnat rang layegi! Paisa hi paisa hoga!*"

# --- FIREBASE ---
if not firebase_admin._apps:
    raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n').strip().strip('"').strip("'")
    cred = credentials.Certificate({"type": "service_account", "project_id": "ultimatemediasearch", "private_key": raw_key, "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"), "token_uri": "https://oauth2.googleapis.com/token"})
    firebase_admin.initialize_app(cred, {'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'})

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

# --- BOT MAIN LOGIC ---
@app.route('/', methods=['GET', 'POST']) # Dono GET/POST handle karega
def webhook():
    if request.method == "POST":
        try:
            update = Update.de_json(request.get_json(force=True), bot)
            if not update: return "ok", 200

            if update.message:
                chat_id = str(update.message.chat_id)
                user_ref = db.reference(f'users/{chat_id}')
                data = user_ref.get()
                dashboard_url = f"https://{request.host}/dashboard?id={chat_id}"

                if update.message.text and update.message.text.startswith("/start"):
                    if not data:
                        # Referral logic
                        ref_by = update.message.text.split()[1] if " " in update.message.text else None
                        if ref_by and ref_by != chat_id:
                            r_ref = db.reference(f'users/{ref_by}')
                            r_data = r_ref.get()
                            if r_data: r_ref.update({"pts": r_data.get('pts', 0) + 15, "refs": r_data.get('refs', 0) + 1})
                        user_ref.set({"pts": 10, "refs": 0, "last_ad": 0})

                    # Professional Menu Button
                    menu = ReplyKeyboardMarkup([[KeyboardButton("📊 Dashboard", web_app=WebAppInfo(url=dashboard_url))]], resize_keyboard=True)
                    
                    # Social Tasks Buttons
                    kb = InlineKeyboardMarkup([
                        [InlineKeyboardButton("📺 Watch Ad (5 pts)", url=AD_LINK)],
                        [InlineKeyboardButton("✅ Confirm Ad View", callback_data="conf_ad")],
                        [InlineKeyboardButton("🔴 YouTube", url=YT)],
                        [InlineKeyboardButton("🔵 FB", url=FB), InlineKeyboardButton("🟣 Insta", url=INSTA)],
                        [InlineKeyboardButton("💰 Claim Social (15 pts)", callback_data="claim_soc")],
                        [InlineKeyboardButton("👫 Invite & Earn", callback_data="invite")]
                    ])

                    bot.send_photo(chat_id, WELCOME_IMG, caption="💎 *EARNPRO OFFICIAL* 💎" + MOTIVATION, reply_markup=kb, parse_mode="Markdown")
                    bot.send_message(chat_id, "Niche 'Dashboard' button se apni earning check karein 👇", reply_markup=menu)

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
                        query.answer("⏳ Video ko 30s tak dekhein!", show_alert=True)
                
                elif query.data == "claim_soc":
                    if not data.get('soc_done'):
                        user_ref.update({"pts": data['pts'] + 15, "soc_done": True})
                        query.answer("🎉 15 Points added for Social Tasks!", show_alert=True)
                    else:
                        query.answer("❌ Already claimed!", show_alert=True)

                elif query.data == "invite":
                    link = f"https://t.me/{bot.get_me().username}?start={chat_id}"
                    bot.send_message(chat_id, f"🎁 *INVITE LINK*\nShare karo aur 15 points kamao:\n\n`{link}`", parse_mode="Markdown")

            return "ok", 200
        except Exception as e:
            return str(e), 500
    
    return "<h1>Bot is Active!</h1>" # Browser mein ye dikhega

# --- WEB DASHBOARD ---
@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id')
    u = db.reference(f'users/{uid}').get() or {"pts": 0, "refs": 0}
    return render_template_string("""
    <!DOCTYPE html>
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background: #0b0e14; color: white; font-family: sans-serif; text-align: center; padding: 20px; }
        .card { background: #161b22; border-radius: 20px; padding: 30px; border: 1px solid #30363d; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        h1 { font-size: 50px; color: #fbbf24; margin: 10px 0; }
        .btn { background: #2563eb; color: white; border: none; padding: 12px; width: 100%; border-radius: 12px; font-weight: bold; margin-top: 20px; }
        .stat { display: flex; justify-content: space-around; margin: 20px 0; }
    </style></head>
    <body>
        <div style="font-size: 14px; background: #2563eb; display: inline-block; padding: 5px 15px; border-radius: 10px; margin-bottom: 20px;">EARNPRO</div>
        <div class="card">
            <p style="color: #8b949e;">AVAILABLE BALANCE</p>
            <h1>{{u.pts}}.00</h1>
            <div class="stat">
                <div><small>REFERRALS</small><br><b>{{u.refs}}</b></div>
                <div><small>EARNING</small><br><b style="color:#10b981;">₹{{u.pts/10}}</b></div>
            </div>
        </div>
        <div style="margin-top:20px; border: 1px dashed #2563eb; padding: 15px; border-radius: 15px;">
            <small style="color: #8b949e;">INVITE CODE</small>
            <h2 style="color: #2563eb; letter-spacing: 2px;">EP-{{uid[:6]}}</h2>
            <button class="btn">SHARE ON WHATSAPP (+15)</button>
        </div>
    </body></html>
    """, u=u, uid=uid)
