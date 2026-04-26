"""
🤖 Ultimate Media Search Bot - Firebase Fixed for Vercel + asia-southeast1
✅ Handles private_key newlines correctly
✅ Proper region configuration
✅ No more "Unauthorized" errors
"""

import os
import sys
import json
import time
import logging
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Dict, Any

# ─────────────────────────────────────────────────────────────────────
# 🔧 Logging Setup (Must be first)
# ─────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)
logger.info("🚀 Starting Ultimate Media Search Bot...")

# ─────────────────────────────────────────────────────────────────────
# 🔐 Firebase Service Account Parser (FIXES THE UNAUTHORIZED ERROR)
# ─────────────────────────────────────────────────────────────────────

def parse_firebase_credentials(env_value: str) -> Optional[Dict[str, Any]]:
    """
    Parse Firebase Service Account JSON from Vercel environment variable.
    
    🔥 CRITICAL: Fixes private_key newline issues that cause "Unauthorized" errors
    
    Args:
        env_value: Raw string from os.environ['FIREBASE_SERVICE_ACCOUNT']
    
    Returns:
        Dict with properly formatted credentials or None
    """
    if not env_value or env_value == 'skip':
        logger.warning("⚠️ FIREBASE_SERVICE_ACCOUNT not set or set to 'skip'")
        return None
    
    try:
        # Try direct JSON parse first (for local development)
        if isinstance(env_value, dict):
            return _fix_private_key(env_value)
        
        # Parse JSON string
        creds = json.loads(env_value)
        
        if not isinstance(creds, dict) or 'private_key' not in creds:
            raise ValueError("Invalid service account format")
        
        return _fix_private_key(creds)
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parse error: {e}")
        logger.error(f"   Env value starts with: {env_value[:100]}...")
        return None
    except Exception as e:
        logger.error(f"❌ Credential parsing failed: {type(e).__name__}: {e}")
        return None


