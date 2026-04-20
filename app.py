"""
🌐 Flask Web Application - FIXED
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import logging
from datetime import datetime
import sys

# Configure logging FIRST
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Initialize Flask app FIRST
app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static'
)

# Load config
try:
    from config import current_config, config_by_name
    app.config.from_object(current_config)
    logger.info("✅ Config loaded successfully")
except Exception as e:
    logger.error(f"❌ Config loading failed: {e}")
    # Create minimal config
    class FallbackConfig:
        SECRET_KEY = os.urandom(24).hex()
        DEBUG = False
        FIREBASE_CONFIG = {}
        FRONTEND_FIREBASE = {
            'apiKey': os.getenv('FIREBASE_API_KEY', ''),
            'databaseURL': os.getenv('FIREBASE_DATABASE_URL', '')
        }
        BOT_TOKEN = os.getenv('BOT_TOKEN', '')
        ADMIN_USER_IDS = []
        POINTS_PER_DOLLAR = 100
        AD_POINTS = 25
        SOCIAL_POINTS = 100
        REFERRAL_BONUS = 50
        WEBAPP_URL = os.getenv('VERCEL_URL', 'http://localhost:8080')
        ADMIN_SECRET_KEY = os.getenv('ADMIN_SECRET_KEY', 'dev-key')
    
    current_config = FallbackConfig()

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Rate limiting
try:
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["10 per minute"],
        storage_uri="memory://"
    )
    logger.info("✅ Rate limiter initialized")
except Exception as e:
    logger.warning(f"⚠️ Rate limiter setup failed: {e}")
    limiter = None

# Initialize Firebase
db_instance = None

def init_firebase_safe():
    """Safe Firebase initialization with error handling"""
    global db_instance
    
    try:
        import firebase_admin
        from firebase_admin import credentials, db
        
        # Check if already initialized
        if not firebase_admin._apps:
            # Try to load from environment
            firebase_config = current_config.FIREBASE_CONFIG
            
            if not firebase_config.get('private_key'):
                logger.warning("⚠️ Firebase credentials not found - running in limited mode")
                return False
            
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred, {
                'databaseURL': current_config.FRONTEND_FIREBASE.get('databaseURL', '')
            })
            
            from database import Database
            db_instance = Database()
            logger.info("✅ Firebase initialized successfully")
            return True
        else:
            logger.info("✅ Firebase already initialized")
            return True
            
    except Exception as e:
        logger.error(f"❌ Firebase initialization error: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(traceback.format_exc())
        return False

# Try to initialize Firebase
firebase_ready = init_firebase_safe()

def get_db():
    """Get database instance with fallback"""
    global db_instance
    if db_instance is None:
        if not firebase_ready:
            raise RuntimeError("Database not available - check Firebase credentials")
        init_firebase_safe()
    return db_instance

# ─────────────────────────────────────────────────────────────────────
# 🌐 Frontend Routes
# ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Root redirect"""
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    """Dashboard with error handling"""
    try:
        telegram_id = request.args.get('id', type=int)
        username = request.args.get('name', 'User')
        
        # Fallback if no ID provided
        if not telegram_id:
            telegram_id = 123456  # Demo ID
        
        # Render with minimal config if Firebase not ready
        user_data = {
            'telegram_id': telegram_id,
            'first_name': username,
            'points': 0,
            'tasks_completed': 0,
            'pending_submissions': {}
        }
        
        if firebase_ready:
            try:
                db = get_db()
                user = db.get_user(telegram_id)
                if user:
                    user_data = user
            except Exception as e:
                logger.warning(f"Could not fetch user: {e}")
        
        return render_template(
            'index.html',
            user=user_data,
            firebase_config=current_config.FRONTEND_FIREBASE,
            banner_image="https://i.ibb.co/9kmTw4Gh/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg",
            config={
                'points_per_dollar': current_config.POINTS_PER_DOLLAR,
                'ad_points': current_config.AD_POINTS,
                'social_points': current_config.SOCIAL_POINTS,
                'referral_bonus': current_config.REFERRAL_BONUS,
                'ad_link': os.getenv('AD_SMART_LINK', ''),
                'youtube_link': os.getenv('YOUTUBE_LINK', ''),
                'instagram_link': os.getenv('INSTAGRAM_LINK', ''),
                'facebook_link': os.getenv('FACEBOOK_LINK', ''),
                'webapp_url': current_config.WEBAPP_URL,
                'bot_username': os.getenv('BOT_USERNAME', 'bot')
            },
            initial_data={
                'telegram_id': telegram_id,
                'username': username,
                'task_filter': '',
                'section': 'home',
                'notifications': []
            }
        )
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return f"<h1>Error</h1><p>{str(e)}</p>", 500

