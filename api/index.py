"""
🌐 Flask Web Application - TWA Dashboard & Admin Panel
Serves premium mobile-responsive frontend and API endpoints.
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import logging
from datetime import datetime

from config import current_config, config_by_name
from database import get_db, init_firebase
from utils.security import (
    rate_limit, api_limiter, submission_limiter,
    require_admin, validate_user_session, sanitize_input,
    generate_device_fingerprint, check_fraud_patterns,
    is_valid_screenshot_url
)
from utils.verification import validate_screenshot_url, get_task_requirements
from utils.helpers import api_response, format_points, log_action, safe_int

# Configure logging
logging.basicConfig(
    level=logging.INFO if not current_config.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static'
)
app.config.from_object(current_config)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[f"{current_config.RATE_LIMIT_REQUESTS} per {current_config.RATE_LIMIT_WINDOW} seconds"],
    storage_uri="memory://"
)

# Initialize Firebase
init_firebase()


# ─────────────────────────────────────────────────────────────────────────────
# 🌐 Frontend Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Redirect to dashboard with user params"""
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
@limiter.limit("20 per minute")
def dashboard():
    """Premium User Dashboard (TWA)"""
    telegram_id = request.args.get('id', type=int)
    username = request.args.get('name', 'User')
    task_filter = request.args.get('task', '')
    section = request.args.get('section', 'home')
    
    # Security: Validate user session
    if not telegram_id:
        return render_template('index.html', 
                            error="Invalid access. Open from Telegram bot.",
                            firebase_config=current_config.FRONTEND_FIREBASE)
    
    # Track access for anti-fraud
    db = get_db()
    ip_hash = None
    if current_config.ENABLE_IP_TRACKING:
        from utils.security import generate_device_fingerprint
        device_fp = generate_device_fingerprint(
            request.headers.get('User-Agent', ''),
            request.remote_addr or '',
            request.headers.get('Accept', '')
        )
        access_result = db.record_user_access(telegram_id, request.remote_addr or '', device_fp)
        
        if not access_result['allowed']:
            return render_template('index.html',
                                error=f"⚠️ Access restricted: {access_result['account_count_on_ip']} accounts on this IP",
                                firebase_config=current_config.FRONTEND_FIREBASE)
        ip_hash = access_result.get('ip_hash')
    
    # Fetch user data
    user = db.get_user(telegram_id)
    if not user:
        return render_template('index.html',
                            error="User not found. Please start the bot first.",
                            firebase_config=current_config.FRONTEND_FIREBASE)
    
    # Check for pending notifications
    notifications = []
    if 'notifications' in user:
        for nid, note in user['notifications'].items():
            if not note.get('read', False):
                notifications.append({**note, 'id': nid})
    
    return render_template(
        'index.html',
        user=user,
        firebase_config=current_config.FRONTEND_FIREBASE,
        banner_image="https://i.ibb.co/9kmTw4Gh/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg",
        config={
            'points_per_dollar': current_config.POINTS_PER_DOLLAR,
            'ad_points': current_config.AD_POINTS,
            'social_points': current_config.SOCIAL_POINTS,
            'referral_bonus': current_config.REFERRAL_BONUS,
            'ad_link': current_config.AD_SMART_LINK,
            'youtube_link': current_config.YOUTUBE_LINK,
            'instagram_link': current_config.INSTAGRAM_LINK,
            'facebook_link': current_config.FACEBOOK_LINK,
            'webapp_url': current_config.WEBAPP_URL
        },
        initial_data={
            'telegram_id': telegram_id,
            'username': username,
            'task_filter': task_filter,
            'section': section,
            'notifications': notifications[:5]  # Limit for initial load
        }
    )


