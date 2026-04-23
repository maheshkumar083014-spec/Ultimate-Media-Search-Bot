"""
Ultimate Media Search Bot - FIXED VERSION
"""

import os
import json
import time
import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============= SECURE CONFIGURATION =============
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
FIREBASE_DATABASE_URL = os.environ.get("FIREBASE_DATABASE_URL", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

# Firebase Config for Frontend
FIREBASE_CONFIG = {
    "apiKey": os.environ.get("FIREBASE_API_KEY", "AIzaSyD50eWvysruXgtgpDhhCVE2zdbSbLkFBwk"),
    "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN", "ultimatemediasearch.firebaseapp.com"),
    "projectId": os.environ.get("FIREBASE_PROJECT_ID", "ultimatemediasearch"),
    "storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET", "ultimatemediasearch.firebasestorage.app"),
    "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID", "123003124713"),
    "appId": os.environ.get("FIREBASE_APP_ID", "1:123003124713:web:c738c97b2772b112822978")
}

# ============= APP INITIALIZATION =============
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE"]}})

# Try to initialize Firebase (optional - app works without it)
firebase_app = None
try:
    import firebase_admin
    from firebase_admin import db
    if not firebase_admin._apps:
        firebase_app = firebase_admin.initialize_app(
            options={'databaseURL': FIREBASE_DATABASE_URL},
            name='[DEFAULT]'
        )
        logger.info("✅ Firebase initialized")
except Exception as e:
    logger.warning(f"⚠️ Firebase not initialized: {e}")

# ============= CONSTANTS =============
SOCIAL_TASKS = {
    "youtube": {"name": "YouTube", "handle": "@USSoccerPulse", "points": 100, "url": "https://youtube.com/@USSoccerPulse"},
    "instagram": {"name": "Instagram", "handle": "@digital_rockstar_m", "points": 100, "url": "https://instagram.com/digital_rockstar_m"},
    "facebook": {"name": "Facebook", "handle": "UltimateMediaSearch", "points": 100, "url": "https://facebook.com/UltimateMediaSearch"}
}

PLANS = {
    "Free": {"price": 0, "ai_cost": 10},
    "Earner Pro": {"price": 100, "ai_cost": 0},
    "Influencer Pro": {"price": 500, "ai_cost": 0}
}

# ============= FIREBASE HELPERS (Safe Fallbacks) =============
def get_user(user_id):
    """Get user from Firebase or return default"""
    try:
        if firebase_app:
            ref = db.reference(f'users/{user_id}')
            data = ref.get()
            if 
                return _default_user(user_id)
            return data
    except:
        pass
    return _default_user(user_id)

def _default_user(user_id):
    return {
        'user_id': user_id,
        'username': 'User',
        'points': 0,
        'plan': 'Free',
        'tasks_completed': [],
        'messages': [],
        'joined_at': time.time()
    }

def update_user(user_id,  ref = db.reference(f'users/{user_id}')
        ref.update(data)
        return True
    except:
        return False

# ============= FLASK ROUTES =============

@app.route('/')
def index():
    """Serve main dashboard"""
    try:
        return render_template('dashboard.html', firebase_config=json.dumps(FIREBASE_CONFIG))
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return f"<h1>Dashboard Error</h1><p>{str(e)}</p>", 500

@app.route('/admin')
def admin_panel():
    """Serve admin panel"""
    try:
        return render_template('admin.html', firebase_config=json.dumps(FIREBASE_CONFIG))
    except Exception as e:
        logger.error(f"Admin panel error: {e}")
        return f"<h1>Admin Panel Error</h1><p>{str(e)}</p>", 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'version': '2.0.0',
        'firebase': 'connected' if firebase_app else 'not configured'
    })

