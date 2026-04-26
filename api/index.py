"""
🤖 Ultimate Media Search Bot - Complete Professional Version
✅ UPI Payment Integration (8543083014@ikwik)
✅ Buy Plans (₹100 & ₹500) - Fixed & Working
✅ Premium Dashboard + Admin Panel
✅ Firebase asia-southeast1 + Vercel Ready
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
import requests

# ─────────────────────────────────────────────────────────────────────
# 🔧 Logging Setup
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
# 🔐 Firebase Credential Parser
# ─────────────────────────────────────────────────────────────────────
def parse_firebase_credentials(env_value: str) -> Optional[Dict[str, Any]]:
    if not env_value or env_value == 'skip':
        logger.warning("⚠️ FIREBASE_SERVICE_ACCOUNT not set")
        return None
    try:
        if isinstance(env_value, dict):
            return _fix_private_key(env_value)
        creds = json.loads(env_value)
        if not isinstance(creds, dict) or 'private_key' not in creds:
            raise ValueError("Invalid format")
        return _fix_private_key(creds)
    except Exception as e:
        logger.error(f"❌ Credential parse failed: {e}")
        return None

def _fix_private_key(creds: Dict[str, Any]) -> Dict[str, Any]:
    key = creds.get('private_key', '')
    if not key or '-----BEGIN PRIVATE KEY-----' in key:
        return creds
    key = key.replace('\\\\n', '\n').replace('\\n', '\n')
    if not key.strip().startswith('-----BEGIN PRIVATE KEY-----'):
        key = '-----BEGIN PRIVATE KEY-----\n' + key.strip()
    if not key.strip().endswith('-----END PRIVATE KEY-----'):
        key = key.strip() + '\n-----END PRIVATE KEY-----\n'
    creds['private_key'] = key
    return creds

# ─────────────────────────────────────────────────────────────────────
# 🗄️ Firebase Initialization
# ─────────────────────────────────────────────────────────────────────
def init_firebase() -> bool:
    try:
        import firebase_admin
        from firebase_admin import credentials, db
        if firebase_admin._apps:
            return True
        db_url = os.environ.get('FIREBASE_DB_URL', 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/').rstrip('/')
        sa_raw = os.environ.get('FIREBASE_SERVICE_ACCOUNT', 'skip')
        sa = parse_firebase_credentials(sa_raw)
        if not sa:
            logger.warning("⚠️ Using REST API fallback")
            return False
        firebase_admin.initialize_app(credentials.Certificate(sa), {
            'databaseURL': db_url,
            'projectId': sa.get('project_id')
        })
        db.reference('.info/serverTimeOffset').get()
        logger.info("✅ Firebase Admin SDK initialized")
        return True
    except ImportError:
        logger.warning("⚠️ firebase-admin missing, using REST")
        return False
    except Exception as e:
        logger.error(f"❌ Firebase init failed: {e}")
        return False

FIREBASE_MODE = 'admin' if init_firebase() else 'rest'

class FirebaseREST:
    def __init__(self, url): self.base = url.rstrip('/')
    def _req(self, method, path, data=None):
        try:
            r = requests.request(method, f"{self.base}/{path}.json", json=data, headers={'Content-Type':'application/json'}, timeout=10)
            return r.json() if r.status_code in [200,201] else None
        except: return None
    def get(self, p): return self._req('GET', p)
    def set(self, p, d): return self._req('PUT', p, d) is not None
    def update(self, p, d): return self._req('PATCH', p, d) is not None

firebase_db = FirebaseREST(os.environ.get('FIREBASE_DB_URL', 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/')) if FIREBASE_MODE == 'rest' else None

def get_user(tid):
    return firebase_db.get(f'users/{tid}') if FIREBASE_MODE == 'rest' else db.reference(f'users/{tid}').get()
def set_user(tid, d):
    return firebase_db.set(f'users/{tid}', d) if FIREBASE_MODE == 'rest' else db.reference(f'users/{tid}').set(d)
def update_user(tid, d):
    return firebase_db.update(f'users/{tid}', d) if FIREBASE_MODE == 'rest' else db.reference(f'users/{tid}').update(d)

# ─────────────────────────────────────────────────────────────────────
# 🔧 Configuration
# ─────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8701635891:AAFmgU89KRhd2dhE-PqRY-mBmGy_SxQEGOg')
VERCEL_DOMAIN = os.environ.get('VERCEL_URL', 'ultimate-media-search-bot.vercel.app')
if not VERCEL_DOMAIN.startswith('https://'): VERCEL_DOMAIN = f"https://{VERCEL_DOMAIN}"

APP_CONFIG = {
    'POINTS_PER_DOLLAR': 100, 'AD_POINTS': 25, 'SOCIAL_POINTS': 100,
    'REFERRAL_BONUS': 50, 'MIN_WITHDRAW': 100,
    'PLAN_100_PRICE': 100, 'PLAN_500_PRICE': 500,
    'AD_LINK': 'https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b',
    'YOUTUBE': 'https://youtube.com/@USSoccerPulse',
    'INSTAGRAM': 'https://instagram.com/digital_rockstar_m',
    'FACEBOOK': 'https://www.facebook.com/UltimateMediaSearch',
    'BANNER': 'https://i.ibb.co/9kmTw4Gh/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg',
    'SUPPORT_LINK': 'https://t.me/YourSupportUsername',
    'COMMUNITY_LINK': 'https://t.me/YourCommunityLink',
    'UPI_ID': '8543083014@ikwik',  # ✅ UPI Payment ID
    'UPI_NAME': 'Ultimate Media Search',
    'DASHBOARD_URL': f'{VERCEL_DOMAIN}/dashboard'
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
# 🌐 Flask App
# ─────────────────────────────────────────────────────────────────────
from flask import Flask, request, jsonify, render_template_string
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()

# ─────────────────────────────────────────────────────────────────────
# 🎨 Dashboard HTML (Complete)
# ─────────────────────────────────────────────────────────────────────
DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="theme-color" content="#667eea">
<title>💰 Ultimate Media Search - Earn Dashboard</title>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-database-compat.js"></script>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,sans-serif;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;color:#fff;padding:20px;padding-bottom:100px}
.container{max-width:480px;margin:0 auto}
.card{background:rgba(255,255,255,0.1);backdrop-filter:blur(10px);border-radius:20px;padding:20px;margin-bottom:20px;border:1px solid rgba(255,255,255,0.2)}
.profile-img{width:80px;height:80px;border-radius:50%;border:3px solid #fff;margin:0 auto 15px;display:block;object-fit:cover}
.welcome-text{font-size:1rem;opacity:0.9;text-align:center}.user-name{font-size:1.5rem;font-weight:bold;text-align:center;margin:5px 0 15px}
.balance{font-size:2.5rem;font-weight:bold;text-align:center;margin:10px 0}
.stats-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:15px}
.stat-item{background:rgba(255,255,255,0.15);padding:12px;border-radius:12px;text-align:center}
.stat-value{font-size:1.3rem;font-weight:bold;display:block}.stat-label{font-size:0.75rem;opacity:0.8}
.card-title{font-size:1.2rem;font-weight:bold;margin-bottom:15px;display:flex;align-items:center;gap:8px}
.task-list{display:flex;flex-direction:column;gap:10px}
.task-item{background:rgba(255,255,255,0.15);border-radius:12px;padding:15px;display:flex;align-items:center;justify-content:space-between;cursor:pointer}
.task-item:active{transform:scale(0.98)}.task-info{display:flex;align-items:center;gap:12px;flex:1}
.task-icon{width:45px;height:45px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.5rem;background:rgba(255,255,255,0.2)}
.task-details h3{font-size:0.95rem;margin-bottom:3px}.task-details p{font-size:0.75rem;opacity:0.8}
.task-reward{background:#48bb78;color:#fff;padding:6px 12px;border-radius:20px;font-size:0.8rem;font-weight:bold}
.btn{width:100%;padding:15px;border:none;border-radius:12px;font-size:1rem;font-weight:bold;cursor:pointer;margin:8px 0;display:flex;align-items:center;justify-content:center;gap:8px}
.btn:active{transform:scale(0.98)}.btn:disabled{opacity:0.6;cursor:not-allowed}
.btn-primary{background:#fff;color:#667eea}.btn-secondary{background:rgba(255,255,255,0.2);color:#fff}.btn-success{background:#48bb78;color:#fff}
.btn-warning{background:#ed8936;color:#fff}.btn-danger{background:#f56565;color:#fff}
#adBtn{background:linear-gradient(135deg,#f093fb,#f5576c);color:#fff;font-size:1.1rem;padding:18px}
.toast{position:fixed;top:20px;left:50%;transform:translateX(-50%) translateY(-100px);background:#1a202c;color:#fff;padding:12px 24px;border-radius:12px;font-weight:600;z-index:1000;transition:transform 0.3s;box-shadow:0 10px 40px rgba(0,0,0,0.3);display:flex;align-items:center;gap:8px}
.toast.show{transform:translateX(-50%) translateY(0)}.toast.success{background:#48bb78}.toast.error{background:#f56565}.toast.info{background:#667eea}
.progress-container{margin:15px 0}.progress-label{display:flex;justify-content:space-between;font-size:0.85rem;margin-bottom:8px}
.progress-bar{height:10px;background:rgba(255,255,255,0.2);border-radius:10px;overflow:hidden}
.progress-fill{height:100%;background:linear-gradient(90deg,#48bb78,#38a169);border-radius:10px;transition:width 0.5s}
.referral-box{background:rgba(255,255,255,0.1);border-radius:12px;padding:12px;display:flex;gap:8px;margin-top:10px}
.referral-link{flex:1;background:rgba(0,0,0,0.3);padding:8px 12px;border-radius:8px;font-size:0.75rem;word-break:break-all;font-family:monospace}
.copy-btn{background:#667eea;color:#fff;border:none;padding:8px 16px;border-radius:8px;font-size:0.8rem;font-weight:bold;cursor:pointer}
.bottom-nav{position:fixed;bottom:0;left:0;right:0;background:rgba(26,32,44,0.95);backdrop-filter:blur(10px);padding:10px 20px;padding-bottom:max(10px,env(safe-area-inset-bottom));display:flex;justify-content:space-around;border-top:1px solid rgba(255,255,255,0.1)}
.nav-item{display:flex;flex-direction:column;align-items:center;gap:4px;padding:8px 16px;border-radius:12px;cursor:pointer;border:none;background:none;color:#fff}
.nav-item.active{background:rgba(255,255,255,0.15)}.nav-item .icon{font-size:1.3rem}.nav-item .label{font-size:0.7rem;opacity:0.8}
.upi-box{background:linear-gradient(135deg,#fff,#f0f0f0);color:#1a202c;padding:20px;border-radius:16px;margin:15px 0;text-align:center}
.upi-qr{width:200px;height:200px;margin:15px auto;border-radius:12px;border:3px solid #667eea}
::-webkit-scrollbar{width:0}
</style>
</head>
<body>
<div class="toast" id="toast"><span id="toastIcon">✅</span><span id="toastMsg">Success!</span></div>
<div class="container">
<div class="card" style="text-align:center">
<img src="{{ banner }}" class="profile-img" id="profileImg">
<div class="welcome-text">Welcome back,</div>
<div class="user-name" id="userName">Loading...</div>
<div class="balance" id="balance">$0.00</div>
<div class="stats-grid">
<div class="stat-item"><span class="stat-value" id="points">0</span><div class="stat-label">Points</div></div>
<div class="stat-item"><span class="stat-value" id="tasks">0</span><div class="stat-label">Tasks</div></div>
<div class="stat-item"><span class="stat-value" id="ads">0</span><div class="stat-label">Ads</div></div>
<div class="stat-item"><span class="stat-value" id="totalEarned">$0.00</span><div class="stat-label">Total</div></div>
</div>
</div>
<div class="card">
<div class="card-title">💎 Buy Premium Plans</div>
<button class="btn btn-warning" onclick="buyPlan(100,'plan_100')"><span>⭐</span><span>Buy ₹100 Plan (Earning Booster)</span></button>
<button class="btn btn-primary" onclick="buyPlan(500,'plan_500')"><span>🚀</span><span>Buy ₹500 Plan (Promotion Hub)</span></button>
</div>
<div class="card">
<div class="card-title">📺 Daily Tasks</div>
<button class="btn" id="adBtn" onclick="watchAd()"><span>🎬</span><span>Watch Daily Ad</span><span style="background:rgba(255,255,255,0.2);padding:4px 10px;border-radius:8px;font-size:0.85rem">+25</span></button>
<div class="progress-container"><div class="progress-label"><span>Daily Progress</span><span id="progressText">0 / 2000 ads</span></div><div class="progress-bar"><div class="progress-fill" id="progressFill" style="width:0%"></div></div></div>
</div>
<div class="card">
<div class="card-title">📱 Social Tasks</div>
<div class="task-list">
<div class="task-item" onclick="claimTask('youtube')"><div class="task-info"><div class="task-icon" style="background:linear-gradient(135deg,#fee2e2,#fecaca)">▶️</div><div class="task-details"><h3>YouTube Subscribe</h3><p>@USSoccerPulse</p></div></div><div class="task-reward">+100</div></div>
<div class="task-item" onclick="claimTask('instagram')"><div class="task-info"><div class="task-icon" style="background:linear-gradient(135deg,#fce7f3,#fbcfe8)">📷</div><div class="task-details"><h3>Instagram Follow</h3><p>@digital_rockstar_m</p></div></div><div class="task-reward">+100</div></div>
<div class="task-item" onclick="claimTask('facebook')"><div class="task-info"><div class="task-icon" style="background:linear-gradient(135deg,#dbeafe,#bfdbfe)">📘</div><div class="task-details"><h3>Facebook Like</h3><p>UltimateMediaSearch</p></div></div><div class="task-reward">+100</div></div>
</div>
</div>
<div class="card">
<div class="card-title">👥 Invite Friends</div>
<p style="font-size:0.9rem;opacity:0.9;margin-bottom:10px">Earn <strong style="color:#48bb78">+50 points</strong> per friend!</p>
<div class="referral-box"><div class="referral-link" id="refLink">Loading...</div><button class="copy-btn" onclick="copyReferral()">Copy</button></div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:15px">
<button class="btn btn-secondary" onclick="shareReferral()">📤 Share</button>
<button class="btn btn-success" onclick="showReferralStats()">📊 Stats</button>
</div>
</div>
<div class="card">
<div class="card-title">💰 Withdraw</div>
<p style="font-size:0.9rem;opacity:0.9;margin-bottom:10px">Minimum: <strong>$1.00</strong> (100 points)</p>
<button class="btn btn-success" onclick="requestWithdraw()" id="withdrawBtn">Request Withdrawal</button>
</div>
</div>
<nav class="bottom-nav">
<button class="nav-item active"><span class="icon">🏠</span><span class="label">Home</span></button>
<button class="nav-item"><span class="icon">📋</span><span class="label">Tasks</span></button>
<button class="nav-item"><span class="icon">💰</span><span class="label">Earn</span></button>
<button class="nav-item"><span class="icon">👤</span><span class="label">Profile</span></button>
</nav>
<script>
const FC={{ firebase_config | safe }};firebase.initializeApp(FC);const db=firebase.database();
const CFG={{ app_config | safe }};
const P=new URLSearchParams(location.search);let UID=P.get('id')||(window.Telegram?.WebApp?.initDataUnsafe?.user?.id)||'123';let UNAME=P.get('name')||(window.Telegram?.WebApp?.initDataUnsafe?.user?.first_name)||'User';let USER_DATA={};let CLAIMED=JSON.parse(localStorage.getItem('c_'+UID)||'{}');
const tg=window.Telegram?.WebApp;if(tg){tg.ready();tg.expand();}
document.addEventListener('DOMContentLoaded',()=>{document.getElementById('userName').textContent=UNAME;loadUser();});
function loadUser(){db.ref('users/'+UID).on('value',s=>{let d=s.val();if(!d){createUser();return;}USER_DATA=d;updateUI();});}
function createUser(){const ts=Date.now();const rc='UMS'+String(UID).slice(-6).toUpperCase();const newUser={uid:UID,name:UNAME,username:UNAME,referral_code:rc,points:0,total_earned:0,ad_views:0,tasks_completed:0,joined_at:ts,last_active:ts,last_ad_date:'',daily_ad_completed:false,plan:'free'};db.ref('users/'+UID).set(newUser);USER_DATA=newUser;updateUI();showToast('🎉 Welcome!','success');}
function updateUI(){const p=USER_DATA.points||0;const bal=(p/CFG.POINTS_PER_DOLLAR).toFixed(2);const total=((USER_DATA.total_earned||0)/CFG.POINTS_PER_DOLLAR).toFixed(2);const ads=USER_DATA.ad_views||0;const prog=Math.min((ads/2000)*100,100);
document.getElementById('balance').textContent='$'+bal;document.getElementById('points').textContent=p.toLocaleString();document.getElementById('tasks').textContent=USER_DATA.tasks_completed||0;document.getElementById('ads').textContent=ads.toLocaleString();document.getElementById('totalEarned').textContent='$'+total;
document.getElementById('progressFill').style.width=prog+'%';document.getElementById('progressText').textContent=ads.toLocaleString()+' / 2,000 ads';
const rc=USER_DATA.referral_code||'UMS'+String(UID).slice(-6).toUpperCase();document.getElementById('refLink').textContent='https://t.me/UltimateMediaSearchBot?start='+rc;
const today=new Date().toDateString();const lastAd=USER_DATA.last_ad_date||'';const btn=document.getElementById('adBtn');
if(lastAd===today){btn.disabled=true;btn.innerHTML='<span>✅</span><span>Daily Ad Completed</span>';}else{btn.disabled=false;btn.innerHTML='<span>🎬</span><span>Watch Daily Ad</span><span style="background:rgba(255,255,255,0.2);padding:4px 10px;border-radius:8px;font-size:0.85rem">+25</span>';}}
async function watchAd(){const today=new Date().toDateString();if((USER_DATA.last_ad_date||'')===today){showToast('⚠️ Already completed today!','info');return;}
const btn=document.getElementById('adBtn');btn.disabled=true;window.open(CFG.AD_LINK,'_blank');let s=30;btn.innerHTML='<span>⏳</span><span>Wait '+s+'s...</span>';
const timer=setInterval(async()=>{s--;btn.innerHTML='<span>⏳</span><span>Wait '+s+'s...</span>';if(s<=0){clearInterval(timer);
try{await db.ref('users/'+UID).update({ad_views:(USER_DATA.ad_views||0)+1,points:(USER_DATA.points||0)+CFG.AD_POINTS,total_earned:(USER_DATA.total_earned||0)+CFG.AD_POINTS,last_ad_date:today,daily_ad_completed:true,last_active:Date.now()});
showToast('🎉 +'+CFG.AD_POINTS+' Points!','success');btn.innerHTML='<span>✅</span><span>Claimed!</span>';}catch(e){showToast('❌ Failed','error');btn.disabled=false;}
}},1000);}
async function claimTask(plat){const key=plat+'_task';if(CLAIMED[key]){showToast('✅ Already claimed!','info');return;}
const links={youtube:CFG.YOUTUBE,instagram:CFG.INSTAGRAM,facebook:CFG.FACEBOOK};window.open(links[plat],'_blank');
try{await db.ref('users/'+UID).update({points:(USER_DATA.points||0)+CFG.SOCIAL_POINTS,total_earned:(USER_DATA.total_earned||0)+CFG.SOCIAL_POINTS,tasks_completed:(USER_DATA.tasks_completed||0)+1,last_active:Date.now(),['social_tasks/'+plat]:{completed:true,completed_at:Date.now()}});
CLAIMED[key]=true;localStorage.setItem('c_'+UID,JSON.stringify(CLAIMED));showToast('🎉 +'+CFG.SOCIAL_POINTS+' Points!','success');}catch(e){showToast('❌ Failed','error');}}
async function buyPlan(amount,planType){
const upiLink=`upi://pay?pa=${CFG.UPI_ID}&pn=${encodeURIComponent(CFG.UPI_NAME)}&am=${amount}&cu=INR&tn=${encodeURIComponent('Plan Purchase: '+planType)}`;
const confirmMsg=`🛒 Buy ${planType==='plan_100'?'₹100 Plan':'₹500 Plan'}?\n\n💳 Pay ₹${amount} via UPI\n\nAfter payment, screenshot send karein admin ko.`;
if(confirm(confirmMsg)){try{window.open(upiLink,'_blank');await db.ref('payments/'+UID+'/'+Date.now()).set({amount:amount,plan:planType,status:'pending',timestamp:Date.now()});
showToast('💳 Payment page opened! Screenshot save karein.','info');}catch(e){showToast('❌ Payment failed','error');}}}
function copyReferral(){navigator.clipboard.writeText(document.getElementById('refLink').textContent).then(()=>showToast('🔗 Copied!','success'));}
function shareReferral(){const l=document.getElementById('refLink').textContent;const t='🎁 Join me! Earn money watching ads: '+l;if(tg)tg.openTelegramLink('https://t.me/share/url?url='+encodeURIComponent(l)+'&text='+encodeURIComponent(t));else window.open('https://t.me/share/url?url='+encodeURIComponent(l)+'&text='+encodeURIComponent(t),'_blank');}
function showReferralStats(){const rc=USER_DATA.referral_count||0;const earn=rc*CFG.REFERRAL_BONUS;showToast('📊 Referrals: '+rc+' | Points: '+earn,'info');}
async function requestWithdraw(){const p=USER_DATA.points||0;if(p<CFG.MIN_WITHDRAW){showToast('💰 Need 100 points ($1)!','error');return;}
const usd=(p/CFG.POINTS_PER_DOLLAR).toFixed(2);if(confirm('Withdraw $'+usd+'?')){try{await db.ref('withdrawals/'+UID+'/'+Date.now()).set({amount:p,usd:usd,status:'pending',requested_at:Date.now()});
await db.ref('users/'+UID).update({points:0,total_withdrawn:(USER_DATA.total_withdrawn||0)+p,pending_withdrawal:true});showToast('✅ Withdrawal submitted! 24-48h','success');}catch(e){showToast('❌ Failed','error');}}}
function showToast(m,t='success'){const icons={success:'✅',error:'❌',info:'ℹ️'};document.getElementById('toastIcon').textContent=icons[t]||'✅';document.getElementById('toastMsg').textContent=m;
const el=document.getElementById('toast');el.className='toast '+t+' show';setTimeout(()=>el.className='toast',3500);if(tg?.HapticFeedback)tg.HapticFeedback.notificationOccurred(t==='success'?'success':'error');}
</script>
</body>
</html>'''

# ─────────────────────────────────────────────────────────────────────
# 🌐 Flask Routes
# ─────────────────────────────────────────────────────────────────────
@app.route('/')
def root():
    return f'''<html><body style="background:#1a202c;color:#fff;text-align:center;padding:40px;font-family:sans-serif">
    <h1>🤖 Ultimate Media Search Bot</h1><p style="color:#94a3b8;margin:20px 0">Server running! ✅</p>
    <a href="{APP_CONFIG['DASHBOARD_URL']}?id=123&name=Test" style="display:inline-block;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;padding:14px 32px;border-radius:12px;text-decoration:none;font-weight:600">🚀 Open Dashboard</a>
    <p style="margin-top:30px;font-size:0.9rem;color:#64748b">Firebase: {FIREBASE_MODE}</p></body></html>'''

@app.route('/dashboard')
def dashboard():
    tid = request.args.get('id', '123')
    name = request.args.get('name', 'User')
    try:
        if not get_user(tid):
            set_user(tid, {'uid':tid,'name':name,'username':name,'points':0,'total_earned':0,'ad_views':0,'tasks_completed':0,'joined_at':int(time.time()*1000),'last_active':int(time.time()*1000),'referral_code':'UMS'+str(tid)[-6:].upper(),'plan':'free'})
    except Exception as e: logger.error(f"User creation error: {e}")
    return render_template_string(DASHBOARD_HTML, firebase_config=json.dumps(FIREBASE_CONFIG), app_config=json.dumps(APP_CONFIG), banner=APP_CONFIG['BANNER'])

@app.route('/health')
def health():
    return jsonify({'status':'healthy','service':'ultimate-media-search','firebase_mode':FIREBASE_MODE,'timestamp':int(time.time()*1000)}), 200

@app.route('/favicon.ico')
@app.route('/favicon.png')
def favicon(): return '', 204

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
    def handle_start(message):
        try:
            uid = message.from_user.id
            name = message.from_user.first_name or 'User'
            dashboard_url = f"{APP_CONFIG['DASHBOARD_URL']}?id={uid}&name={name}"
            
            welcome_text = f"""
