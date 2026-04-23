import os
import json
import uuid
import requests
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
import telebot
from firebase_admin import credentials, initialize_app, db as firebase_db, storage as firebase_storage

# ⚠️ SECURITY: Use Environment Variables in Production!
BOT_TOKEN = os.getenv('BOT_TOKEN', '8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw')
FIREBASE_DATABASE_URL = os.getenv('FIREBASE_DATABASE_URL', 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', 'sk-783d645ce9e84eb8b954786a016561ea')
ADMIN_TELEGRAM_ID = int(os.getenv('ADMIN_TELEGRAM_ID', '123456789'))
UPI_ID = os.getenv('UPI_ID', '8543083014@ikwik')

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# Initialize Flask
app = Flask(__name__, static_folder='static', static_url_path='/static')
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML', threaded=False)

# ============ Firebase Init ============
def init_firebase():
    try:
        sa_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
        if sa_json:
            cred = credentials.Certificate(json.loads(sa_json))
        else:
            # Dev fallback - configure proper rules in production
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": "ultimatemediasearch",
                "private_key_id": "dev",
                "private_key": os.getenv('FIREBASE_PRIVATE_KEY', '-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC...\n-----END PRIVATE KEY-----\n').replace('\\n', '\n'),
                "client_email": "firebase-adminsdk@ultimatemediasearch.iam.gserviceaccount.com",
                "client_id": "dev",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk%40ultimatemediasearch.iam.gserviceaccount.com"
            })
        initialize_app(cred, {'databaseURL': FIREBASE_DATABASE_URL})
        return True
    except Exception as e:
        print(f"⚠️ Firebase init: {e}")
        return False

firebase_ready = init_firebase()

# ============ Helpers ============
def get_user(uid):
    if not firebase_ready: return {'points': 0, 'plan': 'Free', 'referrals': []}
    try:
        data = firebase_db.reference(f'users/{uid}').get()
        return data or {'points': 0, 'plan': 'Free', 'referrals': [], 'joined': datetime.now().isoformat()}
    except: return {'points': 0, 'plan': 'Free', 'referrals': []}

def update_user(uid, data):
    if not firebase_ready: return False
    try:
        firebase_db.reference(f'users/{uid}').update(data)
        return True
    except: return False

def call_deepseek(messages):
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "deepseek-chat", "messages": messages, "temperature": 0.7, "max_tokens": 1000}
    try:
        resp = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=45)
        resp.raise_for_status()
        return resp.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"❌ DeepSeek: {e}")
        return "⚠️ AI service temporarily unavailable."

def verify_admin(req):
    return req.headers.get('X-Telegram-User-Id') and int(req.headers.get('X-Telegram-User-Id')) == ADMIN_TELEGRAM_ID

def get_task_links():
    default = {
        'youtube': 'https://www.youtube.com/@USSoccerPulse',
        'instagram': 'https://www.instagram.com/digital_rockstar_m',
        'facebook': 'https://www.facebook.com/UltimateMediaSearch'
    }
    if not firebase_ready: return default
    try:
        data = firebase_db.reference('config/tasks').get()
        return {**default, **(data or {})}
    except: return default

# ============ Telegram Handlers ============
@bot.message_handler(commands=['start'])
def cmd_start(msg):
    uid = msg.from_user.id
    name = msg.from_user.first_name or "Friend"
    ref_code = msg.text.split()[-1] if len(msg.text.split()) > 1 else None
    
    # Handle referral
    if ref_code and ref_code.isdigit() and int(ref_code) != uid:
        referrer_data = get_user(ref_code)
        current_data = get_user(uid)
        if not current_data.get('referred_by') and uid not in referrer_data.get('referrals', []):
            # Award referral bonus
            update_user(ref_code, {
                'points': (referrer_data.get('points', 0) + 50),
                'referrals': list(set(referrer_data.get('referrals', []) + [uid]))
            })
            update_user(uid, {'referred_by': ref_code, 'points': current_data.get('points', 0) + 25})
            bot.send_message(ref_code, f"🎉 New referral: @{msg.from_user.username or uid}! +50 pts bonus!")
    
    data = get_user(uid)
    plan_display = {'Free':'Free','Earner_Pro':'🥇 Earner Pro','Influencer_Pro':'🌟 Influencer Pro'}.get(data.get('plan','Free'),'Free')
    
    photo = "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg"
    caption = (f"👋 <b>Welcome, {name}!</b>\n\n"
               f"📊 <b>Your Account</b>\n"
               f"├─ 💰 Points: <code>{data.get('points',0)}</code>\n"
               f"├─ 🎫 Plan: <code>{plan_display}</code>\n"
               f"├─ 👥 Referrals: <code>{len(data.get('referrals',[]))}</code>\n"
               f"└─ 🔗 Your Ref Link: <code>https://t.me/{bot.get_me().username}?start={uid}</code>\n\n"
               f"🚀 Use /ai [question] or visit dashboard!")
    
    kb = telebot.types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        telebot.types.InlineKeyboardButton('🚀 Dashboard', url=f'https://{os.getenv("VERCEL_URL", "localhost:5000")}/?uid={uid}'),
        telebot.types.InlineKeyboardButton('💎 Upgrade', callback_data='upgrade')
    )
    kb.add(telebot.types.InlineKeyboardButton('🤖 AI Chat', callback_data='ai_chat'))
    kb.add(telebot.types.InlineKeyboardButton('👥 Invite Friends', callback_data='refer'))
    
    bot.send_photo(msg.chat.id, photo, caption=caption, reply_markup=kb)

