import os
import json
import uuid
import asyncio
from flask import Flask, request, render_template_string
from telegram import Update, Bot, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, constants
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)

# --- SECURE CONFIGURATION (FROM ENV) ---
# Dhyan dein: Token ko code se hata diya gaya hai.
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
# Agar testing ke liye locally chala rahe hain, to TOKEN ki value yahan rakh sakte hain, 
# lekin deployment ke liye Vercel Env hi use karein.
if not TOKEN:
    print("❌ Critical Error: TELEGRAM_BOT_TOKEN environment variable missing!")
    
bot = Bot(token=TOKEN)

# Is image ko dashboard ke liye 'dynamic_photo.png' ke naam se refer karein
PROFILE_PHOTO_URL = "https://i.ibb.co/39V9V4Y3/image.jpg"
YT_LINK = "https://www.youtube.com/@USSoccerPulse"
INSTA_LINK = "https://www.instagram.com/digital_rockstar_m"
FB_LINK = "https://www.facebook.com/profile.php?id=61574378159053"
# Aapka Vercel Domain jahan par bot deployed hai
DASHBOARD_BASE_URL = "https://ultimate-media-search-bot.vercel.app"

# --- FIREBASE SECURE INIT ---
def init_fb():
    if not firebase_admin._apps:
        cred_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
        if not cred_json:
            print("❌ Critical Error: FIREBASE_SERVICE_ACCOUNT environment variable missing!")
            return False
        try:
            # JSON string ko dict mein convert (Safe)
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
            })
            return True
        except Exception as e:
            print(f"❌ Firebase Init Error: {e}")
            return False
    return True

# --- HELPER: ASYNC TELEGRAM CALLS ---
async def send_welcome_async(chat_id, u_name):
    """Asynchronously sends the welcome message with photo and WebApp button."""
    try:
        if not TOKEN:
            return
        
        # User-specific dashboard link
        dash_url = f"{DASHBOARD_BASE_URL}/dashboard?id={chat_id}&name={u_name}"
        
        # Keyboard with WebAppInfo for dynamic dashboard opening
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🚀 Open My Dashboard", web_app=WebAppInfo(url=dash_url))
        ]])
        
        # Escape user name for MarkdownV2 to prevent parsing errors
        escaped_name = u_name.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')

        await bot.send_photo(
            chat_id=chat_id,
            photo=PROFILE_PHOTO_URL,
            caption=(
                f"✨ *Welcome {escaped_name}\\!* ✨\n\n"
                f"💪 Zindagi mein koshish karne walon ki kabhi haar nahi hoti\\.\n\n"
                f"📊 Aaj se hi apni earning shuru karein\\!\n\n"
                f"Niche button par click karke dashboard kholein\\."
            ),
            parse_mode=constants.ParseMode.MARKDOWN_V2,
            reply_markup=kb
        )
        print(f"✅ Send photo to {chat_id}")
    except Exception as e:
        print(f"❌ Error sending welcome: {e}")

# --- BOT WEBHOOK LOGIC ---
@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == "POST":
        try:
            # Telegram bot update receive karna
            update = Update.de_json(request.get_json(force=True), bot)
            if not update or not update.message:
                return "OK", 200
            
            chat_id = str(update.message.chat_id)
            # Default to 'User' if first_name is missing
            u_name = update.message.from_user.first_name or "User"

            if init_fb():
                user_ref = db.reference(f'users/{chat_id}')
                u_data = user_ref.get()

                if not u_data:
                    # New user creation
                    user_ref.set({
                        "name": u_name,
                        "pts": 10,
                        "coupon": str(uuid.uuid4())[:8],
                        "last_ad": 0
                    })
                
                # Create and run the async task
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(send_welcome_async(chat_id, u_name))
                loop.close()

        except Exception as e:
            print(f"⚠️ Webhook Error: {e}")
            
    return "Bot is Active", 200