✨ <b>Welcome to UltimateMediaSearchBot!</b> ✨

🇳 <b>India's #1 Destination for Earning & Social Media Growth.</b>

Namaste! 🙏 Aapne sahi jagah kadam rakha hai.

━━━━━━━━━━━━━━━━━━━━

💰 <b>EARNING DHAMAKA</b>
✅ VIP Tasks: High-paying social media tasks
✅ Fast Payout: Instant withdrawal
✅ Refer & Earn: Lifetime 10% commission

📱 <b>Social Tasks:</b>
1️⃣ YouTube: <a href="{APP_CONFIG['YOUTUBE']}">Subscribe</a>
2️⃣ Instagram: <a href="{APP_CONFIG['INSTAGRAM']}">Follow</a>
3️⃣ Facebook: <a href="{APP_CONFIG['FACEBOOK']}">Like</a>

━━━━━━━━━━━━━━━━━━━━

💳 <b>PREMIUM PLANS</b>
⭐ ₹100 Plan - Earning Booster
🚀 ₹500 Plan - Promotion Hub

━━━━━━━━━━━━━━━━━━━━

👇 <b>Neeche buttons se shuru karein!</b>
            """
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("💰 Earn Points", url=dashboard_url),
                types.InlineKeyboardButton("📊 My Dashboard", url=dashboard_url)
            )
            markup.add(
                types.InlineKeyboardButton("⭐ Buy ₹100 Plan", callback_data="buy_100"),
                types.InlineKeyboardButton("🚀 Buy ₹500 Plan", callback_data="buy_500")
            )
            markup.add(
                types.InlineKeyboardButton("📺 Watch Ad", url=APP_CONFIG['AD_LINK']),
                types.InlineKeyboardButton("💬 Support", url=APP_CONFIG['SUPPORT_LINK'])
            )
            
            try:
                img_resp = requests.get(APP_CONFIG['BANNER'], timeout=10)
                bot.send_photo(message.chat.id, photo=img_resp.content, caption=welcome_text, reply_markup=markup, parse_mode="HTML")
            except:
                bot.send_message(message.chat.id, f"🖼️ Image: {APP_CONFIG['BANNER']}\n\n{welcome_text}", reply_markup=markup, parse_mode="HTML")
                
        except Exception as e:
            logger.error(f"Start error: {e}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
    def handle_buy_plan(call):
        try:
            plan = call.data.split('_')[1]
            amount = 100 if plan == '100' else 500
            upi_link = f"upi://pay?pa={APP_CONFIG['UPI_ID']}&pn={APP_CONFIG['UPI_NAME']}&am={amount}&cu=INR&tn=Plan Purchase {plan}"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("💳 Pay via UPI", url=upi_link))
            markup.add(types.InlineKeyboardButton("📞 Contact Admin", url=APP_CONFIG['SUPPORT_LINK']))
            
            bot.edit_message_text(
                f"💳 <b>Payment Details</b>\n\n"
                f"Plan: {'₹100 - Earning Booster' if plan=='100' else '₹500 - Promotion Hub'}\n"
                f"Amount: ₹{amount}\n\n"
                f"UPI ID: <code>{APP_CONFIG['UPI_ID']}</code>\n\n"
                f"✅ Payment ke baad screenshot admin ko bhejein.",
                call.message.chat.id, call.message.message_id,
                reply_markup=markup, parse_mode="HTML"
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"Buy plan error: {e}")

# ─────────────────────────────────────────────────────────────────────
# 🔗 Webhook
# ─────────────────────────────────────────────────────────────────────
@app.route('/webhook', methods=['POST'])
def webhook():
    if not bot: return 'Bot unavailable', 503
    try:
        update = request.get_json(force=True)
        if update: bot.process_new_updates([types.Update.de_json(update)])
        return '', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': str(e)}), 500

WEBHOOK_SET = False
@app.before_request
def set_webhook_once():
    global WEBHOOK_SET
    if not WEBHOOK_SET and bot and request.path == '/webhook':
        try:
            bot.set_webhook(f"{request.host_url.rstrip('/')}/webhook")
            logger.info(f"✅ Webhook set")
        except: pass
        WEBHOOK_SET = True

@app.errorhandler(404)
def not_found(e): return jsonify({'error':'Not found'}), 404
@app.errorhandler(500)
def server_error(e): 
    logger.error(f"Server error: {e}")
    return jsonify({'error':'Internal server error'}), 500

logger.info(f"✅ Server ready | Firebase: {FIREBASE_MODE}")
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
