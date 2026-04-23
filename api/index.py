import os
import json
import uuid
import logging
import requests
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, make_response
from dotenv import load_dotenv
import telebot

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ Config ============
BOT_TOKEN = os.getenv('BOT_TOKEN', '8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw')
FIREBASE_DB_URL = os.getenv('FIREBASE_DATABASE_URL', 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/')
DEEPSEEK_KEY = os.getenv('DEEPSEEK_API_KEY', 'sk-783d645ce9e84eb8b954786a016561ea')
ADMIN_ID = int(os.getenv('ADMIN_TELEGRAM_ID', '123456789'))
UPI_ID = os.getenv('UPI_ID', '8543083014@ikwik')

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

# ============ Flask & Bot Init ============
app = Flask(__name__, static_folder='../static', static_url_path='/static')
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML', threaded=False)

# ============ Firebase Init ============
firebase_ready = False
db = None
try:
    from firebase_admin import credentials, initialize_app, db as fb_db
    sa = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
    if sa:
        cred = credentials.Certificate(json.loads(sa))
    else:
        cred = credentials.Certificate({
            "type": "service_account", "project_id": "ultimatemediasearch",
            "private_key_id": "dev",
            "private_key": os.getenv('FIREBASE_PRIVATE_KEY', '-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...\n-----END PRIVATE KEY-----\n').replace('\\n', '\n'),
            "client_email": "firebase-adminsdk@ultimatemediasearch.iam.gserviceaccount.com",
            "client_id": "dev",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk%40ultimatemediasearch.iam.gserviceaccount.com"
        })
    initialize_app(cred, {'databaseURL': FIREBASE_DB_URL})
    db = fb_db
    firebase_ready = True
    logger.info("✅ Firebase initialized")
except Exception as e:
    logger.warning(f"⚠️ Firebase fallback mode: {e}")

# ============ Helpers ============
def get_user(uid):
    if not firebase_ready: return {'points':0,'plan':'Free','referrals':[],'joined':datetime.now().isoformat()}
    try: return db.reference(f'users/{uid}').get() or {'points':0,'plan':'Free','referrals':[],'joined':datetime.now().isoformat()}
    except: return {'points':0,'plan':'Free','referrals':[]}

def update_user(uid, data):
    if not firebase_ready: return False
    try: db.reference(f'users/{uid}').update(data); return True
    except: return False

def call_ai(msg):
    try:
        r = requests.post(DEEPSEEK_URL, json={"model":"deepseek-chat","messages":[{"role":"user","content":msg}],"temperature":0.7}, headers={"Authorization":f"Bearer {DEEPSEEK_KEY}"}, timeout=45)
        return r.json()['choices'][0]['message']['content'].strip()
    except: return "⚠️ AI service unavailable."

def is_admin(req): return req.headers.get('X-Telegram-User-Id') and int(req.headers.get('X-Telegram-User-Id')) == ADMIN_ID
def get_tasks():
    default = {'youtube':'https://www.youtube.com/@USSoccerPulse','instagram':'https://www.instagram.com/digital_rockstar_m','facebook':'https://www.facebook.com/UltimateMediaSearch'}
    if not firebase_ready: return default
    try: return {**default, **(db.reference('config/tasks').get() or {})}
    except: return default

# ============ Bot Handlers ============
@bot.message_handler(commands=['start'])
def start(msg):
    uid = msg.from_user.id
    name = msg.from_user.first_name or "Friend"
    ref = msg.text.split()[-1] if len(msg.text.split())>1 else None
    if ref and ref.isdigit() and int(ref)!=uid:
        ref_data, user_data = get_user(ref), get_user(uid)
        if not user_data.get('referred_by') and uid not in ref_data.get('referrals',[]):
            update_user(ref, {'points':ref_data.get('points',0)+50,'referrals':list(set(ref_data.get('referrals',[])+[str(uid)]))})
            update_user(uid, {'referred_by':str(ref),'points':user_data.get('points',0)+25})
            try: bot.send_message(ref, f"🎉 New referral! @{msg.from_user.username or uid} joined. +50 pts bonus!", parse_mode='HTML')
            except: pass
    
    d = get_user(uid)
    plan_map = {'Free':'Free','Earner_Pro':'🥇 Earner Pro','Influencer_Pro':'🌟 Influencer Pro'}
    kb = telebot.types.InlineKeyboardMarkup(row_width=2)
    kb.add(telebot.types.InlineKeyboardButton('🚀 Dashboard', url=f"https://{os.getenv('VERCEL_URL','localhost:5000')}/dashboard?uid={uid}"),
           telebot.types.InlineKeyboardButton('💎 Upgrade', callback_data='upgrade'))
    kb.add(telebot.types.InlineKeyboardButton('🤖 AI Chat', callback_data='ai_chat'),
           telebot.types.InlineKeyboardButton('👥 Refer & Earn', callback_data='refer'))
    bot.send_photo(msg.chat.id, "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg",
                   f"👋 <b>Welcome, {name}!</b>\n\n💰 Points: <code>{d.get('points',0)}</code>\n🎫 Plan: <code>{plan_map.get(d.get('plan','Free'),'Free')}</code>\n👥 Refs: <code>{len(d.get('referrals',[]))}</code>\n🔗 Link: <code>https://t.me/{bot.get_me().username}?start={uid}</code>", reply_markup=kb)

@bot.message_handler(commands=['ai'])
def ai_cmd(msg):
    uid, plan = msg.from_user.id, get_user(msg.from_user.id).get('plan','Free')
    q = msg.text.replace('/ai','',1).strip()
    if not q: return bot.reply_to(msg, "❓ Usage: <code>/ai Your question</code>\n💡 Free: 10 pts/query", parse_mode='HTML')
    if plan=='Free':
        pts = get_user(uid).get('points',0)
        if pts<10: return bot.reply_to(msg, f"❌ Need 10 pts | Have: {pts}\n💎 Upgrade for unlimited!", parse_mode='HTML')
        update_user(uid, {'points':pts-10})
    bot.reply_to(msg, f"🤖 <em>Thinking...</em>", parse_mode='HTML')
    bot.reply_to(msg, f"🤖 <b>AI:</b>\n\n{call_ai(q)[:4000]}", parse_mode='HTML')

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    bot.answer_callback_query(c.id)
    uid = c.from_user.id
    if c.data=='upgrade':
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton('🥇 Earner Pro - ₹100', callback_data='buy_earner'))
        kb.add(telebot.types.InlineKeyboardButton('🌟 Influencer Pro - ₹500', callback_data='buy_influencer'))
        kb.add(telebot.types.InlineKeyboardButton('💳 UPI Info', callback_data='upi'))
        bot.edit_message_text(f"💎 <b>Plans</b>\n🥇 Earner: 2x pts + 500 bonus\n🌟 Influencer: 5x pts + Unlimited AI\n📱 UPI: <code>{UPI_ID}</code>", c.message.chat.id, c.message.message_id, parse_mode='HTML', reply_markup=kb)
    elif c.data.startswith('buy_'):
        p = "Earner Pro" if "earner" in c.data else "Influencer Pro"
        pr = "₹100" if "earner" in c.data else "₹500"
        bot.edit_message_text(f"💳 <b>{p} - {pr}</b>\n1️⃣ Pay {pr} to <code>{UPI_ID}</code>\n2️⃣ Copy TXN ID\n3️⃣ Dashboard → Upgrade → Submit", c.message.chat.id, c.message.message_id, parse_mode='HTML')
    elif c.data=='upi': bot.answer_callback_query(c.id, f"UPI: {UPI_ID}", show_alert=True)
    elif c.data=='refer':
        bot.edit_message_text(f"👥 <b>Refer & Earn</b>\n🔗 <code>https://t.me/{bot.get_me().username}?start={uid}</code>\n🎁 +25 pts/signup | +50 pts/first task\n📊 Your referrals: <code>{len(get_user(uid).get('referrals',[]))}</code>", c.message.chat.id, c.message.message_id, parse_mode='HTML')
    elif c.data=='ai_chat': bot.edit_message_text("🤖 <b>AI Chat</b>\nUse <code>/ai [question]</code>\nFree: 10 pts | Pro: Unlimited", c.message.chat.id, c.message.message_id, parse_mode='HTML')