@app.route('/admin')
@require_admin
def admin_panel():
    """Secure Admin Panel"""
    admin_id = getattr(request.args, 'admin_id', None) or request.headers.get('X-Admin-ID')
    
    if not admin_id or int(admin_id) not in current_config.ADMIN_USER_IDS:
        return redirect(url_for('dashboard'))
    
    # Get platform stats
    db = get_db()
    stats = db.get_user_stats()
    pending = db.get_pending_submissions(limit=20)
    
    return render_template(
        'admin.html',
        firebase_config=current_config.FRONTEND_FIREBASE,
        admin_id=admin_id,
        stats=stats,
        pending_submissions=pending,
        config={
            'app_url': current_config.APP_URL,
            'admin_key': current_config.ADMIN_SECRET_KEY
        }
    )


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files with caching"""
    return send_from_directory('static', filename, max_age=3600)


# ─────────────────────────────────────────────────────────────────────────────
# 🔌 API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/user', methods=['GET'])
@rate_limit(api_limiter)
def api_get_user():
    """Get current user data"""
    telegram_id = validate_user_session()
    if not telegram_id:
        return api_response(False, error="Unauthorized", status_code=401)
    
    db = get_db()
    user = db.get_user(telegram_id)
    
    if not user:
        return api_response(False, error="User not found", status_code=404)
    
    # Calculate derived values
    user['balance_usd'] = user.get('points', 0) / current_config.POINTS_PER_DOLLAR
    user['can_withdraw'] = user.get('points', 0) >= current_config.POINTS_PER_DOLLAR
    user['referral_link'] = f"https://t.me/{os.getenv('BOT_USERNAME', 'bot')}?start={user.get('referral_code', '')}"
    
    # Remove sensitive fields
    safe_user = {k: v for k, v in user.items() if k not in ['ip_hash', 'device_fingerprint']}
    
    return api_response(True, data=safe_user)


@app.route('/api/tasks', methods=['GET'])
@rate_limit(api_limiter)
def api_get_tasks():
    """Get available tasks with user completion status"""
    telegram_id = validate_user_session()
    if not telegram_id:
        return api_response(False, error="Unauthorized", status_code=401)
    
    db = get_db()
    user = db.get_user(telegram_id)
    if not user:
        return api_response(False, error="User not found", status_code=404)
    
    # Get user's recent submissions to show completion status
    recent_subs = db.submissions_ref.order_by_child('user_id').equal_to(telegram_id).limit_to_last(50).get()
    completed_tasks = {}
    
    if recent_subs:
        for sub in recent_subs.values():
            if sub.get('status') == 'approved':
                completed_tasks[sub.get('task_type')] = True
    
    tasks = [
        {
            'id': 'ad',
            'icon': '📺',
            'title': 'Watch Advertisement',
            'description': 'View a short ad (30 seconds)',
            'points': current_config.AD_POINTS,
            'type': 'instant',
            'completed': completed_tasks.get('ad', False),
            'cooldown': 3600  # 1 hour between ad views
        },
        {
            'id': 'youtube_subscribe',
            'icon': '▶️',
            'title': 'YouTube Subscribe',
            'description': 'Subscribe to our channel',
            'points': current_config.SOCIAL_POINTS,
            'type': 'verification',
            'completed': completed_tasks.get('youtube_subscribe', False),
            'link': current_config.YOUTUBE_LINK,
            'requirements': get_task_requirements('youtube_subscribe')
        },
        {
            'id': 'youtube_like',
            'icon': '❤️',
            'title': 'YouTube Like Video',
            'description': 'Like our latest video',
            'points': current_config.SOCIAL_POINTS,
            'type': 'verification',
            'completed': completed_tasks.get('youtube_like', False),
            'link': current_config.YOUTUBE_LINK,
            'requirements': get_task_requirements('youtube_like')
        },
        {
            'id': 'facebook_follow',
            'icon': '📘',
            'title': 'Facebook Follow',
            'description': 'Follow our Facebook page',
            'points': current_config.SOCIAL_POINTS,
            'type': 'verification',
            'completed': completed_tasks.get('facebook_follow', False),
            'link': current_config.FACEBOOK_LINK,
            'requirements': get_task_requirements('facebook_follow')
        },
        {
            'id': 'instagram_follow',
            'icon': '📷',
            'title': 'Instagram Follow',
            'description': 'Follow our Instagram',
            'points': current_config.SOCIAL_POINTS,
            'type': 'verification',
            'completed': completed_tasks.get('instagram_follow', False),
            'link': current_config.INSTAGRAM_LINK,
            'requirements': get_task_requirements('instagram_follow')
        }
    ]
    
    return api_response(True, data={'tasks': tasks})


@app.route('/api/submit/task', methods=['POST'])
@rate_limit(submission_limiter)
def api_submit_task():
    """Submit task completion with screenshot"""
    telegram_id = validate_user_session()
    if not telegram_id:
        return api_response(False, error="Unauthorized", status_code=401)
    
    try:
        data = request.get_json() or {}
        task_type = sanitize_input(data.get('task_type'))
        screenshot_url = sanitize_input(data.get('screenshot_url'))
        proof_text = sanitize_input(data.get('proof_text', ''), max_length=200)
        
        # Validate inputs
        if not task_type or not screenshot_url:
            return api_response(False, error="Task type and screenshot URL required", status_code=400)
        
        # Validate screenshot URL
        is_valid, error_msg = validate_screenshot_url(screenshot_url)
        if not is_valid:
            return api_response(False, error=f"Invalid screenshot: {error_msg}", status_code=400)
        
        # Check for fraud patterns
        from utils.security import check_fraud_patterns
        fraud_flags = check_fraud_patterns(telegram_id, request.remote_addr or '')
        if fraud_flags['multiple_accounts_same_ip'] or fraud_flags['rapid_submissions']:
            log_action('fraud_detected', telegram_id, fraud_flags, 'warning')
            return api_response(False, error="Suspicious activity detected", status_code=403)
        
        # Check for duplicate submissions
        from utils.verification import check_duplicate_submission, generate_screenshot_hash
        screenshot_hash = generate_screenshot_hash(screenshot_url, telegram_id, task_type)
        if check_duplicate_submission(telegram_id, task_type, screenshot_hash):
            return api_response(False, error="Similar submission already pending", status_code=409)
        
        # Create submission
        db = get_db()
        submission_id = db.create_submission(telegram_id, task_type, screenshot_url, proof_text)
        
        log_action('submission_created', telegram_id, {'task': task_type, 'submission_id': submission_id})
        
        return api_response(True, data={
            'submission_id': submission_id,
            'status': 'pending',
            'message': 'Submission received! Awaiting admin approval (~24h)'
        })
        
    except Exception as e:
        logger.error(f"Task submission error: {e}")
        return api_response(False, error="Submission failed", status_code=500)


@app.route('/api/earn/ad', methods=['POST'])
@rate_limit(api_limiter)
def api_earn_ad():
    """Instant ad view reward (no verification needed)"""
    telegram_id = validate_user_session()
    if not telegram_id:
        return api_response(False, error="Unauthorized", status_code=401)
    
    db = get_db()
    user = db.get_user(telegram_id)
    
    if not user:
        return api_response(False, error="User not found", status_code=404)
    
    # Check cooldown (1 hour between ad views)
    history = user.get('history', {}) or {}
    recent_ad = None
    for entry in history.values():
        if entry.get('type') == 'ad_view':
            recent_ad = entry
            break
    
    if recent_ad:
        time_diff = datetime.now().timestamp() * 1000 - recent_ad.get('timestamp', 0)
        if time_diff < 3600000:  # 1 hour in ms
            remaining = int((3600000 - time_diff) / 60000)
            return api_response(False, error=f"Please wait {remaining} minutes before next ad", status_code=429)
    
    # Award points
    if db.add_points(telegram_id, current_config.AD_POINTS, 'ad_view', 'Ad watched'):
        log_action('ad_rewarded', telegram_id, {'points': current_config.AD_POINTS})
        return api_response(True, data={'points_added': current_config.AD_POINTS})
    
    return api_response(False, error="Failed to award points", status_code=500)


@app.route('/api/referral/stats', methods=['GET'])
@rate_limit(api_limiter)
def api_referral_stats():
    """Get referral statistics for user"""
    telegram_id = validate_user_session()
    if not telegram_id:
        return api_response(False, error="Unauthorized", status_code=401)
    
    db = get_db()
    user = db.get_user(telegram_id)
    
    if not user:
        return api_response(False, error="User not found", status_code=404)
    
    # Get referrals
    referrals = db.referrals_ref.child(str(telegram_id)).get() or {}
    
    stats = {
        'total_referrals': len(referrals),
        'total_bonus_earned': len(referrals) * current_config.REFERRAL_BONUS,
        'referral_link': f"https://t.me/{os.getenv('BOT_USERNAME', 'bot')}?start={user.get('referral_code', '')}",
        'recent_referrals': []
    }
    
    # Get recent referral details
    for ref_id, ref_data in list(referrals.items())[-10:]:
        ref_user = db.get_user(int(ref_id))
        if ref_user:
            stats['recent_referrals'].append({
                'username': ref_user.get('username', 'Unknown'),
                'joined': ref_data.get('joined_at'),
                'bonus': ref_data.get('bonus_awarded', current_config.REFERRAL_BONUS)
            })
    
    return api_response(True, data=stats)


# ─────────────────────────────────────────────────────────────────────────────
# 🔐 Admin API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/admin/submissions', methods=['GET'])
@require_admin
@rate_limit(api_limiter)
def api_admin_get_submissions():
    """Admin: Get pending submissions for review"""
    limit = safe_int(request.args.get('limit', 20), 20)
    db = get_db()
    
    submissions = db.get_pending_submissions(limit=limit)
    
    return api_response(True, data={
        'submissions': submissions,
        'count': len(submissions)
    })


@app.route('/api/admin/review', methods=['POST'])
@require_admin
@rate_limit(api_limiter)
def api_admin_review_submission():
    """Admin: Approve or reject submission"""
    try:
        data = request.get_json() or {}
        submission_id = data.get('submission_id')
        approved = data.get('approved', False)
        reason = sanitize_input(data.get('reason', ''), max_length=200)
        
        if not submission_id:
            return api_response(False, error="Submission ID required", status_code=400)
        
        db = get_db()
        admin_id = getattr(request, 'admin_id', request.headers.get('X-Admin-ID', '0'))
        
        if db.review_submission(submission_id, int(admin_id), approved, reason):
            action = 'approved' if approved else 'rejected'
            log_action(f'submission_{action}', int(admin_id), {
                'submission_id': submission_id,
                'reason': reason
            })
            return api_response(True, data={'status': action})
        
        return api_response(False, error="Review failed", status_code=500)
        
    except Exception as e:
        logger.error(f"Admin review error: {e}")
        return api_response(False, error="Internal error", status_code=500)


@app.route('/api/admin/broadcast', methods=['POST'])
@require_admin
@rate_limit("5 per minute")
def api_admin_broadcast():
    """Admin: Send broadcast message"""
    try:
        data = request.get_json() or {}
        message = sanitize_input(data.get('message'), max_length=1000)
        target_users = data.get('user_ids')  # Optional list
        
        if not message:
            return api_response(False, error="Message required", status_code=400)
        
        db = get_db()
        admin_id = getattr(request, 'admin_id', request.headers.get('X-Admin-ID', '0'))
        
        result = db.broadcast_message(int(admin_id), message, target_users)
        
        if result.get('success'):
            log_action('broadcast_sent', int(admin_id), {
                'count': result['sent'],
                'message': message[:100]
            })
            return api_response(True, data=result)
        
        return api_response(False, error=result.get('error', 'Broadcast failed'), status_code=500)
        
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        return api_response(False, error="Internal error", status_code=500)


@app.route('/api/admin/stats', methods=['GET'])
@require_admin
def api_admin_stats():
    """Admin: Get platform statistics"""
    db = get_db()
    stats = db.get_user_stats()
    
    return api_response(True, data=stats)


# ─────────────────────────────────────────────────────────────────────────────
# 🔍 Health & Utility
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/health')
def health_check():
    """Vercel/Railway health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'telegram-earning-bot',
        'timestamp': int(datetime.now().timestamp() * 1000),
        'version': '1.0.0'
    }), 200