# --- DASHBOARD PAGE ---
@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', '0')
    name = request.args.get('name', 'User')
    
    if not init_fb():
        return "Database Connection Error. Check environment variables.", 500

    u_ref = db.reference(f'users/{uid}')
    u_data = u_ref.get() or {"pts": 0, "coupon": "N/A"}
    
    # Points Claiming Logic (no changes to point logic, just added success URL)
    if request.args.get('ad_claim') == '1':
        new_pts = u_data.get('pts', 0) + 10
        u_ref.update({"pts": new_pts})
        # Important: Success alert and then redirect back to avoid double claims on refresh
        success_template = (
            "<script>"
            "alert('Points Added! 🚀');"
            "window.location.href='/dashboard?id={{uid}}&name={{name}}';"
            "</script>"
        )
        return render_template_string(success_template, uid=uid, name=name)

    # Use the same image file for dashboard aesthetic, dynamically referencing it
    dynamic_photo = PROFILE_PHOTO_URL

    return render_template_string("""
    <!DOCTYPE html><html><head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background:#0f172a; color:white; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align:center; padding:15px; margin:0; }
        .dynamic-header { width:100px; height:100px; border-radius:50%; border: 3px solid #fbbf24; margin: 20px auto; background-image: url('{{dynamic_img}}'); background-size: cover; background-position: center; }
        .card { background:#1e293b; border-radius:15px; padding:20px; border:1px solid #334155; margin-bottom:15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        .pts { font-size:54px; color:#fbbf24; font-weight:bold; margin: 10px 0; }
        .btn-withdraw { background:#b45309; color:white; padding:12px; border-radius:10px; width:100%; border:none; font-weight:bold; cursor:pointer; font-size: 16px; margin-top: 10px;}
        .task { background:#1e293b; padding:15px; border-radius:12px; margin-bottom:10px; display:flex; justify-content:space-between; text-decoration:none; color:white; border:1px solid #334155; align-items:center; transition: background 0.2s;}
        .task:active { background: #334155; }
        .icon-box { width:35px; height:35px; border-radius:8px; display:flex; align-items:center; justify-content:center; margin-right:10px; }
    </style></head>
    <body>
        <div class="dynamic-header"></div>
        <div class="card">
            <p style="margin:0; color:#94a3b8;">Welcome, {{name}}</p>
            <div class="pts">{{pts}}</div>
            <button class="btn-withdraw" onclick="alert('Withdrawals open at 100 points. Keep earning!')">💳 WITHDRAW FUNDS</button>
            <p style="font-size:13px; margin-top:15px;">🎁 Promo Code: <span style="color:#fbbf24; font-weight:bold;">{{coupon}}</span></p>
        </div>
        <div style="text-align:left;">
            <p style="font-size:12px; color:#94a3b8; font-weight:bold; letter-spacing:1px; margin-bottom: 15px;">EARN POINTS</p>
            <a href="{{yt}}" target="_blank" class="task"><div style="display:flex; align-items:center;"><div class="icon-box" style="background:#ef4444;"><i class="fab fa-youtube"></i></div>YouTube Subscribe</div><b>+5</b></a>
            <a href="{{fb}}" target="_blank" class="task"><div style="display:flex; align-items:center;"><div class="icon-box" style="background:#3b82f6;"><i class="fab fa-facebook-f"></i></div>Follow Facebook</div><b>+5</b></a>
            <div class="task" style="cursor:pointer;" onclick="location.href='/dashboard?id={{uid}}&name={{name}}&ad_claim=1'"><div style="display:flex; align-items:center;"><div class="icon-box" style="background:#fbbf24; color:black;"><i class="fas fa-play"></i></div>Watch Video Ad</div><b>+10</b></div>
        </div>
    </body></html>
    """, pts=u_data.get('pts', 0), coupon=u_data.get('coupon', '...'), uid=uid, name=name, yt=YT_LINK, fb=FB_LINK, dynamic_img=dynamic_photo)

if __name__ == "__main__":
    # Local running: use 'python app.py'
    app.run(host='0.0.0.0', port=5000, debug=True)