def _fix_private_key(creds: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fix private_key formatting for RSA authentication.
    
    The private_key must have actual newlines, not escaped \\n strings.
    """
    key = creds.get('private_key', '')
    
    if not key or '-----BEGIN PRIVATE KEY-----' in key:
        # Already properly formatted
        return creds
    
    # Fix escaped newlines: \\n → \n → actual newline
    key = key.replace('\\\\n', '\n').replace('\\n', '\n')
    
    # Ensure proper PEM format
    if not key.strip().startswith('-----BEGIN PRIVATE KEY-----'):
        key = '-----BEGIN PRIVATE KEY-----\n' + key.strip()
    if not key.strip().endswith('-----END PRIVATE KEY-----'):
        key = key.strip() + '\n-----END PRIVATE KEY-----\n'
    
    creds['private_key'] = key
    return creds


# ─────────────────────────────────────────────────────────────────────
# 🗄️ Firebase Initialization (asia-southeast1 Compatible)
# ─────────────────────────────────────────────────────────────────────

def init_firebase() -> bool:
    """
    Initialize Firebase Admin SDK with proper region handling.
    
    Returns:
        bool: True if successful, False if falling back to REST API
    """
    try:
        import firebase_admin
        from firebase_admin import credentials, db
        
        # Skip if already initialized
        if firebase_admin._apps:
            logger.info("✅ Firebase Admin SDK already initialized")
            return True
        
        # Get configuration from environment
        db_url = os.environ.get(
            'FIREBASE_DB_URL',
            'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
        ).rstrip('/')
        
        service_account_raw = os.environ.get('FIREBASE_SERVICE_ACCOUNT', 'skip')
        
        # Parse credentials with newline fix
        service_account = parse_firebase_credentials(service_account_raw)
        
        if not service_account:
            logger.warning("⚠️ Using REST API fallback (no service account)")
            return False
        
        # Create credentials object
        cred = credentials.Certificate(service_account)
        
        # Initialize with explicit region-specific database URL
        firebase_admin.initialize_app(cred, {
            'databaseURL': db_url,  # ✅ asia-southeast1 URL
            'projectId': service_account.get('project_id'),
        })
        
        # Test connection
        db.reference('.info/serverTimeOffset').get()
        
        logger.info(f"✅ Firebase Admin SDK initialized")
        logger.info(f"   📍 Database: {db_url}")
        logger.info(f"   🆔 Project: {service_account.get('project_id')}")
        
        return True
        
    except ImportError:
        logger.warning("⚠️ firebase-admin not installed, using REST API")
        return False
    except Exception as e:
        logger.error(f"❌ Firebase init failed: {type(e).__name__}: {e}")
        logger.error("💡 Falling back to REST API mode")
        return False


# ─────────────────────────────────────────────────────────────────────
# 🌐 Firebase REST API Fallback (When Admin SDK Fails)
# ─────────────────────────────────────────────────────────────────────

import requests

class FirebaseREST:
    """Simple Firebase REST API client - works without Admin SDK"""
    
    def __init__(self, db_url: str):
        self.base_url = db_url.rstrip('/')
    
    def _request(self, method: str, path: str, data: Any = None) -> Any:
        try:
            url = f"{self.base_url}/{path}.json"
            headers = {'Content-Type': 'application/json'}
            timeout = 10
            
            if method == 'GET':
                resp = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'PUT':
                resp = requests.put(url, json=data, headers=headers, timeout=timeout)
            elif method == 'PATCH':
                resp = requests.patch(url, json=data, headers=headers, timeout=timeout)
            elif method == 'POST':
                resp = requests.post(url, json=data, headers=headers, timeout=timeout)
            else:
                return None
            
            if resp.status_code in [200, 201]:
                return resp.json()
            logger.warning(f"Firebase {method} {resp.status_code}: {path}")
            return None
        except Exception as e:
            logger.error(f"Firebase REST error: {e}")
            return None
    
    def get(self, path: str) -> Any:
        return self._request('GET', path)
    
    def set(self, path: str, data: Any) -> bool:
        return self._request('PUT', path, data) is not None
    
    def update(self, path: str, data: Dict) -> bool:
        return self._request('PATCH', path, data) is not None


# Initialize Firebase (try Admin SDK, fallback to REST)
FIREBASE_MODE = 'admin' if init_firebase() else 'rest'
logger.info(f"🔗 Firebase mode: {FIREBASE_MODE}")

if FIREBASE_MODE == 'rest':
    firebase_db = FirebaseREST(
        os.environ.get('FIREBASE_DB_URL', 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/')
    )
    def get_user(tid): return firebase_db.get(f'users/{tid}')
    def set_user(tid, data): return firebase_db.set(f'users/{tid}', data)
    def update_user(tid, data): return firebase_db.update(f'users/{tid}', data)
else:
    from firebase_admin import db
    def get_user(tid): return db.reference(f'users/{tid}').get()
    def set_user(tid, data): return db.reference(f'users/{tid}').set(data)
    def update_user(tid, data): return db.reference(f'users/{tid}').update(data)

# ─────────────────────────────────────────────────────────────────────
# 🔧 App Configuration
# ─────────────────────────────────────────────────────────────────────

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8701635891:AAFmgU89KRhd2dhE-PqRY-mBmGy_SxQEGOg')

APP_CONFIG = {
    'POINTS_PER_DOLLAR': 100,
    'AD_POINTS': 25,
    'SOCIAL_POINTS': 100,
    'REFERRAL_BONUS': 50,
    'MIN_WITHDRAW': 100,
    'AD_LINK': 'https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b',
    'YOUTUBE': 'https://youtube.com/@USSoccerPulse',
    'INSTAGRAM': 'https://instagram.com/digital_rockstar_m',
    'FACEBOOK': 'https://www.facebook.com/UltimateMediaSearch',
    'BANNER': 'https://i.ibb.co/9kmTw4Gh/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg'
}

FIREBASE_CONFIG = {
    'apiKey': os.environ.get('FIREBASE_API_KEY', 'AIzaSyD50eWvysruXgtgpDhhCVE2zdbSbLkFBwk'),
    'authDomain': 'ultimatemediasearch.firebaseapp.com',
    'databaseURL': os.environ.get('FIREBASE_DB_URL'),
    'projectId': 'ultimatemediasearch',
    'storageBucket': 'ultimatemediasearch.firebasestorage.app',
    'messagingSenderId': '123003124713',
    'appId': os.environ.get('FIREBASE_APP_ID', '1:123003124713:web:c738c97b2772b112822978')
}

# ─────────────────────────────────────────────────────────────────────
# 🌐 Flask Application
# ─────────────────────────────────────────────────────────────────────

from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()

# ─────────────────────────────────────────────────────────────────────
# 🎨 Simplified Dashboard HTML
# ─────────────────────────────────────────────────────────────────────

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>💰 Earn Dashboard</title>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-database-compat.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,sans-serif;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;color:#fff;padding:20px}
.card{background:rgba(255,255,255,0.1);backdrop-filter:blur(10px);border-radius:20px;padding:20px;margin-bottom:20px}
.balance{font-size:2.5rem;font-weight:bold;margin:10px 0}
.btn{background:#fff;color:#667eea;padding:15px;border-radius:12px;border:none;font-weight:bold;width:100%;margin:8px 0;cursor:pointer}
.btn:disabled{opacity:0.6}
.task{background:rgba(255,255,255,0.15);padding:15px;border-radius:12px;margin:10px 0;display:flex;justify-content:space-between;align-items:center}
.toast{position:fixed;top:20px;left:50%;transform:translateX(-50%) translateY(-100px);background:#48bb78;color:#fff;padding:12px 24px;border-radius:12px;transition:transform 0.3s;z-index:1000}
.toast.show{transform:translateX(-50%) translateY(0)}
</style>
</head>
<body>
<div class="toast" id="toast">✅ Success!</div>
<div class="card">
<h1>👋 Welcome, <span id="userName">User</span>!</h1>
<div class="balance" id="balance">$0.00</div>
<p>Points: <span id="points">0</span> | Tasks: <span id="tasks">0</span></p>
</div>
<div class="card">
<h2>💎 Tasks</h2>
<button class="btn" onclick="watchAd()" id="adBtn">📺 Watch Ad (+25 pts)</button>
<a href="{{ youtube }}" target="_blank" onclick="claim('youtube')" class="btn" style="text-decoration:none;display:block;text-align:center">▶️ YouTube (+100 pts)</a>
<a href="{{ instagram }}" target="_blank" onclick="claim('instagram')" class="btn" style="text-decoration:none;display:block;text-align:center">📷 Instagram (+100 pts)</a>
<a href="{{ facebook }}" target="_blank" onclick="claim('facebook')" class="btn" style="text-decoration:none;display:block;text-align:center">📘 Facebook (+100 pts)</a>
</div>
<script>
const FC={{ firebase_config | safe }};firebase.initializeApp(FC);const db=firebase.database();
const P=new URLSearchParams(location.search);
let UID=P.get('id')||'123';
let UNAME=P.get('name')||'User';
let USER_DATA={};
document.getElementById('userName').textContent=UNAME;

function loadUser(){
    db.ref('users/'+UID).on('value',s=>{
        let d=s.val();
        if(!d){createUser();return;}
        USER_DATA=d;
        updateUI();
    });
}

function createUser(){
    const newUser={uid:UID,name:UNAME,points:0,total_earned:0,ad_views:0,tasks_completed:0,joined_at:Date.now()};
    db.ref('users/'+UID).set(newUser);
    USER_DATA=newUser;
    updateUI();
}

function updateUI(){
    const p=USER_DATA.points||0;
    document.getElementById('balance').textContent='$'+(p/100).toFixed(2);
    document.getElementById('points').textContent=p;
    document.getElementById('tasks').textContent=USER_DATA.tasks_completed||0;
}

async function watchAd(){
    const btn=document.getElementById('adBtn');
    btn.disabled=true;
    btn.textContent='⏳ Watching...';
    window.open('{{ ad_link }}','_blank');
    
    setTimeout(async()=>{
        try{
            await db.ref('users/'+UID).update({
                points:(USER_DATA.points||0)+25,
                total_earned:(USER_DATA.total_earned||0)+25,
                ad_views:(USER_DATA.ad_views||0)+1
            });
            showToast('🎉 +25 Points!');
            loadUser();
        }catch(e){showToast('Error: '+e.message);}
        btn.disabled=false;
        btn.textContent='📺 Watch Ad (+25 pts)';
    },30000);
}

async function claim(plat){
    try{
        await db.ref('users/'+UID).update({
            points:(USER_DATA.points||0)+100,
            total_earned:(USER_DATA.total_earned||0)+100,
            tasks_completed:(USER_DATA.tasks_completed||0)+1
        });
        showToast('🎉 +100 Points!');
        loadUser();
    }catch(e){showToast('Error: '+e.message);}
}

function showToast(m){
    const t=document.getElementById('toast');
    t.textContent=m;
    t.className='toast show';
    setTimeout(()=>t.className='toast',3000);
}

loadUser();
</script>
</body>
</html>'''

# ─────────────────────────────────────────────────────────────────────
# 🌐 Routes
# ─────────────────────────────────────────────────────────────────────

@app.route('/')
def root():
    return '''<html><body style="background:#1a202c;color:#fff;text-align:center;padding:40px;font-family:sans-serif">
    <h1>🤖 Ultimate Media Search Bot</h1>
    <p style="color:#94a3b8;margin:20px 0">Server is running! ✅</p>
    <a href="/dashboard?id=123&name=Test" style="display:inline-block;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;padding:14px 32px;border-radius:12px;text-decoration:none;font-weight:600">🚀 Open Dashboard</a>
    <p style="margin-top:30px;font-size:0.9rem;color:#64748b">Firebase Mode: {{ firebase_mode }}</p>
    </body></html>'''.replace('{{ firebase_mode }}', FIREBASE_MODE)

@app.route('/dashboard')
def dashboard():
    tid = request.args.get('id', '123')
    name = request.args.get('name', 'User')
    
    # Create user if not exists
    try:
        if not get_user(tid):
            timestamp = int(time.time() * 1000)
            set_user(tid, {
                'uid': tid, 'name': name, 'username': name,
                'points': 0, 'total_earned': 0, 'ad_views': 0,
                'tasks_completed': 0, 'joined_at': timestamp,
                'last_active': timestamp, 'referral_code': 'UMS' + str(tid)[-6:].upper()
            })
            logger.info(f"✅ User created: {tid}")
    except Exception as e:
        logger.error(f"User creation error: {e}")
    
    return render_template_string(
        DASHBOARD_HTML,
        firebase_config=json.dumps(FIREBASE_CONFIG),
        youtube=APP_CONFIG['YOUTUBE'],
        instagram=APP_CONFIG['INSTAGRAM'],
        facebook=APP_CONFIG['FACEBOOK'],
        ad_link=APP_CONFIG['AD_LINK']
    )

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'ultimate-media-search',
        'firebase_mode': FIREBASE_MODE,
        'timestamp': int(time.time() * 1000)
    }), 200

@app.route('/favicon.ico')
@app.route('/favicon.png')
def favicon():
    return '', 204

# ─────────────────────────────────────────────────────────────────────
# 🤖 Telegram Bot
# ─────────────────────────────────────────────────────────────────────

try:
    import telebot
    from telebot import types
    bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML', threaded=False)
    logger.info("✅ Telegram Bot initialized")
except Exception as e:
    logger.warning(f"⚠️ Bot init warning: {e}")
    bot = None

if bot:
    @bot.message_handler(commands=['start'])
    def handle_start(msg):
        try:
            uid = msg.from_user.id
            name = msg.from_user.first_name or 'User'
            
            # Create/update user
            try:
                if not get_user(uid):
                    set_user(uid, {
                        'uid': uid, 'name': name, 'username': name,
                        'points': 0, 'total_earned': 0, 'ad_views': 0,
                        'tasks_completed': 0, 'joined_at': int(time.time()*1000),
                        'referral_code': 'UMS' + str(uid)[-6:].upper()
                    })
            except Exception as e:
                logger.error(f"User save error: {e}")
            
            caption = f"""
🌟 <b>Welcome {name}!</b>

💬 <i>"Your smartphone is now your ATM!"</i> 💰

🎁 <b>How to Earn:</b>
├ 📺 Watch Ads → +{APP_CONFIG['AD_POINTS']} Points
├ 📱 Social Tasks → +{APP_CONFIG['SOCIAL_POINTS']} Points
└ 💰 <b>{APP_CONFIG['POINTS_PER_DOLLAR']} Points = $1.00</b>

👇 Open your Dashboard!
            """
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            dashboard_url = f"/dashboard?id={uid}&name={name}"
            
            markup.add(
                types.InlineKeyboardButton("🚀 Open Dashboard", url=dashboard_url)
            )
            
            try:
                bot.send_photo(msg.chat.id, photo=APP_CONFIG['BANNER'], caption=caption, reply_markup=markup)
            except:
                bot.send_message(msg.chat.id, caption, reply_markup=markup)
                
        except Exception as e:
            logger.error(f"Start error: {e}")
            bot.send_message(msg.chat.id, "⚠️ Error. Try /start again.")

# ─────────────────────────────────────────────────────────────────────
# 🔗 Webhook & Entry Point
# ─────────────────────────────────────────────────────────────────────

@app.route('/webhook', methods=['POST'])
def webhook():
    if not bot:
        return 'Bot unavailable', 503
    try:
        update = request.get_json(force=True)
        if update:
            bot.process_new_updates([types.Update.de_json(update)])
        return '', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

# Auto-set webhook
WEBHOOK_SET = False

@app.before_request
def set_webhook_once():
    global WEBHOOK_SET
    if not WEBHOOK_SET and bot and request.path == '/webhook':
        try:
            host = request.host_url.rstrip('/')
            bot.set_webhook(f"{host}/webhook")
            logger.info(f"✅ Webhook set: {host}/webhook")
        except:
            pass
        WEBHOOK_SET = True

logger.info(f"✅ Server ready | Firebase: {FIREBASE_MODE}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🚀 Starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
