import os
from flask import Flask, request, render_template_string
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

app = Flask(__name__)

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
WELCOME_IMG = "https://i.ibb.co/zWJHms9p/image.jpg"

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == "POST":
        try:
            update = Update.de_json(request.get_json(force=True), bot)
            if update.message and update.message.text:
                chat_id = str(update.message.chat_id)
                user_name = update.effective_user.first_name
                
                # Dynamic Dashboard URL
                dash_url = f"https://{request.host}/dashboard?id={chat_id}&name={user_name}"
                
                # Buttons
                markup = ReplyKeyboardMarkup([[KeyboardButton("📊 My Dashboard", web_app=WebAppInfo(url=dash_url))]], resize_keyboard=True)
                
                bot.send_photo(
                    chat_id, 
                    WELCOME_IMG, 
                    caption=f"🔥 *Assalam-o-Alaikum {user_name}!*\n\nAapka bot ab active hai. Dashboard check karein!",
                    parse_mode="Markdown",
                    reply_markup=markup
                )
            return "ok", 200
        except Exception as e:
            print(f"Error: {e}")
            return "ok", 200
    return "<h1>Bot is Active!</h1>"

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', 'User')
    name = request.args.get('name', 'User')
    
    # Isme maine background ko dark aur saare links ko ek dum clean rakha hai
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { background: #0b0e14; color: white; font-family: sans-serif; text-align: center; padding: 20px; margin: 0; }
            .card { background: #161b22; border-radius: 20px; padding: 25px; border: 1px solid #30363d; margin-bottom: 20px; }
            .btn { display: block; background: #238636; color: white; padding: 15px; margin: 10px 0; border-radius: 10px; text-decoration: none; font-weight: bold; }
            .social-btn { background: #21262d; border: 1px solid #30363d; color: #58a6ff; }
            .tip { background: #121d2f; padding: 15px; border-radius: 10px; font-size: 14px; color: #8b949e; text-align: left; border-left: 4px solid #58a6ff; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2 style="margin:0;">Welcome, {{name}}!</h2>
            <p style="color:#8b949e;">Your Earning Points</p>
            <h1 style="color:#f0883e; font-size: 50px; margin: 10px 0;">50.00</h1>
            <p>ID: {{uid}}</p>
        </div>

        <div class="tip">
            💡 <b>Earn Money:</b> Hamare niche diye gaye links ko share karein. Profile aur videos share karne par aapko points milenge jo cash mein badle ja sakte hain!
        </div>

        <h3 style="text-align:left; margin-top:25px;">🔗 Official Links</h3>
        <a href="https://www.youtube.com/@USSoccerPulse" class="btn social-btn">🔴 YouTube Channel</a>
        <a href="https://www.facebook.com/61574378159053" class="btn social-btn">🔵 Facebook Page</a>
        <a href="https://www.instagram.com/digital_rockstar_m" class="btn social-btn">🟣 Instagram Profile</a>
        
        <p style="margin-top:40px; font-size:12px; color:#484f58;">EarnPro v2.5 • Powered by Vercel</p>
    </body>
    </html>
    """, uid=uid, name=name)