@bot.message_handler(commands=['ai'])
def cmd_ai(msg):
    uid = msg.from_user.id
    plan = get_user(uid).get('plan', 'Free')
    question = msg.text.replace('/ai', '', 1).strip()
    
    if not question:
        bot.reply_to(msg, "❓ Usage: <code>/ai Your question</code>\n💡 Free: 10 pts/query", parse_mode='HTML')
        return
    
    if plan == 'Free':
        current = get_user(uid).get('points', 0)
        if current < 10:
            bot.reply_to(msg, "❌ <b>Insufficient Points!</b>\nNeed: 10 | Have: {}\n💎 Upgrade for unlimited!".format(current), parse_mode='HTML')
            return
        update_user(uid, {'points': current - 10})
        bot.reply_to(msg, "🤖 <em>Thinking... (-10 pts)</em>", parse_mode='HTML')
    
    messages = [
        {"role": "system", "content": "You are EarnBot AI, a helpful Telegram assistant. Be concise."},
        {"role": "user", "content": question}
    ]
    reply = call_deepseek(messages)
    bot.reply_to(msg, f"🤖 <b>AI Response:</b>\n\n{reply[:4000]}", parse_mode='HTML')

@bot.message_handler(commands=['refer'])
def cmd_refer(msg):
    uid = msg.from_user.id
    ref_link = f"https://t.me/{bot.get_me().username}?start={uid}"
    bot.reply_to(msg, 
        f"👥 <b>Referral Program</b>\n\n"
        f"🔗 Your Link:\n<code>{ref_link}</code>\n\n"
        f"🎁 Rewards:\n"
        f"• +25 pts when someone joins via your link\n"
        f"• +50 pts when they complete first task\n\n"
        f"📊 Your Stats:\n"
        f"• Total Referrals: <code>{len(get_user(uid).get('referrals', []))}</code>\n"
        f"• Earned from referrals: <code>{len(get_user(uid).get('referrals', [])) * 50}</code> pts",
        parse_mode='HTML')

