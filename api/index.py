import os
import json
import logging
import time
import telebot
from telebot import types
from flask import Flask, request, jsonify, render_template_string, redirect, send_from_directory

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# 🔐 Configuration
# ─────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw')
FIREBASE_DB_URL = os.environ.get('FIREBASE_DATABASE_URL', 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/').rstrip('/')

# App Config
APP_CONFIG = {
    'POINTS_PER_DOLLAR': 100,
    'AD_POINTS': 25,
    'SOCIAL_POINTS': 100,
    'REFERRAL_BONUS': 50,
    'AD_LINK': 'https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b',
    'YOUTUBE_LINK': 'https://www.youtube.com/@USSoccerPulse',
    'INSTAGRAM_LINK': 'https://www.instagram.com/digital_rockstar_m',
    'FACEBOOK_LINK': 'https://www.facebook.com/UltimateMediaSearch',
    'BANNER_IMAGE': 'https://i.ibb.co/9kmTw4Gh/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg'
}

# Frontend Firebase Config
FRONTEND_FIREBASE = {
    'apiKey': 'AIzaSyD50eWvysruXgtgpDhhCVE2zdbSbLkFBwk',
    'authDomain': 'ultimatemediasearch.firebaseapp.com',
    'databaseURL': FIREBASE_DB_URL,
    'projectId': 'ultimatemediasearch',
    'storageBucket': 'ultimatemediasearch.firebasestorage.app',
    'messagingSenderId': '123003124713',
    'appId': '1:123003124713:web:c738c97b2772b112822978'
}

logger.info("✅ Configuration loaded")

# ─────────────────────────────────────────────────────────────────────
# ️ Firebase REST API (Lightweight - No Admin SDK)
# ─────────────────────────────────────────────────────────────────────
import requests

def fb_get(path):
    try:
        r = requests.get(f"{FIREBASE_DB_URL}/{path}.json", timeout=10)
        return r.json() if r.status_code == 200 else None
    except: return None

def fb_set(path, data):
    try:
        r = requests.put(f"{FIREBASE_DB_URL}/{path}.json", json=data, timeout=10)
        return r.status_code in [200, 201]
    except: return False

def fb_update(path, data):
    try:
        r = requests.patch(f"{FIREBASE_DB_URL}/{path}.json", json=data, timeout=10)
        return r.status_code in [200, 201]
    except: return False

def fb_push(path, data):
    try:
        r = requests.post(f"{FIREBASE_DB_URL}/{path}.json", json=data, timeout=10)
        return r.json().get('name') if r.status_code in [200, 201] else None
    except: return None

def get_user(uid):
    return fb_get(f'users/{uid}')

def create_user(uid, name, ref_code=None):
    ts = int(time.time() * 1000)
    my_ref = 'UMS' + str(uid)[::-1][:6].upper()
    user = {
        'uid': uid, 'name': name, 'referral_code': my_ref, 'referred_by': ref_code,
        'points': 0, 'total_earned': 0, 'ad_views': 0, 'tasks_completed': 0,
        'joined_at': ts, 'last_active': ts, 'last_ad_date': '', 'is_banned': False
    }
    if fb_set(f'users/{uid}', user) and ref_code:
        # Reward referrer
        all_users = fb_get('users')
        if all_users:
            for u_id, u_data in all_users.items():
                if u_data.get('referral_code') == ref_code:
                    fb_update(f'users/{u_id}', {
                        'points': (u_data.get('points',0) or 0) + APP_CONFIG['REFERRAL_BONUS'],
                        'total_earned': (u_data.get('total_earned',0) or 0) + APP_CONFIG['REFERRAL_BONUS'],
                        'referral_count': (u_data.get('referral_count',0) or 0) + 1
                    })
                    fb_set(f'referrals/{u_id}/{uid}', {'joined_at': ts, 'bonus': APP_CONFIG['REFERRAL_BONUS']})
                    break
    return user

def add_points(uid, pts, type_):
    try:
        user = get_user(uid)
        if not user: return False
        ts = int(time.time() * 1000)
        updates = {
            'points': (user.get('points',0) or 0) + pts,
            'total_earned': (user.get('total_earned',0) or 0) + pts,
            'tasks_completed': (user.get('tasks_completed',0) or 0) + 1,
            'last_active': ts,
            f'history/{ts}': {'points': pts, 'type': type_, 'timestamp': ts}
        }
        if type_ == 'ad_view':
            updates['ad_views'] = (user.get('ad_views',0) or 0) + 1
        return fb_update(f'users/{uid}', updates)
    except: return False

logger.info("✅ Database functions ready")

# ─────────────────────────────────────────────────────────────────────
#  Telegram Bot Setup (pyTelegramBotAPI)
# ─────────────────────────────────────────────────────────────────────
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML', threaded=False)

# Bot Handlers
@bot.message_handler(commands=['start'])
def handle_start(message):
    try:
        uid = message.from_user.id
        uname = message.from_user.first_name or 'User'
        
        # Parse referral code
        ref_code = None
        if message.text and len(message.text.split()) > 1:
            ref_code = message.text.split()[-1]
        
        # Create/Update user
        if not get_user(uid):
            create_user(uid, uname, ref_code)
        else:
            fb_update(f'users/{uid}', {'last_active': int(time.time() * 1000), 'name': uname})
        
        # ✅ WELCOME MESSAGE + PHOTO + MOTIVATION
        caption = f"""🌟 Welcome back, <b>{uname}</b>!

💬 <i>"Your smartphone is now your ATM. Stop scrolling for free—start earning for your time! 💰✨"</i>

📊 <b>YOUR AD-EARNING DASHBOARD</b>

🎁 <b>How to Earn:</b>
├ 📺 Ads → +{APP_CONFIG['AD_POINTS']} pts
├ 📱 Social → +{APP_CONFIG['SOCIAL_POINTS']} pts
├ 👥 Referrals → +{APP_CONFIG['REFERRAL_BONUS']} pts
└ 💰 <b>{APP_CONFIG['POINTS_PER_DOLLAR} pts = $1.00</b>

👇 Tap below to open your Dashboard!"""
        
        # Inline Keyboard
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🚀 Open Dashboard", web_app=types.WebAppInfo(url=f"/dashboard?id={uid}&name={uname}")),
            types.InlineKeyboardButton("👥 Invite Friends", callback_data=f"invite:{uid}")
        )
        
        # Send Photo + Caption
        try:
            bot.send_photo(message.chat.id, photo=APP_CONFIG['BANNER_IMAGE'], caption=caption, reply_markup=markup)
        except Exception as e:
            logger.warning(f"Photo send failed: {e}")
            # Fallback to text
            bot.send_message(message.chat.id, caption + f"\n\n🖼️ <a href='{APP_CONFIG['BANNER_IMAGE']}'>View Banner</a>", reply_markup=markup, parse_mode='HTML')
            
    except Exception as e:
        logger.error(f"Start error: {e}")
        bot.send_message(message.chat.id, "⚠️ Error. Please try /start again.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('invite:'))
def handle_invite(call):
    try:
        uid = int(call.data.split(':')[1])
        if call.from_user.id != uid:
            bot.answer_callback_query(call.id, "⚠️ Unauthorized", show_alert=True)
            return
        
        user = get_user(uid)
        ref_code = user.get('referral_code', '') if user else ''
        ref_link = f"https://t.me/UltimateMediaSearchBot?start={ref_code}"
        
        text = f"""👥 <b>Invite & Earn!</b>

🎁 +{APP_CONFIG['REFERRAL_BONUS']} Points per friend!

🔗 Your Link:
<code>{ref_link}</code>

📋 Share with friends & earn!"""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📋 Copy Link", switch_inline_query=ref_link))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"Invite error: {e}")
        bot.answer_callback_query(call.id, "Error", show_alert=True)

# ─────────────────────────────────────────────────────────────────────
# 🌐 Flask App
# ─────────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder='../static', template_folder='../templates')

# ─────────────────────────────────────────────────────────────────────
# 🎨 Dashboard HTML Template (Inline)
# ─────────────────────────────────────────────────────────────────────
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>💰 Ultimate Media Search</title>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-database-compat.js"></script>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:linear-gradient(180deg,#fef3c7,#fde68a 20%,#f59e0b 40%,#d97706 60%,#92400e 80%,#78350f);min-height:100vh;color:#292524;overflow-x:hidden}
.container{max-width:480px;margin:0 auto;padding:16px 16px 100px;position:relative;z-index:1}
.particles{position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden}
.particle{position:absolute;width:6px;height:6px;background:rgba(251,191,36,0.4);border-radius:50%;animation:floatUp linear infinite}
@keyframes floatUp{0%{transform:translateY(100vh) scale(0);opacity:0}10%{opacity:1}90%{opacity:1}100%{transform:translateY(-10vh) scale(1);opacity:0}}
.welcome-section{text-align:center;padding:20px 0 10px}
.profile-ring{width:90px;height:90px;border-radius:50%;background:linear-gradient(135deg,#fbbf24,#d97706,#92400e);padding:3px;margin:0 auto 12px;animation:pulseRing 3s ease-in-out infinite}
@keyframes pulseRing{0%,100%{box-shadow:0 0 0 0 rgba(245,158,11,0.4)}50%{box-shadow:0 0 0 12px rgba(245,158,11,0)}}
.profile-img{width:100%;height:100%;border-radius:50%;object-fit:cover;border:3px solid #fffbeb}
.welcome-text{font-size:1.4rem;font-weight:700;color:#fff;text-shadow:0 2px 10px rgba(69,26,3,0.3);margin-bottom:4px}
.welcome-name{font-size:1.6rem;font-weight:800;color:#fffbeb;text-shadow:0 2px 15px rgba(69,26,3,0.4)}
.card{background:rgba(255,248,235,0.85);backdrop-filter:blur(20px);border:1px solid rgba(217,119,6,0.3);border-radius:24px;padding:20px;margin-top:16px;box-shadow:0 8px 32px rgba(120,53,15,0.2)}
.card-title{font-size:1.1rem;font-weight:800;text-align:center;color:#78350f;text-transform:uppercase;margin-bottom:16px;padding-bottom:12px;border-bottom:2px solid rgba(217,119,6,0.15)}
.task-section{background:rgba(254,243,199,0.6);border:1px solid rgba(217,119,6,0.2);border-radius:16px;padding:14px;margin-bottom:16px}
.task-icons{display:flex;gap:8px;margin-bottom:12px}
.task-btn{width:48px;height:48px;border-radius:14px;display:flex;flex-direction:column;align-items:center;justify-content:center;border:none;cursor:pointer;transition:0.2s}
.task-btn:active{transform:scale(0.92)}
.task-btn .icon{font-size:1.2rem;margin-bottom:2px}
.task-btn .lbl{font-size:0.55rem;font-weight:600;color:#78350f}
.task-btn.ad{background:linear-gradient(135deg,#bbf7d0,#86efac)}
.task-btn.done{background:linear-gradient(135deg,#fef3c7,#fde68a)}
.task-btn.off{background:linear-gradient(135deg,#fed7aa,#fdba74)}
.task-row{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid rgba(217,119,6,0.1)}
.task-row:last-child{border:none}
.badge{padding:4px 14px;border-radius:20px;font-size:0.7rem;font-weight:700;text-transform:uppercase}
.badge.done{background:rgba(34,197,94,0.15);color:#16a34a}
.badge.pend{background:rgba(245,158,11,0.15);color:#d97706}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px}
.tracker,.withdraw{background:rgba(254,243,199,0.6);border:1px solid rgba(217,119,6,0.2);border-radius:16px;padding:14px}
.tracker-info{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.tracker-badge{background:linear-gradient(135deg,#d97706,#92400e);color:#fff;padding:2px 6px;border-radius:4px;font-size:0.6rem;font-weight:800}
.progress-big{text-align:center;margin:10px 0}
.progress-big .num{font-size:1.3rem;font-weight:800;color:#78350f}
.bar-bg{width:100%;height:8px;background:rgba(217,119,6,0.15);border-radius:10px;overflow:hidden}
.bar-fill{height:100%;border-radius:10px;background:linear-gradient(90deg,#f59e0b,#d97706,#92400e);transition:1s}
.withdraw{text-align:center}
.bal-amt{font-size:1.8rem;font-weight:900;background:linear-gradient(135deg,#92400e,#451a03);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:10px}
.btn-w{width:100%;padding:10px;border-radius:12px;border:none;background:linear-gradient(135deg,#92400e,#451a03);color:#fffbeb;font-weight:700;cursor:pointer;box-shadow:0 4px 12px rgba(69,26,3,0.3)}
.btn-w:active{transform:scale(0.96)}
.btn-w:disabled{opacity:0.5}
.social-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:12px}
.s-card{background:rgba(254,243,199,0.7);border:1px solid rgba(217,119,6,0.2);border-radius:14px;padding:12px 8px;text-align:center;text-decoration:none;display:block;cursor:pointer}
.s-card:active{transform:scale(0.95)}
.s-icon{width:40px;height:40px;border-radius:12px;display:flex;align-items:center;justify-content:center;margin:0 auto 8px;font-size:1.2rem}
.s-icon.yt{background:linear-gradient(135deg,#fee2e2,#fecaca)}
.s-icon.ig{background:linear-gradient(135deg,#fce7f3,#fbcfe8)}
.s-icon.fb{background:linear-gradient(135deg,#dbeafe,#bfdbfe)}
.s-name{font-size:0.65rem;font-weight:700;color:#78350f}
.s-handle{font-size:0.55rem;color:#78716c}
.social-bottom{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:16px}
.sb-card{background:rgba(255,255,255,0.15);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,0.2);border-radius:14px;padding:14px 8px;text-align:center;text-decoration:none;display:block}
.sb-card:active{transform:scale(0.95)}
.ic{width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 8px;font-size:1.3rem}
.ic.yt{background:#ef4444}.ic.ig{background:linear-gradient(135deg,#f43f5e,#a855f7,#ec4899)}.ic.fb{background:#2563eb}
.sb-name{font-size:0.7rem;font-weight:700;color:#fff}
.sb-handle{font-size:0.6rem;color:rgba(255,255,255,0.8)}
.quick-acts{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:16px}
.act-btn{padding:14px;border-radius:16px;border:none;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px}
.act-btn:active{transform:scale(0.96)}
.act-btn.pri{background:linear-gradient(135deg,#d97706,#92400e);color:#fff;box-shadow:0 4px 15px rgba(217,119,6,0.4)}
.act-btn.sec{background:rgba(255,255,255,0.2);color:#fff;border:1px solid rgba(255,255,255,0.3)}
.ref-card{background:linear-gradient(135deg,rgba(251,191,36,0.2),rgba(217,119,6,0.15));border:1px solid rgba(217,119,6,0.25);border-radius:16px;padding:14px;margin-top:16px;text-align:center}
.ref-box{display:flex;align-items:center;background:rgba(255,255,255,0.6);border-radius:10px;padding:8px 12px;margin:10px 0}
.ref-box code{flex:1;font-size:0.7rem;color:#78350f;word-break:break-all}
.copy-btn{background:linear-gradient(135deg,#d97706,#92400e);color:#fff;border:none;padding:6px 12px;border-radius:8px;font-size:0.7rem;font-weight:700;cursor:pointer}
.toast{position:fixed;top:20px;left:50%;transform:translateX(-50%) translateY(-100px);background:rgba(30,41,59,0.95);color:#fff;padding:12px 24px;border-radius:14px;font-weight:600;z-index:1000;transition:0.4s;display:flex;align-items:center;gap:8px}
.toast.show{transform:translateX(-50%) translateY(0)}
.toast.s{border-left:4px solid #22c55e}.toast.e{border-left:4px solid #ef4444}.toast.i{border-left:4px solid #3b82f6}
.modal{position:fixed;inset:0;background:rgba(0,0,0,0.6);backdrop-filter:blur(4px);z-index:100;display:none;align-items:center;justify-content:center;padding:20px}
.modal.act{display:flex}
.modal-box{background:linear-gradient(145deg,#fffbeb,#fef3c7);border:1px solid rgba(217,119,6,0.3);border-radius:24px;padding:24px;width:100%;max-width:360px;animation:modalIn 0.3s}
@keyframes modalIn{from{opacity:0;transform:scale(0.9)}to{opacity:1;transform:scale(1)}}
.m-title{font-size:1.1rem;font-weight:800;color:#78350f;text-align:center;margin-bottom:16px}
.m-input{width:100%;padding:12px;border-radius:12px;border:1px solid rgba(217,119,6,0.3);background:rgba(255,255,255,0.8);margin-bottom:12px;outline:none}
.m-btn{width:100%;padding:12px;border-radius:12px;border:none;font-weight:700;cursor:pointer}
.m-btn.pri{background:linear-gradient(135deg,#d97706,#92400e);color:#fff;margin-bottom:8px}
.m-btn.sec{background:rgba(217,119,6,0.1);color:#78350f}
.nav{position:fixed;bottom:0;left:0;right:0;background:rgba(255,248,235,0.95);backdrop-filter:blur(20px);border-top:1px solid rgba(217,119,6,0.2);padding:8px 16px;padding-bottom:max(8px,env(safe-area-inset-bottom));display:flex;justify-content:space-around;z-index:50}
.nav-btn{display:flex;flex-direction:column;align-items:center;gap:2px;padding:6px 12px;border:none;background:none;cursor:pointer}
.nav-btn .icon{font-size:1.3rem}
.nav-btn .lbl{font-size:0.6rem;font-weight:600;color:#78716c}
.confetti{position:fixed;width:8px;height:8px;z-index:200;pointer-events:none}
</style>
</head>
<body>
<div class="particles" id="particles"></div>
<div class="toast" id="toast"><span id="tIcon">✅</span><span id="tMsg">Success</span></div>
<div class="modal" id="wModal"><div class="modal-box"><div class="m-title">💰 Withdraw</div><p style="text-align:center;margin-bottom:12px;color:#78716c">Balance: <strong id="wBal">$0.00</strong></p><select id="wMethod" class="m-input"><option value="">Method</option><option value="paypal">PayPal</option><option value="crypto">USDT</option><option value="bank">Bank</option></select><input id="wAddr" class="m-input" placeholder="Address"><button class="m-btn pri" onclick="doWithdraw()">Submit</button><button class="m-btn sec" onclick="closeM('wModal')">Cancel</button></div></div>
<div class="modal" id="rModal"><div class="modal-box"><div class="m-title">👥 Invite</div><div class="ref-box"><code id="rLink">Loading...</code><button class="copy-btn" onclick="copyRef()">Copy</button></div><div style="display:flex;justify-content:space-around;margin:12px 0"><div><div style="font-size:1.3rem;font-weight:800;color:#78350f" id="rCount">0</div><div style="font-size:0.65rem;color:#78716c">Referrals</div></div><div><div style="font-size:1.3rem;font-weight:800;color:#22c55e" id="rEarn">0</div><div style="font-size:0.65rem;color:#78716c">Points</div></div></div><button class="m-btn pri" onclick="shareRef()">📤 Share</button><button class="m-btn sec" onclick="closeM('rModal')">Close</button></div></div>
<div class="container">
<div class="welcome-section"><div class="profile-ring"><img src="{{ banner }}" class="profile-img" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><circle cx=%2250%22 cy=%2250%22 r=%2250%22 fill=%22%23d97706%22/><text x=%2250%22 y=%2260%22 text-anchor=%22middle%22 fill=%22white%22 font-size=%2240%22>👤</text></svg>'"></div><div class="welcome-text">Welcome back,</div><div class="welcome-name" id="uName">Loading...</div></div>
<div class="card"><div class="card-title">📊 Ad-Earning Dashboard</div>
<div class="task-section"><div style="font-size:0.8rem;font-weight:700;color:#78350f;margin-bottom:12px">📅 Today's Tasks</div>
<div class="task-icons"><button class="task-btn ad" onclick="watchAd()" id="adBtn"><span class="icon">📺</span><span class="lbl">Daily Ad</span></button><button class="task-btn done" onclick="showToast('Check tasks','i')"><span class="icon">✅</span><span class="lbl">Done</span></button><button class="task-btn off" onclick="openOffer()"><span class="icon">💎</span><span class="lbl">Offer</span></button></div>
<div class="task-row"><span style="font-weight:600">Daily Ad</span><span class="badge done" id="adBadge">COMPLETED</span></div>
<div class="task-row"><span style="font-weight:600">Offerwall</span><span class="badge pend">PENDING</span></div></div>
<div class="grid-2"><div class="tracker"><div style="font-size:0.75rem;font-weight:700;color:#78350f;margin-bottom:10px">📊 AD Tracker</div><div class="tracker-info"><span class="tracker-badge">AD</span><div><div style="font-size:0.65rem;color:#78716c">VIEWED:</div><div style="font-size:0.75rem;font-weight:600" id="adSmall">0 / 2,000</div></div></div><div class="progress-big"><div class="num" id="adBig">0 / 2,000</div></div><div class="bar-bg"><div class="bar-fill" id="progFill" style="width:0%"></div></div></div>
<div class="withdraw"><div style="font-size:0.75rem;font-weight:700;color:#78350f;margin-bottom:10px">💰 Balance</div><div style="font-size:0.65rem;color:#78716c;margin-bottom:4px">AVAILABLE:</div><div class="bal-amt" id="balDisp">$0.00</div><button class="btn-w" onclick="openW()" id="wBtn">Request Payout</button></div></div>
<div style="margin-top:16px"><div style="font-size:0.8rem;font-weight:700;color:#78350f;margin-bottom:10px">🔗 Social Links</div>
<div class="social-grid"><a href="{{ yt }}" target="_blank" class="s-card"><div class="s-icon yt">▶️</div><div class="s-name">YouTube</div><div class="s-handle">@USSoccerPulse</div></a><a href="{{ ig }}" target="_blank" class="s-card"><div class="s-icon ig">📷</div><div class="s-name">Instagram</div><div class="s-handle">@digital_rockstar_m</div></a><a href="{{ fb }}" target="_blank" class="s-card"><div class="s-icon fb">📘</div><div class="s-name">Facebook</div><div class="s-handle">UltimateMediaSearch</div></a></div></div></div>
<div class="social-bottom"><a href="{{ yt }}" target="_blank" class="sb-card"><div class="ic yt">▶️</div><div class="sb-name">YouTube</div><div class="sb-handle">@USSoccerPulse</div></a><a href="{{ ig }}" target="_blank" class="sb-card"><div class="ic ig">📷</div><div class="sb-name">Instagram</div><div class="sb-handle">@digital_rockstar_m</div></a><a href="{{ fb }}" target="_blank" class="sb-card"><div class="ic fb">📘</div><div class="sb-name">Facebook</div><div class="sb-handle">UltimateMediaSearch</div></a></div>
<div class="quick-acts"><button class="act-btn pri" onclick="openM('rModal')">👥 Invite <span style="font-size:0.7rem;opacity:0.8">+50</span></button><button class="act-btn sec" onclick="refresh()">🔄 Refresh</button></div>
<div class="ref-card"><div style="font-size:0.8rem;font-weight:700;color:#78350f;margin-bottom:8px">👥 Referral Stats</div><div style="display:flex;justify-content:space-around"><div><div style="font-size:1.2rem;font-weight:800;color:#d97706" id="dRC">0</div><div style="font-size:0.65rem;color:#78716c">Friends</div></div><div><div style="font-size:1.2rem;font-weight:800;color:#22c55e" id="dRP">0</div><div style="font-size:0.65rem;color:#78716c">Points</div></div><div><div style="font-size:1.2rem;font-weight:800;color:#78350f" id="dTE">$0.00</div><div style="font-size:0.65rem;color:#78716c">Earned</div></div></div></div>
</div>
<nav class="nav"><button class="nav-btn"><span class="icon">🏠</span><span class="lbl">Home</span></button><button class="nav-btn"><span class="icon">📋</span><span class="lbl">Tasks</span></button><button class="nav-btn"><span class="icon">💰</span><span class="lbl">Earn</span></button><button class="nav-btn"><span class="icon">👤</span><span class="lbl">Profile</span></button></nav>
<script>
const fbCfg={{ fb }};firebase.initializeApp(fbCfg);const db=firebase.database();const CFG={{ cfg }};const p=new URLSearchParams(location.search);let UID=parseInt(p.get('id'))||0;let UNAME=p.get('name')||'User';let UDATA={};let ADC=0;let CLM=JSON.parse(localStorage.getItem('clm_'+UID)||'{}');const tg=window.Telegram?.WebApp;if(tg){tg.ready();tg.expand();if(tg.initDataUnsafe?.user){if(!UID)UID=tg.initDataUnsafe.user.id;if(UNAME==='User')UNAME=tg.initDataUnsafe.user.first_name||'User';}}
document.addEventListener('DOMContentLoaded',()=>{mkPart();if(!UID){showToast('❌ Open from Telegram','e');return;}document.getElementById('uName').textContent=UNAME+'!';loadU();setupL();});
async function loadU(){try{const s=await db.ref('users/'+UID).once('value');UDATA=s.val()||{};if(!UDATA.uid)await mkUser();ADC=UDATA.ad_views||0;updUI();}catch(e){console.error(e);}}
async function mkUser(){const ts=Date.now();const rc='UMS'+String(UID).split('').reverse().join('').slice(0,6).toUpperCase();const rb=p.get('ref')||null;UDATA={uid:UID,name:UNAME,referral_code:rc,referred_by:rb,points:0,total_earned:0,ad_views:0,tasks_completed:0,joined_at:ts,last_active:ts,last_ad_date:'',is_banned:false};await db.ref('users/'+UID).set(UDATA);if(rb)await procRef(rb,UID);showToast('🎉 Welcome '+UNAME+'!','s');}
async function procRef(code,nid){const s=await db.ref('users').orderByChild('referral_code').equalTo(code).once('value');const d=s.val();if(d){const rid=Object.keys(d)[0];const b=CFG.REFERRAL_BONUS;await db.ref('users/'+rid+'/points').transaction(v=>(v||0)+b);await db.ref('users/'+rid+'/total_earned').transaction(v=>(v||0)+b);await db.ref('users/'+rid+'/referral_count').transaction(v=>(v||0)+1);await db.ref('referrals/'+rid+'/'+nid).set({joined_at:Date.now(),bonus:b});}}
function setupL(){db.ref('users/'+UID).on('value',s=>{const d=s.val();if(d){UDATA={...UDATA,...d};ADC=d.ad_views||0;updUI();}});}
function updUI(){const pts=UDATA.points||0;const usd=(pts/CFG.POINTS_PER_DOLLAR).toFixed(2);const prog=Math.min((ADC/2000)*100,100);document.getElementById('balDisp').textContent='$'+usd;document.getElementById('wBal').textContent='$'+usd;document.getElementById('adSmall').textContent=ADC.toLocaleString()+' / 2,000';document.getElementById('adBig').textContent=ADC.toLocaleString()+' / 2,000';document.getElementById('progFill').style.width=prog+'%';const today=new Date().toDateString();const done=(UDATA.last_ad_date||'')===today;const b=document.getElementById('adBadge');b.textContent=done?'COMPLETED':'AVAILABLE';b.className='badge '+(done?'done':'pend');document.getElementById('wBtn').disabled=pts<CFG.POINTS_PER_DOLLAR;const rc=UDATA.referral_count||0;document.getElementById('rCount').textContent=rc;document.getElementById('rEarn').textContent=rc*CFG.REFERRAL_BONUS;document.getElementById('dRC').textContent=rc;document.getElementById('dRP').textContent=rc*CFG.REFERRAL_BONUS;document.getElementById('dTE').textContent='$'+((UDATA.total_earned||0)/CFG.POINTS_PER_DOLLAR).toFixed(2);const rl='https://t.me/UltimateMediaSearchBot?start='+(UDATA.referral_code||'UMS'+String(UID).split('').reverse().join('').slice(0,6).toUpperCase());document.getElementById('rLink').textContent=rl;}
async function watchAd(){const today=new Date().toDateString();if((UDATA.last_ad_date||'')===today){showToast('⚠️ Done today!','i');return;}window.open(CFG.AD_LINK,'_blank');const btn=document.getElementById('adBtn');btn.style.opacity='0.6';btn.disabled=true;let s=30;const lbl=btn.querySelector('.lbl');const t=setInterval(()=>{s--;lbl.textContent=s+'s';if(s<=0){clearInterval(t);compAd();}},1000);}
async function compAd(){const btn=document.getElementById('adBtn');btn.style.opacity='1';btn.disabled=false;btn.querySelector('.lbl').textContent='Daily Ad';try{await db.ref('users/'+UID).update({ad_views:(UDATA.ad_views||0)+1,points:(UDATA.points||0)+CFG.AD_POINTS,total_earned:(UDATA.total_earned||0)+CFG.AD_POINTS,last_ad_date:new Date().toDateString(),last_active:Date.now()});ADC=(UDATA.ad_views||0)+1;UDATA.points=(UDATA.points||0)+CFG.AD_POINTS;UDATA.total_earned=(UDATA.total_earned||0)+CFG.AD_POINTS;UDATA.last_ad_date=new Date().toDateString();updUI();showToast('🎉 +'+CFG.AD_POINTS+' Points!','s');conf();}catch(e){showToast('❌ Failed','e');}}
function openOffer(){window.open(CFG.AD_LINK,'_blank');showToast('💎 Offer opened!','i');}
function openW(){if((UDATA.points||0)<CFG.POINTS_PER_DOLLAR){showToast('💰 Need 100 pts!','e');return;}document.getElementById('wModal').classList.add('act');}
function closeM(id){document.getElementById(id).classList.remove('act');}
async function doWithdraw(){const m=document.getElementById('wMethod').value;const a=document.getElementById('wAddr').value.trim();if(!m||!a){showToast('⚠️ Fill all','e');return;}const pts=UDATA.points||0;try{await db.ref('withdrawals/'+UID+'/'+Date.now()).set({amount:pts,usd:(pts/CFG.POINTS_PER_DOLLAR).toFixed(2),method:m,address:a,status:'pending',at:Date.now()});await db.ref('users/'+UID).update({points:0,total_withdrawn:(UDATA.total_withdrawn||0)+pts});UDATA.points=0;closeM('wModal');updUI();showToast('✅ Submitted! 24-48h','s');conf();}catch(e){showToast('❌ Failed','e');}}
function openM(id){document.getElementById(id).classList.add('act');}
function copyRef(){navigator.clipboard.writeText(document.getElementById('rLink').textContent).then(()=>showToast('🔗 Copied!','s'));}
function shareRef(){const l=document.getElementById('rLink').textContent;if(tg)tg.openTelegramLink('https://t.me/share/url?url='+encodeURIComponent(l));else window.open('https://t.me/share/url?url='+encodeURIComponent(l),'_blank');}
function showToast(m,t='s'){const i={s:'✅',e:'❌',i:'ℹ️'};document.getElementById('tIcon').textContent=i[t]||'✅';document.getElementById('tMsg').textContent=m;const el=document.getElementById('toast');el.className='toast '+t+' show';setTimeout(()=>el.classList.remove('show'),3500);}
function refresh(){showToast('🔄 Refreshing...','i');loadU().then(()=>showToast('✅ Done!','s'));}
function mkPart(){const c=document.getElementById('particles');for(let i=0;i<20;i++){const p=document.createElement('div');p.className='particle';p.style.left=Math.random()*100+'%';p.style.animationDuration=(Math.random()*10+8)+'s';p.style.animationDelay=(Math.random()*10)+'s';p.style.width=(Math.random()*6+3)+'px';p.style.height=p.style.width;c.appendChild(p);}}
function conf(){const cols=['#f59e0b','#d97706','#92400e','#22c55e','#3b82f6','#ef4444'];for(let i=0;i<30;i++){const c=document.createElement('div');c.className='confetti';c.style.left=Math.random()*100+'vw';c.style.top='-10px';c.style.background=cols[Math.floor(Math.random()*cols.length)];c.style.borderRadius=Math.random()>0.5?'50%':'2px';c.style.width=(Math.random()*8+4)+'px';c.style.height=(Math.random()*8+4)+'px';document.body.appendChild(c);const d=Math.random()*2000+1500;const x=(Math.random()-0.5)*200;c.animate([{transform:'translateY(0) translateX(0) rotate(0deg)',opacity:1},{transform:'translateY(100vh) translateX('+x+'px) rotate('+Math.random()*720+'deg)',opacity:0}],{duration:d,easing:'cubic-bezier(0.25,0.46,0.45,0.94)'}).onfinish=()=>c.remove();}}
document.querySelectorAll('.modal').forEach(m=>m.addEventListener('click',e=>{if(e.target===m)m.classList.remove('act');}));
</script>
</body>
</html>"""

# ─────────────────────────────────────────────────────────────────────
# 🌐 Routes (Matching vercel.json)
# ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
    """Premium Dashboard Route"""
    uid = request.args.get('id', type=int)
    name = request.args.get('name', 'User')
    
    if not uid:
        return '<h1 style="text-align:center;padding:40px;color:#78350f">⚠️ Open from Telegram bot with /start</h1>'
    
    # Initialize user if needed
    if not get_user(uid):
        create_user(uid, name)
    
    return render_template_string(
        DASHBOARD_HTML,
        fb=json.dumps(FRONTEND_FIREBASE),
        cfg=json.dumps(APP_CONFIG),
        banner=APP_CONFIG['BANNER_IMAGE'],
        yt=APP_CONFIG['YOUTUBE_LINK'],
        ig=APP_CONFIG['INSTAGRAM_LINK'],
        fb=APP_CONFIG['FACEBOOK_LINK']
    )

@app.route('/welcome')
def welcome():
    """Welcome Route"""
    return """<h1 style="text-align:center;padding:40px;color:#78350f">🌟 Welcome to Ultimate Media Search!</h1>"""

@app.route('/admin')
def admin():
    """Admin Route"""
    return """<h1 style="text-align:center;padding:40px;color:#78350f">🔒 Admin Panel</h1>"""

@app.route('/api/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def api_handler(path):
    """API Routes Handler"""
    if request.method == 'OPTIONS':
        return '', 204
    
    if path == 'earn/ad':
        uid = request.args.get('user_id', type=int) or (request.get_json() or {}).get('user_id')
        if uid and add_points(uid, APP_CONFIG['AD_POINTS'], 'ad_view'):
            return jsonify({'success': True, 'points_added': APP_CONFIG['AD_POINTS']})
        return jsonify({'success': False}), 400
    
    if path == 'earn/social':
        data = request.get_json() or {}
        uid = data.get('user_id')
        task = data.get('task')
        if uid and task and add_points(int(uid), APP_CONFIG['SOCIAL_POINTS'], f'social_{task}'):
            return jsonify({'success': True, 'points_added': APP_CONFIG['SOCIAL_POINTS']})
        return jsonify({'success': False}), 400
    
    if path == 'user':
        uid = request.args.get('id', type=int) or (request.get_json() or {}).get('user_id')
        if uid:
            user = get_user(uid)
            return jsonify({'success': True, 'data': user}) if user else jsonify({'success': False})
        return jsonify({'success': False}), 400
    
    return jsonify({'error': 'Not found'}), 404

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Telegram Webhook Handler"""
    try:
        update = telebot.types.Update.de_json(request.get_json(force=True))
        if update:
            bot.process_new_updates([update])
        return '', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """Health Check"""
    return jsonify({
        'status': 'healthy',
        'service': 'ultimate-media-search',
        'timestamp': int(time.time() * 1000)
    }), 200

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Static Files"""
    return send_from_directory('../static', filename)

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

# ─────────────────────────────────────────────────────────────────────
# 🚀 Vercel Entry Point
# ─────────────────────────────────────────────────────────────────────
app.logger = logger
logger.info("✅ Serverless function ready!")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🚀 Starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

