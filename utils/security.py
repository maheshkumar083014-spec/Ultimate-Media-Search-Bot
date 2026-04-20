"""
🛡️ Security Module - Anti-Fraud & Rate Limiting
Protects bot from abuse, spam, and fraudulent activity.
"""
import hashlib
import time
from functools import wraps
from flask import request, jsonify, g
from collections import defaultdict, deque
from typing import Optional, Callable
from config import current_config
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for API endpoints"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = defaultdict(lambda: deque())
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if request is within rate limit"""
        now = time.time()
        window_start = now - self.window
        
        # Clean old requests
        while self.requests[identifier] and self.requests[identifier][0] < window_start:
            self.requests[identifier].popleft()
        
        # Check limit
        if len(self.requests[identifier]) >= self.max_requests:
            return False
        
        # Record this request
        self.requests[identifier].append(now)
        return True
    
    def get_retry_after(self, identifier: str) -> int:
        """Get seconds until next request allowed"""
        if not self.requests[identifier]:
            return 0
        oldest = self.requests[identifier][0]
        return max(0, int(oldest + self.window - time.time()) + 1)


# Global rate limiters
api_limiter = RateLimiter(
    current_config.RATE_LIMIT_REQUESTS, 
    current_config.RATE_LIMIT_WINDOW
)

submission_limiter = RateLimiter(5, 300)  # 5 submissions per 5 minutes


def generate_device_fingerprint(user_agent: str, ip: str, 
                               accept_headers: str = '') -> str:
    """Generate semi-unique device fingerprint (not cryptographically secure)"""
    fingerprint_data = f"{user_agent}|{ip}|{accept_headers}"
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]


def rate_limit(limiter: RateLimiter, key_func: Optional[Callable] = None):
    """Decorator for rate limiting Flask routes"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Determine rate limit key
            if key_func:
                key = key_func()
            else:
                # Default: IP + User-Agent
                key = f"{request.remote_addr}:{request.headers.get('User-Agent', '')}"
            
            if not limiter.is_allowed(key):
                retry_after = limiter.get_retry_after(key)
                logger.warning(f"⚠️ Rate limit exceeded: {key}")
                return jsonify({
                    'error': 'Too many requests',
                    'retry_after': retry_after
                }), 429
            
            return f(*args, **kwargs)
        return wrapped
    return decorator


def require_admin(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def wrapped(*args, **kwargs):
        admin_key = request.headers.get('X-Admin-Key') or request.args.get('admin_key')
        
        if not admin_key or admin_key != current_config.ADMIN_SECRET_KEY:
            logger.warning(f"🔐 Unauthorized admin access attempt from {request.remote_addr}")
            return jsonify({'error': 'Unauthorized'}), 401
        
        # Extract admin ID from token or header
        admin_id = request.headers.get('X-Admin-ID')
        if admin_id and admin_id.isdigit():
            g.admin_id = int(admin_id)
        
        return f(*args, **kwargs)
    return wrapped


def validate_user_session(telegram_id: Optional[int] = None):
    """Validate user session from headers or URL params"""
    if telegram_id:
        return telegram_id
    
    # Try to get from header
    user_id = request.headers.get('X-User-ID')
    if user_id and user_id.isdigit():
        return int(user_id)
    
    # Try to get from URL param (less secure, for TWA)
    user_id = request.args.get('user_id')
    if user_id and user_id.isdigit():
        return int(user_id)
    
    return None


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Sanitize user input to prevent XSS/injection"""
    import bleach
    if not text:
        return ''
    # Strip HTML tags, limit length
    cleaned = bleach.clean(str(text), tags=[], strip=True)
    return cleaned[:max_length].strip()


def is_valid_screenshot_url(url: str) -> bool:
    """Validate screenshot URL format and domain"""
    if not url or not url.startswith('https://'):
        return False
    
    # Allow common image hosting domains
    allowed_domains = [
        'i.ibb.co', 'imgur.com', 'postimg.cc', 'imgbb.com',
        'firebasestorage.googleapis.com', 'cdn.discordapp.com'
    ]
    
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    
    return any(domain.endswith(allowed) or domain == allowed for allowed in allowed_domains)


def check_fraud_patterns(telegram_id: int, ip_hash: str, 
                        device_fp: Optional[str] = None) -> Dict[str, bool]:
    """Check for suspicious activity patterns"""
    from database import get_db
    db = get_db()
    
    flags = {
        'multiple_accounts_same_ip': False,
        'rapid_submissions': False,
        'suspicious_device': False
    }
    
    user = db.get_user(telegram_id)
    if not user:
        return flags
    
    # Check IP clustering
    users_on_ip = db.users_ref.order_by_child('ip_hash').equal_to(ip_hash).get()
    if users_on_ip and len(users_on_ip) > current_config.MAX_ACCOUNTS_PER_IP:
        flags['multiple_accounts_same_ip'] = True
    
    # Check submission velocity (last hour)
    one_hour_ago = int(time.time() * 1000) - 3600000
    recent_subs = db.submissions_ref.order_by_child('user_id').equal_to(telegram_id).get()
    if recent_subs:
        recent_count = sum(1 for s in recent_subs.values() 
                         if s.get('submitted_at', 0) > one_hour_ago)
        if recent_count > 10:  # More than 10 submissions/hour is suspicious
            flags['rapid_submissions'] = True
    
    return flags