@app.errorhandler(404)
def not_found(e):
    return api_response(False, error="Not found", status_code=404)


@app.errorhandler(429)
def rate_limit_exceeded(e):
    return api_response(False, error="Too many requests. Please slow down.", status_code=429)


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return api_response(False, error="Internal server error", status_code=500)


# ─────────────────────────────────────────────────────────────────────────────
# 🚀 Entry Point for Vercel
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🚀 Starting server on port {port} ({current_config.FLASK_ENV})")
    app.run(host='0.0.0.0', port=port, debug=current_config.DEBUG)
"""
🌐 Flask Web Application - TWA Dashboard & Admin Panel
Serves premium mobile-responsive frontend and API endpoints.
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import logging
from datetime import datetime

from config import current_config, config_by_name
from database import get_db, init_firebase
from utils.security import (
    rate_limit, api_limiter, submission_limiter,
    require_admin, validate_user_session, sanitize_input,
    generate_device_fingerprint, check_fraud_patterns,
    is_valid_screenshot_url
)
from utils.verification import validate_screenshot_url, get_task_requirements
from utils.helpers import api_response, format_points, log_action, safe_int

# Configure logging
logging.basicConfig(
    level=logging.INFO if not current_config.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static'
)
app.config.from_object(current_config)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[f"{current_config.RATE_LIMIT_REQUESTS} per {current_config.RATE_LIMIT_WINDOW} seconds"],
    storage_uri="memory://"
)

# Initialize Firebase
init_firebase()


# ─────────────────────────────────────────────────────────────────────────────
# 🌐 Frontend Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Redirect to dashboard with user params"""
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
@limiter.limit("20 per minute")
def dashboard():
    """Premium User Dashboard (TWA)"""
    telegram_id = request.args.get('id', type=int)
    username = request.args.get('name', 'User')
    task_filter = request.args.get('task', '')
    section = request.args.get('section', 'home')
    
    # Security: Validate user session
    if not telegram_id:
        return render_template('index.html', 
                            error="Invalid access. Open from Telegram bot.",
                            firebase_config=current_config.FRONTEND_FIREBASE)
    
    # Track access for anti-fraud
    db = get_db()
    ip_hash = None
    if current_config.ENABLE_IP_TRACKING:
        from utils.security import generate_device_fingerprint
        device_fp = generate_device_fingerprint(
            request.headers.get('User-Agent', ''),
            request.remote_addr or '',
            request.headers.get('Accept', '')
        )
        access_result = db.record_user_access(telegram_id, request.remote_addr or '', device_fp)
        
        if not access_result['allowed']:
            return render_template('index.html',
                                error=f"⚠️ Access restricted: {access_result['account_count_on_ip']} accounts on this IP",
                                firebase_config=current_config.FRONTEND_FIREBASE)
        ip_hash = access_result.get('ip_hash')
    
    # Fetch user data
    user = db.get_user(telegram_id)
    if not user:
        return render_template('index.html',
                            error="User not found. Please start the bot first.",
                            firebase_config=current_config.FRONTEND_FIREBASE)
    
    # Check for pending notifications
    notifications = []
    if 'notifications' in user:
        for nid, note in user['notifications'].items():
            if not note.get('read', False):
                notifications.append({**note, 'id': nid})
    
    return render_template(
        'index.html',
        user=user,
        firebase_config=current_config.FRONTEND_FIREBASE,
        banner_image="https://i.ibb.co/9kmTw4Gh/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg",
        config={
            'points_per_dollar': current_config.POINTS_PER_DOLLAR,
            'ad_points': current_config.AD_POINTS,
            'social_points': current_config.SOCIAL_POINTS,
            'referral_bonus': current_config.REFERRAL_BONUS,
            'ad_link': current_config.AD_SMART_LINK,
            'youtube_link': current_config.YOUTUBE_LINK,
            'instagram_link': current_config.INSTAGRAM_LINK,
            'facebook_link': current_config.FACEBOOK_LINK,
            'webapp_url': current_config.WEBAPP_URL
        },
        initial_data={
            'telegram_id': telegram_id,
            'username': username,
            'task_filter': task_filter,
            'section': section,
            'notifications': notifications[:5]  # Limit for initial load
        }
    )