@bot.callback_query_handler(func=lambda c: True)
def handle_callback(call):
    uid = call.from_user.id
    data = get_user(uid)
    try:
        if call.data == 'dashboard':
            bot.answer_callback_query(call.id)
            dashboard_url = f'https://{os.getenv("VERCEL_URL", "localhost:5000")}/?uid={uid}'
            kb = telebot.types.InlineKeyboardMarkup()
            kb.add(telebot.types.InlineKeyboardButton('🚀 Open Dashboard', url=dashboard_url))
            bot.edit_message_text("📊 <b>Dashboard</b>\n\nClick below to open your web dashboard:", 
                chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML', reply_markup=kb)
        
        elif call.data == 'upgrade':
            bot.answer_callback_query(call.id)
            kb = telebot.types.InlineKeyboardMarkup()
            kb.add(
                telebot.types.InlineKeyboardButton('🥇 Earner Pro - ₹100', callback_data='buy_earner'),
                telebot.types.InlineKeyboardButton('🌟 Influencer Pro - ₹500', callback_data='buy_influencer')
            )
            kb.add(telebot.types.InlineKeyboardButton('💳 UPI: '+UPI_ID, callback_data='upi_info'))
            bot.edit_message_text(
                f"💎 <b>Upgrade Plans</b>\n\n"
                f"🥇 <b>Earner Pro (₹100)</b>\n• 2x points on tasks\n• 500 bonus pts\n\n"
                f"🌟 <b>Influencer Pro (₹500)</b>\n• Unlimited AI\n• 5x points\n• Promote feature\n\n"
                f"📱 Pay via UPI: <code>{UPI_ID}</code>\nThen submit TXN ID in dashboard:",
                chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML', reply_markup=kb)
        
        elif call.data == 'ai_chat':
            bot.answer_callback_query(call.id)
            bot.edit_message_text(
                "🤖 <b>AI Chat</b>\n\nUse <code>/ai [question]</code> to start.\nFree: 10 pts/msg | Pro: Unlimited",
                chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML')
        
        elif call.data == 'refer':
            bot.answer_callback_query(call.id)
            ref_link = f"https://t.me/{bot.get_me().username}?start={uid}"
            kb = telebot.types.InlineKeyboardMarkup()
            kb.add(telebot.types.InlineKeyboardButton('🔗 Copy Link', url=f'https://t.me/share/url?url={ref_link}&text=Join%20EarnBot%20&earn%20rewards!'))
            bot.edit_message_text(
                f"👥 <b>Invite & Earn</b>\n\n"
                f"🔗 Your Referral Link:\n<code>{ref_link}</code>\n\n"
                f"🎁 Rewards:\n• +25 pts per signup\n• +50 pts when they complete first task\n\n"
                f"📊 Your referrals: <code>{len(data.get('referrals', []))}</code>",
                chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML', reply_markup=kb)
        
        elif call.data.startswith('buy_'):
            plan = "Earner_Pro" if "earner" in call.data else "Influencer_Pro"
            price = "₹100" if "earner" in call.data else "₹500"
            bot.answer_callback_query(call.id)
            bot.edit_message_text(
                f"💳 <b>{plan.replace('_',' ').title()} - {price}</b>\n\n"
                f"1. Pay <code>{price}</code> to UPI: <code>{UPI_ID}</code>\n"
                f"2. Copy Transaction ID\n"
                f"3. Open dashboard → Upgrade → Submit TXN\n"
                f"4. Admin verifies in ~24h ✅",
                chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML')
        
        elif call.data == 'upi_info':
            bot.answer_callback_query(call.id, f"UPI: {UPI_ID}", show_alert=True)
            
    except Exception as e:
        print(f"❌ Callback error: {e}")
        bot.answer_callback_query(call.id, "⚠️ Error. Try /start again.")

# ============ API Endpoints ============
@app.route('/api/chat', methods=['POST'])
def api_chat():
    try:
        data = request.get_json(force=True)
        uid = data.get('user_id')
        message = data.get('message', '').strip()
        if not uid or not message: return jsonify({'error': 'Missing params'}), 400
        
        user = get_user(uid)
        # Deduct points for Free users
        if user.get('plan') == 'Free':
            if user.get('points', 0) < 10: return jsonify({'error': 'Insufficient points'}), 402
            update_user(uid, {'points': user['points'] - 10})
        
        messages = [
            {"role": "system", "content": "You are EarnBot AI. Be helpful and concise."},
            {"role": "user", "content": message}
        ]
        reply = call_deepseek(messages)
        return jsonify({'reply': reply}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upgrade/submit', methods=['POST'])
def submit_upgrade():
    try:
        data = request.get_json(force=True)
        uid, plan, txn = data.get('user_id'), data.get('plan'), data.get('transaction_id', '').strip()
        if not all([uid, plan, txn]): return jsonify({'error': 'Missing fields'}), 400
        
        firebase_db.reference(f'upgrades/pending/{uuid.uuid4().hex}').set({
            'user_id': uid, 'plan': plan, 'transaction_id': txn,
            'screenshot_url': data.get('screenshot_url', ''),
            'amount': 100 if plan == 'Earner_Pro' else 500,
            'status': 'pending', 'submitted_at': datetime.now().isoformat()
        })
        # Notify admin
        try:
            bot.send_message(ADMIN_TELEGRAM_ID, f"🔔 New Upgrade: User {uid} | {plan} | TXN: {txn}", parse_mode='HTML')
        except: pass
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks', methods=['GET'])
def api_tasks():
    return jsonify({'tasks': get_task_links()}), 200

@app.route('/api/user/<uid>', methods=['GET'])
def api_user(uid):
    return jsonify(get_user(uid)), 200

# ============ Admin Endpoints ============
@app.route('/admin/api/users', methods=['GET'])
def admin_users():
    if not verify_admin(request): return jsonify({'error': 'Unauthorized'}), 401
    try:
        users = firebase_db.reference('users').get() or {}
        return jsonify({'users': [{**{'id':k}, **v} for k,v in users.items() if isinstance(v, dict)]}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/admin/api/upgrades', methods=['GET', 'POST'])
def admin_upgrades():
    if not verify_admin(request): return jsonify({'error': 'Unauthorized'}), 401
    if request.method == 'GET':
        try:
            pending = firebase_db.reference('upgrades/pending').get() or {}
            return jsonify({'upgrades': [{**{'id':k}, **v} for k,v in pending.items() if isinstance(v, dict) and v.get('status')=='pending']}), 200
        except Exception as e: return jsonify({'error': str(e)}), 500
    else:
        try:
            data = request.get_json(force=True)
            uid, action = data.get('upgrade_id'), data.get('action')
            ref = firebase_db.reference(f'upgrades/pending/{uid}')
            upgrade = ref.get()
            if not upgrade: return jsonify({'error': 'Not found'}), 404
            if action == 'approve':
                user_ref = firebase_db.reference(f'users/{upgrade["user_id"]}')
                current = user_ref.get() or {}
                bonus = 500 if upgrade['plan'] == 'Earner_Pro' else 2500
                user_ref.update({'plan': upgrade['plan'], 'points': (current.get('points',0)+bonus), 'upgraded_at': datetime.now().isoformat()})
                try: bot.send_message(int(upgrade['user_id']), f"🎉 Upgrade Approved! You're now {upgrade['plan'].replace('_',' ').title()}! +{bonus} pts bonus.", parse_mode='HTML')
                except: pass
            firebase_db.reference(f'upgrades/history/{uid}').set({**upgrade, 'status': action, 'processed_at': datetime.now().isoformat()})
            ref.delete()
            return jsonify({'success': True}), 200
        except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/admin/api/points', methods=['POST'])
def admin_points():
    if not verify_admin(request): return jsonify({'error': 'Unauthorized'}), 401
    try:
        data = request.get_json(force=True)
        uid, amount, reason = data.get('user_id'), int(data.get('amount',0)), data.get('reason','Admin adjustment')
        ref = firebase_db.reference(f'users/{uid}/points')
        current = ref.get() or 0
        ref.set(current + amount)
        firebase_db.reference('logs/adjustments').push({'user_id':uid, 'by':ADMIN_TELEGRAM_ID, 'amount':amount, 'reason':reason, 'ts':datetime.now().isoformat()})
        return jsonify({'success': True, 'new_points': current+amount}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/admin/api/tasks', methods=['GET', 'POST'])
def admin_tasks():
    if not verify_admin(request): return jsonify({'error': 'Unauthorized'}), 401
    if request.method == 'GET':
        return jsonify({'tasks': get_task_links()}), 200
    else:
        try:
            updates = {k:v for k,v in request.get_json(force=True).items() if k in ['youtube','instagram','facebook'] and v.startswith('https://')}
            if not updates: return jsonify({'error': 'No valid updates'}), 400
            firebase_db.reference('config/tasks').update(updates)
            return jsonify({'success': True, 'updated': updates}), 200
        except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/admin/api/broadcast', methods=['POST'])
def admin_broadcast():
    if not verify_admin(request): return jsonify({'error': 'Unauthorized'}), 401
    try:
        data = request.get_json(force=True)
        message, target = data.get('message','').strip(), data.get('target_plan')
        if not message: return jsonify({'error': 'Message required'}), 400
        users = firebase_db.reference('users').get() or {}
        sent = failed = 0
        for uid, udata in users.items():
            if not uid.isdigit(): continue
            if target and udata.get('plan') != target: continue
            try:
                bot.send_message(int(uid), f"📢 <b>Update</b>:\n\n{message}", parse_mode='HTML')
                sent += 1
            except: failed += 1
        firebase_db.reference('notifications').push({'title':'📢 Admin Update','message':message,'timestamp':datetime.now().isoformat(),'target':target or 'all'})
        return jsonify({'success': True, 'sent': sent, 'failed': failed}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500

# ============ Webhook & Static ============
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.content_type != 'application/json': return jsonify({'error': 'Invalid'}), 400
    try:
        update = telebot.types.Update.de_json(request.get_json(force=True))
        bot.process_new_updates([update])
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin', methods=['GET'])
@app.route('/admin.html', methods=['GET'])
def serve_admin():
    return send_from_directory('static', 'admin.html')

@app.route('/', methods=['GET'])
@app.route('/index.html', methods=['GET'])
@app.route('/dashboard', methods=['GET'])
def serve_dashboard():
    return send_from_directory('static', 'index.html')

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status':'healthy','firebase':firebase_ready}), 200

# ============ Vercel Handler ============
def handler(req, ctx=None):
    return app(req.environ, lambda s, h, exc=None: None)

# Set webhook after deploy:
# https://api.telegram.org/bot<TOKEN>/setWebhook?url=<YOUR_VERCEL_URL>/webhook

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))
