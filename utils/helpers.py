"""
🔧 Helper Utilities - Common functions across the application
"""
import re
import json
from datetime import datetime
from typing import Any, Optional
from flask import jsonify
import logging

logger = logging.getLogger(__name__)


def api_response(success: bool, data: Any = None, error: str = None, 
               status_code: int = 200) -> tuple:
    """Standardized API response formatter"""
    response = {
        'success': success,
        'timestamp': int(datetime.now().timestamp() * 1000)
    }
    
    if data is not None:
        response['data'] = data
    if error:
        response['error'] = error
    
    return jsonify(response), status_code


def format_points(points: int, include_currency: bool = True) -> str:
    """Format points with optional USD conversion"""
    from config import current_config
    if include_currency:
        usd = points / current_config.POINTS_PER_DOLLAR
        return f"{points:,} pts (${usd:.2f})"
    return f"{points:,}"


def is_valid_telegram_id(value: Any) -> bool:
    """Validate Telegram user ID format"""
    try:
        tid = int(value)
        return tid > 0 and tid < 2**40  # Telegram IDs are positive integers
    except (ValueError, TypeError):
        return False


def mask_sensitive_data(data: dict, fields: list = None) -> dict:
    """Mask sensitive fields in data for logging"""
    if fields is None:
        fields = ['token', 'password', 'secret', 'key', 'private']
    
    masked = data.copy()
    for key in masked:
        if any(f in key.lower() for f in fields):
            if isinstance(masked[key], str) and len(masked[key]) > 4:
                masked[key] = masked[key][:2] + '*' * (len(masked[key]) - 4) + masked[key][-2:]
            else:
                masked[key] = '[REDACTED]'
    return masked


def parse_referral_link(url: str) -> Optional[str]:
    """Extract referral code from app URL"""
    from urllib.parse import urlparse, parse_qs
    from config import current_config
    
    if not url.startswith(current_config.WEBAPP_URL):
        return None
    
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    
    return params.get('ref', [None])[0]


def generate_web_app_url(telegram_id: int, username: str, 
                        referral_code: Optional[str] = None) -> str:
    """Generate authenticated Web App URL for Telegram"""
    from config import current_config
    import urllib.parse
    
    base_url = f"{current_config.WEBAPP_URL}/dashboard"
    params = {
        'id': telegram_id,
        'name': username,
        'ts': int(datetime.now().timestamp())
    }
    
    if referral_code:
        params['ref'] = referral_code
    
    # Simple signature (in production, use HMAC with bot token)
    query = urllib.parse.urlencode(params)
    return f"{base_url}?{query}"


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to integer"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """Truncate text with ellipsis"""
    if not text or len(text) <= max_length:
        return text or ''
    return text[:max_length - len(suffix)].rstrip() + suffix


def log_action(action: str, user_id: Optional[int] = None, 
              details: dict = None, level: str = 'info'):
    """Standardized logging for actions"""
    log_entry = {
        'action': action,
        'user_id': user_id,
        'timestamp': datetime.now().isoformat(),
        ** (details or {})
    }
    
    logger.log(getattr(logging, level.upper(), logging.INFO), 
              json.dumps(mask_sensitive_data(log_entry)))