@app.route('/admin')
def admin_panel():
    """Admin panel"""
    admin_key = request.args.get('key', '')
    admin_id = request.args.get('admin_id', '0')
    
    if admin_key != current_config.ADMIN_SECRET_KEY:
        return "Unauthorized", 401
    
    return render_template(
        'admin.html',
        firebase_config=current_config.FRONTEND_FIREBASE,
        admin_id=admin_id,
        stats={'total_users': 0, 'pending_reviews': 0},
        pending_submissions=[],
        config={'app_url': current_config.WEBAPP_URL, 'admin_key': admin_key}
    )

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    return '', 204

# ─────────────────────────────────────────────────────────────────────
# 🔌 API Endpoints (Simplified)
# ─────────────────────────────────────────────────────────────────────

@app.route('/api/user', methods=['GET'])
def api_get_user():
    """Get user data"""
    telegram_id = request.args.get('id', type=int) or request.headers.get('X-User-ID', type=int)
    
    if not telegram_id:
        return jsonify({'success': False, 'error': 'No user ID'}), 400
    
    user_data = {
        'telegram_id': telegram_id,
        'points': 0,
        'tasks_completed': 0,
        'pending_submissions': {},
        'balance_usd': 0,
        'can_withdraw': False
    }
    
    if firebase_ready:
        try:
            db = get_db()
            user = db.get_user(telegram_id)
            if user:
                user_data = {
                    **user,
                    'balance_usd': user.get('points', 0) / current_config.POINTS_PER_DOLLAR,
                    'can_withdraw': user.get('points', 0) >= current_config.POINT_PER_DOLLAR
                }
        except Exception as e:
            logger.warning(f"API get user error: {e}")
    
    return jsonify({'success': True, 'data': user_data})

@app.route('/api/tasks', methods=['GET'])
def api_get_tasks():
    """Get available tasks"""
    tasks = [
        {
            'id': 'ad',
            'icon': '📺',
            'title': 'Watch Advertisement',
            'description': 'View a short ad (30 seconds)',
            'points': current_config.AD_POINTS,
            'type': 'instant',
            'completed': False
        },
        {
            'id': 'youtube_subscribe',
            'icon': '▶️',
            'title': 'YouTube Subscribe',
            'description': 'Subscribe to our channel',
            'points': current_config.SOCIAL_POINTS,
            'type': 'verification',
            'completed': False,
            'link': os.getenv('YOUTUBE_LINK', '')
        }
    ]
    return jsonify({'success': True, 'data': {'tasks': tasks}})

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'firebase': 'connected' if firebase_ready else 'disconnected',
        'timestamp': int(datetime.now().timestamp() * 1000)
    }), 200

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

# ─────────────────────────────────────────────────────────────────────
# 🚀 Entry Point
# ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🚀 Starting server on port {port}")
    logger.info(f"🔧 Debug mode: {current_config.DEBUG}")
    logger.info(f"🗄️ Firebase: {'Ready' if firebase_ready else 'Not configured'}")
    app.run(host='0.0.0.0', port=port, debug=current_config.DEBUG)