@app.route('/admin')
@require_admin
def admin_panel():
    """Secure Admin Panel"""
    admin_id = getattr(request.args, 'admin_id', None) or request.headers.get('X-Admin-ID')
    
    if not admin_id or int(admin_id) not in current_config.ADMIN_USER_IDS:
        return redirect(url_for('dashboard'))
    
    # Get platform stats
    db = get_db()
    stats = db.get_user_stats()
    pending = db.get_pending_submissions(limit=20)
    
    return render_template(
        'admin.html',
        firebase_config=current_config.FRONTEND_FIREBASE,
        admin_id=admin_id,
        stats=stats,
        pending_submissions=pending,
        config={
            'app_url': current_config.APP_URL,
            'admin_key': current_config.ADMIN_SECRET_KEY
        }
    )


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files with caching"""
    return send_from_directory('static', filename, max_age=3600)


# ─────────────────────────────────────────────────────────────────────────────
# 🔌 API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/user', methods=['GET'])
@rate_limit(api_limiter)
def api_get_user():
    """Get current user data"""
    telegram_id = validate_user_session()
    if not telegram_id:
        return api_response(False, error="Unauthorized", status_code=401)
    
    db = get_db()
    user = db.get_user(telegram_id)
    
    if not user:
        return api_response(False, error="User not found", status_code=404)
    
    # Calculate derived values
    user['balance_usd'] = user.get('points', 0) / current_config.POINTS_PER_DOLLAR
    user['can_withdraw'] = user.get('points', 0) >= current_config.POINTS_PER_DOLLAR
    user['referral_link'] = f"https://t.me/{os.getenv('BOT_USERNAME', 'bot')}?start={user.get('referral_code', '')}"
    
    # Remove sensitive fields
    safe_user = {k: v for k, v in user.items() if k not in ['ip_hash', 'device_fingerprint']}
    
    return api_response(True, data=safe_user)


@app.route('/api/tasks', methods=['GET'])
@rate_limit(api_limiter)
def api_get_tasks():
    """Get available tasks with user completion status"""
    telegram_id = validate_user_session()
    if not telegram_id:
        return api_response(False, error="Unauthorized", status_code=401)
    
    db = get_db()
    user = db.get_user(telegram_id)
    if not user:
        return api_response(False, error="User not found", status_code=404)
    
    # Get user's recent submissions to show completion status
    recent_subs = db.submissions_ref.order_by_child('user_id').equal_to(telegram_id).limit_to_last(50).get()
    completed_tasks = {}
    
    if recent_subs:
        for sub in recent_subs.values():
            if sub.get('status') == 'approved':
                completed_tasks[sub.get('task_type')] = True
    
    tasks = [
        {
            'id': 'ad',
            'icon': '📺',
            'title': 'Watch Advertisement',
            'description': 'View a short ad (30 seconds)',
            'points': current_config.AD_POINTS,
            'type': 'instant',
            'completed': completed_tasks.get('ad', False),
            'cooldown': 3600  # 1 hour between ad views
        },
        {
            'id': 'youtube_subscribe',
            'icon': '▶️',
            'title': 'YouTube Subscribe',
            'description': 'Subscribe to our channel',
            'points': current_config.SOCIAL_POINTS,
            'type': 'verification',
            'completed': completed_tasks.get('youtube_subscribe', False),
            'link': current_config.YOUTUBE_LINK,
            'requirements': get_task_requirements('youtube_subscribe')
        },
        {
            'id': 'youtube_like',
            'icon': '❤️',
            'title': 'YouTube Like Video',
            'description': 'Like our latest video',
            'points': current_config.SOCIAL_POINTS,
            'type': 'verification',
            'completed': completed_tasks.get('youtube_like', False),
            'link': current_config.YOUTUBE_LINK,
            'requirements': get_task_requirements('youtube_like')
        },
        {
            'id': 'facebook_follow',
            'icon': '📘',
            'title': 'Facebook Follow',
            'description': 'Follow our Facebook page',
            'points': current_config.SOCIAL_POINTS,
            'type': 'verification',
            'completed': completed_tasks.get('facebook_follow', False),
            'link': current_config.FACEBOOK_LINK,
            'requirements': get_task_requirements('facebook_follow')
        },
        {
            'id': 'instagram_follow',
            'icon': '📷',
            'title': 'Instagram Follow',
            'description': 'Follow our Instagram',
            'points': current_config.SOCIAL_POINTS,
            'type': 'verification',
            'completed': completed_tasks.get('instagram_follow', False),
            'link': current_config.INSTAGRAM_LINK,
            'requirements': get_task_requirements('instagram_follow')
        }
    ]
    
    return api_response(True, data={'tasks': tasks})


@app.route('/api/submit/task', methods=['POST'])
@rate_limit(submission_limiter)
def api_submit_task():
    """Submit task completion with screenshot"""
    telegram_id = validate_user_session()
    if not telegram_id:
        return api_response(False, error="Unauthorized", status_code=401)
    
    try:
        data = request.get_json() or {}
        task_type = sanitize_input(data.get('task_type'))
        screenshot_url = sanitize_input(data.get('screenshot_url'))
        proof_text = sanitize_input(data.get('proof_text', ''), max_length=200)
        
        # Validate inputs
        if not task_type or not screenshot_url:
            return api_response(False, error="Task type and screenshot URL required", status_code=400)
        
        # Validate screenshot URL
        is_valid, error_msg = validate_screenshot_url(screenshot_url)
        if not is_valid:
            return api_response(False, error=f"Invalid screenshot: {error_msg}", status_code=400)
        
        # Check for fraud patterns
        from utils.security import check_fraud_patterns
        fraud_flags = check_fraud_patterns(telegram_id, request.remote_addr or '')
        if fraud_flags['multiple_accounts_same_ip'] or fraud_flags['rapid_submissions']:
            log_action('fraud_detected', telegram_id, fraud_flags, 'warning')
            return api_response(False, error="Suspicious activity detected", status_code=403)
        
        # Check for duplicate submissions
        from utils.verification import check_duplicate_submission, generate_screenshot_hash
        screenshot_hash = generate_screenshot_hash(screenshot_url, telegram_id, task_type)
        if check_duplicate_submission(telegram_id, task_type, screenshot_hash):
            return api_response(False, error="Similar submission already pending", status_code=409)
        
        # Create submission
        db = get_db()
        submission_id = db.create_submission(telegram_id, task_type, screenshot_url, proof_text)
        
        log_action('submission_created', telegram_id, {'task': task_type, 'submission_id': submission_id})
        
        return api_response(True, data={
            'submission_id': submission_id,
            'status': 'pending',
            'message': 'Submission received! Awaiting admin approval (~24h)'
        })
        
    except Exception as e:
        logger.error(f"Task submission error: {e}")
        return api_response(False, error="Submission failed", status_code=500)


@app.route('/api/earn/ad', methods=['POST'])
@rate_limit(api_limiter)
def api_earn_ad():
    """Instant ad view reward (no verification needed)"""
    telegram_id = validate_user_session()
    if not telegram_id:
        return api_response(False, error="Unauthorized", status_code=401)
    
    db = get_db()
    user = db.get_user(telegram_id)
    
    if not user:
        return api_response(False, error="User not found", status_code=404)
    
    # Check cooldown (1 hour between ad views)
    history = user.get('history', {}) or {}
    recent_ad = None
    for entry in history.values():
        if entry.get('type') == 'ad_view':
            recent_ad = entry
            break
    
    if recent_ad:
        time_diff = datetime.now().timestamp() * 1000 - recent_ad.get('timestamp', 0)
        if time_diff < 3600000:  # 1 hour in ms
            remaining = int((3600000 - time_diff) / 60000)
            return api_response(False, error=f"Please wait {remaining} minutes before next ad", status_code=429)
    
    # Award points
    if db.add_points(telegram_id, current_config.AD_POINTS, 'ad_view', 'Ad watched'):
        log_action('ad_rewarded', telegram_id, {'points': current_config.AD_POINTS})
        return api_response(True, data={'points_added': current_config.AD_POINTS})
    
    return api_response(False, error="Failed to award points", status_code=500)


@app.route('/api/referral/stats', methods=['GET'])
@rate_limit(api_limiter)
def api_referral_stats():
    """Get referral statistics for user"""
    telegram_id = validate_user_session()
    if not telegram_id:
        return api_response(False, error="Unauthorized", status_code=401)
    
    db = get_db()
    user = db.get_user(telegram_id)
    
    if not user:
        return api_response(False, error="User not found", status_code=404)
    
    # Get referrals
    referrals = db.referrals_ref.child(str(telegram_id)).get() or {}
    
    stats = {
        'total_referrals': len(referrals),
        'total_bonus_earned': len(referrals) * current_config.REFERRAL_BONUS,
        'referral_link': f"https://t.me/{os.getenv('BOT_USERNAME', 'bot')}?start={user.get('referral_code', '')}",
        'recent_referrals': []
    }
    
    # Get recent referral details
    for ref_id, ref_data in list(referrals.items())[-10:]:
        ref_user = db.get_user(int(ref_id))
        if ref_user:
            stats['recent_referrals'].append({
                'username': ref_user.get('username', 'Unknown'),
                'joined': ref_data.get('joined_at'),
                'bonus': ref_data.get('bonus_awarded', current_config.REFERRAL_BONUS)
            })
    
    return api_response(True, data=stats)


# ─────────────────────────────────────────────────────────────────────────────
# 🔐 Admin API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/admin/submissions', methods=['GET'])
@require_admin
@rate_limit(api_limiter)
def api_admin_get_submissions():
    """Admin: Get pending submissions for review"""
    limit = safe_int(request.args.get('limit', 20), 20)
    db = get_db()
    
    submissions = db.get_pending_submissions(limit=limit)
    
    return api_response(True, data={
        'submissions': submissions,
        'count': len(submissions)
    })


@app.route('/api/admin/review', methods=['POST'])
@require_admin
@rate_limit(api_limiter)
def api_admin_review_submission():
    """Admin: Approve or reject submission"""
    try:
        data = request.get_json() or {}
        submission_id = data.get('submission_id')
        approved = data.get('approved', False)
        reason = sanitize_input(data.get('reason', ''), max_length=200)
        
        if not submission_id:
            return api_response(False, error="Submission ID required", status_code=400)
        
        db = get_db()
        admin_id = getattr(request, 'admin_id', request.headers.get('X-Admin-ID', '0'))
        
        if db.review_submission(submission_id, int(admin_id), approved, reason):
            action = 'approved' if approved else 'rejected'
            log_action(f'submission_{action}', int(admin_id), {
                'submission_id': submission_id,
                'reason': reason
            })
            return api_response(True, data={'status': action})
        
        return api_response(False, error="Review failed", status_code=500)
        
    except Exception as e:
        logger.error(f"Admin review error: {e}")
        return api_response(False, error="Internal error", status_code=500)


@app.route('/api/admin/broadcast', methods=['POST'])
@require_admin
@rate_limit("5 per minute")
def api_admin_broadcast():
    """Admin: Send broadcast message"""
    try:
        data = request.get_json() or {}
        message = sanitize_input(data.get('message'), max_length=1000)
        target_users = data.get('user_ids')  # Optional list
        
        if not message:
            return api_response(False, error="Message required", status_code=400)
        
        db = get_db()
        admin_id = getattr(request, 'admin_id', request.headers.get('X-Admin-ID', '0'))
        
        result = db.broadcast_message(int(admin_id), message, target_users)
        
        if result.get('success'):
            log_action('broadcast_sent', int(admin_id), {
                'count': result['sent'],
                'message': message[:100]
            })
            return api_response(True, data=result)
        
        return api_response(False, error=result.get('error', 'Broadcast failed'), status_code=500)
        
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        return api_response(False, error="Internal error", status_code=500)


@app.route('/api/admin/stats', methods=['GET'])
@require_admin
def api_admin_stats():
    """Admin: Get platform statistics"""
    db = get_db()
    stats = db.get_user_stats()
    
    return api_response(True, data=stats)


# ─────────────────────────────────────────────────────────────────────────────
# 🔍 Health & Utility
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/health')
def health_check():
    """Vercel/Railway health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'telegram-earning-bot',
        'timestamp': int(datetime.now().timestamp() * 1000),
        'version': '1.0.0'
    }), 200


@app.errorhandler(404)
def not_found(e):
    return api_response(False, error="Not found", status_code=404)


@app.errorhandler(429)
def rate_limit_exceeded(e):
    return api_response(False, error="Too many requests. Please slow down.", status_code=429)


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return api_response(False, error="Internal server error", status_code=500)


# ─────────────────────────────────────────────────────────────────────────────
# 🚀 Entry Point for Vercel
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🚀 Starting server on port {port} ({current_config.FLASK_ENV})")
    app.run(host='0.0.0.0', port=port, debug=current_config.DEBUG)