@app.route('/api/auth/admin', methods=['POST'])
def admin_auth():
    """Admin authentication"""
    try:
        data = request.json or {}
        password = data.get('password', '')
        
        if password == ADMIN_PASSWORD and ADMIN_PASSWORD != 'admin123':
            return jsonify({
                'success': True,
                'token': f"admin_{int(time.time())}",
                'expires': time.time() + 3600
            })
        return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
    except Exception as e:
        logger.error(f"Auth error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/<user_id>', methods=['GET'])
def api_get_user(user_id):
    """Get user data"""
    try:
        user_data = get_user(user_id)
        completed = len(user_data.get('tasks_completed', []))
        daily_limit = 3 if user_data['plan'] == 'Free' else 10
        
        return jsonify({
            **user_data,
            'ad_progress': min(100, int((completed / daily_limit) * 100)),
            'tasks_available': SOCIAL_TASKS,
            'plans': PLANS
        })
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/chat', methods=['POST'])
async def api_ai_chat():
    """AI chat endpoint"""
    try:
        import requests
        data = request.json or {}
        user_id = data.get('user_id')
        message = data.get('message', '').strip()
        
        if not user_id or not message:
            return jsonify({'error': 'Missing user_id or message'}), 400
        
        user_data = get_user(user_id)
        ai_cost = PLANS.get(user_data['plan'], PLANS['Free'])['ai_cost']
        
        # Check points
        if user_data['plan'] == 'Free' and user_data['points'] < ai_cost:
            return jsonify({
                'success': False,
                'response': f"❌ Insufficient points. Need {ai_cost}, have {user_data['points']}",
                'cost': ai_cost
            })
        
        # Deduct points for free users
        if user_data['plan'] == 'Free':
            update_user(user_id, {'points': user_data['points'] - ai_cost})
        
        # Call DeepSeek API
        if not DEEPSEEK_API_KEY:
            return jsonify({
                'success': False,
                'response': "⚠️ AI not configured. Add DEEPSEEK_API_KEY in environment variables."
            })
        
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": message}],
            "max_tokens": 500
        }
        
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            # Save to history
            history = user_data.get('messages', [])[-19:]
            history.extend([
                {'role': 'user', 'content': message},
                {'role': 'assistant', 'content': ai_response}
            ])
            update_user(user_id, {'messages': history})
            
            return jsonify({
                'success': True,
                'response': ai_response,
                'cost': ai_cost if user_data['plan'] == 'Free' else 0,
                'balance': user_data['points'] - ai_cost if user_data['plan'] == 'Free' else user_data['points']
            })
        else:
            return jsonify({
                'success': False,
                'response': f"❌ AI Error: {response.status_code}"
            })
            
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/complete', methods=['POST'])
def api_complete_task():
    """Complete task"""
    try:
        data = request.json or {}
        user_id = data.get('user_id')
        task_id = data.get('task_id')
        
        if not user_id or not task_id:
            return jsonify({'error': 'Missing data'}), 400
        
        if task_id not in SOCIAL_TASKS:
            return jsonify({'error': 'Invalid task'}), 400
        
        user_data = get_user(user_id)
        
        if task_id in user_data.get('tasks_completed', []):
            return jsonify({'success': True, 'message': 'Already completed', 'points': user_data['points']})
        
        # Award points
        task = SOCIAL_TASKS[task_id]
        new_points = user_data['points'] + task['points']
        user_data.setdefault('tasks_completed', []).append(task_id)
        
        update_user(user_id, {
            'points': new_points,
            'tasks_completed': user_data['tasks_completed']
        })
        
        return jsonify({
            'success': True,
            'points_earned': task['points'],
            'new_balance': new_points
        })
    except Exception as e:
        logger.error(f"Task complete error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/payment/submit', methods=['POST'])
def api_submit_payment():
    """Submit payment"""
    try:
        data = request.json or {}
        user_id = data.get('user_id')
        txn_id = data.get('txn_id', '').strip()
        
        if not user_id or not txn_id:
            return jsonify({'error': 'Missing data'}), 400
        
        # Save to Firebase
        try:
            if firebase_app:
                ref = db.reference('payments').push()
                ref.set({
                    'user_id': user_id,
                    'txn_id': txn_id,
                    'amount': data.get('amount', 100),
                    'plan': data.get('plan', 'Earner Pro'),
                    'status': 'pending',
                    'timestamp': time.time()
                })
        except:
            pass  # Firebase optional
        
        return jsonify({'success': True, 'message': 'Payment submitted'})
    except Exception as e:
        logger.error(f"Payment error: {e}")
        return jsonify({'error': str(e)}), 500

# ============= ERROR HANDLERS =============
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not Found', 'path': request.path}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

# ============= MAIN =============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🚀 Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
