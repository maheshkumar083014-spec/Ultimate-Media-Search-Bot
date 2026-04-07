import os
import time
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template_string
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

app = Flask(__name__)

# --- CONFIGURATION ---
ADMIN_ID = "8701635891"
WELCOME_IMG = "https://i.ibb.co/zWJHms9p/image.jpg"
YT_LINK = "https://www.youtube.com/@USSoccerPulse"
FB_LINK = "https://www.facebook.com/61574378159053"
INSTA_LINK = "https://www.instagram.com/digital_rockstar_m"
AD_LINK = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"

# --- FIREBASE INIT ---
def init_firebase():
    if not firebase_admin._apps:
        try:
            raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "")
            # Key cleaning for Vercel
            if raw_key:
                raw_key = raw_key.replace('\\n', '\n').strip().strip('"').strip("'")
            
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": os.getenv("FIREBASE_PROJECT_ID", "ultimatemediasearch"),
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
            print(f"Firebase Error: {e}")
            return False
    return True

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == "POST":
        try:
            init_firebase()
            update = Update.de_json(request.get_json(force=True), bot)
            if not update or not update.effective_user: return "ok", 200
            
            chat_id = str(update.effective_user.id)
            user_ref = db.reference(f'users/{chat_id}')
            user_data = user_ref.get()

            # --- START COMMAND ---
            if update.message and update.message.text and update.message.text.startswith("/start"):
                if not user_data:
                    # Referral Check
                    args = update.message.text.split()
                    ref_id = args[1] if len(args) > 1 else None
                    if ref_id and ref_id != chat_id:
                        r_ref = db.reference(f'users/{ref_id}')
                        r_data = r_ref.get()
                        if r_data:
                            r_ref.update({"pts": r_data.get('pts', 0) + 15, "refs": r_data.get('refs', 0) + 1})
                    
                    user_ref.set({"pts": 10, "refs": 0, "name": update.effective_user.first_name})

                dash_url = f"https://{request.host}/dashboard?id={chat_id}"
                reply_markup = ReplyKeyboardMarkup([[KeyboardButton("📊 Open Dashboard", web_app=WebAppInfo(url=dash_url))]], resize_keyboard=True)
                
                inline_kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📺 Watch Ad (5 pts)", url=AD_LINK)],
                    [InlineKeyboardButton("👫 Invite & Earn (15 pts)", callback_data="invite")]
                ])

                bot.send_photo(
                    chat_id, 
                    WELCOME_IMG, 
                    caption=f"👋 *Assalam-o-Alaikum {update.effective_user.first_name}!*\n\nWelcome to EarnPro Bot. Yahan aap ads dekh kar aur doston ko invite karke paise kama sakte hain.\n\n👇 *Niche button se dashboard kholein:*",
                    reply_markup=inline_kb,
                    parse_mode="Markdown"
                )
                bot.send_message(chat_id, "Apna balance check karne ke liye Dashboard button dabayein.", reply_markup=reply_markup)

            # --- CALLBACKS ---
            elif update.callback_query:
                if update.callback_query.data == "invite":
                    bot_info = bot.get_me()
                    link = f"https://t.me/{bot_info.username}?start={chat_id}"
                    bot.send_message(chat_id, f"🚀 *Aapka Invite Link:*\n`{link}`\n\nEk dost ko bulane par 15 points milenge!", parse_mode="Markdown")

            return "ok", 200
        except Exception as e:
            return "ok", 200
    return "Bot is Running"

# --- DASHBOARD PAGE ---
@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id')
    init_firebase()
    u = db.reference(f'users/{uid}').get() or {"pts": 0, "refs": 0, "name": "User"}
    
    return render_template_string("""
    <!DOCTYPE html>
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background: #0f172a; color: white; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; margin: 0; padding: 20px; }
        .card { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-radius: 20px; padding: 25px; border: 1px solid #334155; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
        .points { font-size: 48px; font-weight: bold; color: #fbbf24; margin: 10px 0; }
        .social-box { margin-top: 25px; text-align: left; background: #1e293b; padding: 15px; border-radius: 15px; }
        .social-link { display: block; background: #334155; color: #f8fafc; padding: 12px; margin: 8px 0; border-radius: 10px; text-decoration: none; font-weight: bold; font-size: 14px; }
        .social-link:hover { background: #475569; }
        .tip { background: #065f46; padding: 15px; border-radius: 12px; margin-top: 20px; font-size: 13px; line-height: 1.5; border-left: 5px solid #10b981; text-align: left; }
        .footer-text { color: #94a3b8; font-size: 12px; margin-top: 30px; }
    </style></head>
    <body>
        <div class="card">
            <p style="color: #94a3b8; margin: 0;">Welcome, {{name}}</p>
            <div class="points">{{pts}}</div>
            <p style="margin: 0; font-weight: bold;">TOTAL EARNING POINTS</p>
            <hr style="border: 0; border-top: 1px solid #334155; margin: 20px 0;">
            <p>Total Referrals: <span style="color:#fbbf24;">{{refs}}</span></p>
        </div>

        <div class="tip">
            💡 <b>Paisa Kamane ka Tarika:</b><br>
            Aap hamare social media links ke videos aur profile ko apne doston ke sath share karke extra points kama sakte hain. Har valid share par points milenge!
        </div>

        <div class="social-box">
            <p style="margin-top: 0; font-weight: bold; color: #fbbf24;">🔗 IMPORTANT LINKS</p>
            <a href="{{yt}}" class="social-link">📺 YouTube Channel</a>
            <a href="{{fb}}" class="social-link">🔵 Facebook Page</a>
            <a href="{{insta}}" class="social-link">🟣 Instagram Profile</a>
        </div>

        <p class="footer-text">EarnPro Official v2.1 • Fast Withdrawals</p>
    </body></html>
    """, pts=u['pts'], refs=u['refs'], name=u.get('name', 'User'), yt=YT_LINK, fb=FB_LINK, insta=INSTA_LINK)

if __name__ == "__main__":
    app.run(debug=True)