# ============ Routes (Matches vercel.json) ============
@app.route('/')
@app.route('/dashboard')
@app.route('/welcome')
def serve_dashboard(): return send_from_directory('../static', 'index.html')

@app.route('/admin')
def serve_admin(): return send_from_directory('../static', 'admin.html')

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.content_type != 'application/json': return jsonify({'error':'Invalid'}), 400
    try: bot.process_new_updates([telebot.types.Update.de_json(request.get_json())]); return jsonify({'status':'ok'}), 200
    except Exception as e: return jsonify({'error':str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def api_chat():
    d = request.get_json(force=True, silent=True) or {}
    uid, msg = d.get('user_id'), d.get('message','').strip()
    if not uid or not msg: return jsonify({'error':'Missing fields'}), 400
    u = get_user(uid)
    if u.get('plan')=='Free' and u.get('points',0)<10: return jsonify({'error':'Insufficient points'}), 402
    if u.get('plan')=='Free': update_user(uid, {'points':u['points']-10})
    return jsonify({'reply':call_ai(msg), 'pts_used':10 if u.get('plan')=='Free' else 0}), 200

@app.route('/api/upgrade/submit', methods=['POST'])
def submit_upgrade():
    d = request.get_json(force=True, silent=True) or {}
    uid, plan, txn = d.get('user_id'), d.get('plan'), d.get('transaction_id','').strip()
    if not all([uid,plan,txn]): return jsonify({'error':'Missing fields'}), 400
    if firebase_ready:
        db.reference(f'upgrades/pending/{uuid.uuid4().hex}').set({'user_id':uid,'plan':plan,'transaction_id':txn,'amount':100 if plan=='Earner_Pro' else 500,'status':'pending','submitted_at':datetime.now().isoformat()})
    try: bot.send_message(ADMIN_ID, f"🔔 New Upgrade: @{uid} | {plan} | TXN: {txn}", parse_mode='HTML')
    except: pass
    return jsonify({'success':True, 'message':'Submitted! Admin will verify in 24h.'}), 200

@app.route('/api/tasks', methods=['GET'])
def api_tasks(): return jsonify({'tasks':get_tasks()}), 200

@app.route('/api/user/<uid>', methods=['GET'])
def api_user(uid): return jsonify(get_user(uid)), 200

# ============ Admin API ============
@app.route('/admin/api/users', methods=['GET'])
def adm_users():
    if not is_admin(request): return jsonify({'error':'Unauthorized'}), 401
    try:
        u = db.reference('users').get() if firebase_ready else {}
        return jsonify({'users':[{'id':k, **v} for k,v in (u or {}).items() if isinstance(v, dict)]}), 200
    except Exception as e: return jsonify({'error':str(e)}), 500

@app.route('/admin/api/upgrades', methods=['GET','POST'])
def adm_upgrades():
    if not is_admin(request): return jsonify({'error':'Unauthorized'}), 401
    if request.method=='GET':
        try: p = db.reference('upgrades/pending').get() if firebase_ready else {}
        return jsonify({'upgrades':[{'id':k, **v} for k,v in (p or {}).items() if isinstance(v,dict) and v.get('status')=='pending']}), 200
    else:
        d = request.get_json(force=True) or {}
        uid, act = d.get('upgrade_id'), d.get('action')
        if not uid or act not in ['approve','reject']: return jsonify({'error':'Invalid'}), 400
        ref = db.reference(f'upgrades/pending/{uid}')
        u = ref.get()
        if not u: return jsonify({'error':'Not found'}), 404
        if act=='approve':
            cur = db.reference(f'users/{u["user_id"]}').get() or {}
            bonus = 500 if u['plan']=='Earner_Pro' else 2500
            db.reference(f'users/{u["user_id"]}').update({'plan':u['plan'],'points':cur.get('points',0)+bonus})
            try: bot.send_message(int(u['user_id']), f"🎉 Approved! You're now {u['plan'].replace('_',' ').title()}! +{bonus} pts", parse_mode='HTML')
            except: pass
        db.reference(f'upgrades/history/{uid}').set({**u, 'status':act, 'processed_at':datetime.now().isoformat()})
        ref.delete()
        return jsonify({'success':True}), 200

@app.route('/admin/api/points', methods=['POST'])
def adm_points():
    if not is_admin(request): return jsonify({'error':'Unauthorized'}), 401
    d = request.get_json(force=True) or {}
    uid, amt, reason = d.get('user_id'), int(d.get('amount',0)), d.get('reason','Admin')
    if not uid or amt==0: return jsonify({'error':'Invalid'}), 400
    ref = db.reference(f'users/{uid}/points')
    cur = ref.get() or 0
    ref.set(cur+amt)
    return jsonify({'success':True, 'new_points':cur+amt}), 200

@app.route('/admin/api/tasks', methods=['GET','POST'])
def adm_tasks():
    if not is_admin(request): return jsonify({'error':'Unauthorized'}), 401
    if request.method=='GET': return jsonify({'tasks':get_tasks()}), 200
    d = request.get_json(force=True) or {}
    upd = {k:v for k,v in d.items() if k in ['youtube','instagram','facebook'] and str(v).startswith('https://')}
    if not upd: return jsonify({'error':'Invalid URLs'}), 400
    db.reference('config/tasks').update(upd)
    return jsonify({'success':True}), 200

@app.route('/admin/api/broadcast', methods=['POST'])
def adm_broadcast():
    if not is_admin(request): return jsonify({'error':'Unauthorized'}), 401
    d = request.get_json(force=True) or {}
    msg, target = d.get('message','').strip(), d.get('target_plan')
    if not msg: return jsonify({'error':'Message required'}), 400
    users = db.reference('users').get() if firebase_ready else {}
    sent = failed = 0
    for uid, udata in (users or {}).items():
        if not uid.isdigit(): continue
        if target and udata.get('plan')!=target: continue
        try: bot.send_message(int(uid), f"📢 <b>Update</b>:\n\n{msg}", parse_mode='HTML'); sent+=1
        except: failed+=1
    if firebase_ready: db.reference('notifications').push({'title':'📢 Admin','message':msg,'timestamp':datetime.now().isoformat()})
    return jsonify({'success':True, 'sent':sent, 'failed':failed}), 200

# ============ Health & Vercel ============
@app.route('/api/health', methods=['GET'])
def health(): return jsonify({'status':'ok','firebase':firebase_ready}), 200

def handler(req, ctx=None): return app(req.environ, lambda s,h,e=None:None)

if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.getenv('PORT',8080)))
