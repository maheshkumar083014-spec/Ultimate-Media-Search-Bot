"""
📸 Screenshot Verification Utilities
Handles image validation, storage, and metadata extraction.
"""
import re
import hashlib
from datetime import datetime
from typing import Optional, Dict, Tuple
from PIL import Image
import io
import requests
from config import current_config
import logging

logger = logging.getLogger(__name__)


def validate_screenshot_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate screenshot URL: format, size, content-type
    Returns: (is_valid, error_message)
    """
    if not url:
        return False, "No URL provided"
    
    # Check URL format
    if not re.match(r'^https?://.+\.+(jpg|jpeg|png|webp)(\?.*)?$', url, re.I):
        return False, "Invalid image URL format"
    
    # Check file size via HEAD request
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        content_length = response.headers.get('Content-Length')
        
        if content_length:
            size_mb = int(content_length) / (1024 * 1024)
            if size_mb > current_config.MAX_SCREENSHOT_SIZE_MB:
                return False, f"Image too large: {size_mb:.1f}MB (max: {current_config.MAX_SCREENSHOT_SIZE_MB}MB)"
        
        # Check content type
        content_type = response.headers.get('Content-Type', '')
        if 'image' not in content_type.lower():
            return False, f"Invalid content type: {content_type}"
            
    except requests.RequestException as e:
        logger.warning(f"Could not validate screenshot URL: {e}")
        # Don't fail hard - allow if we can't verify
    
    return True, None


def extract_image_metadata(url: str) -> Optional[Dict[str, any]]:
    """Extract basic metadata from image URL (dimensions, format)"""
    try:
        response = requests.get(url, timeout=15, stream=True)
        response.raise_for_status()
        
        # Read first part of image for metadata
        img_data = io.BytesIO()
        for chunk in response.iter_content(chunk_size=8192):
            img_data.write(chunk)
            if len(img_data.getvalue()) > 64 * 1024:  # 64KB should be enough for metadata
                break
        
        img_data.seek(0)
        with Image.open(img_data) as img:
            return {
                'format': img.format,
                'width': img.width,
                'height': img.height,
                'mode': img.mode,
                'aspect_ratio': round(img.width / img.height, 2) if img.height > 0 else 0
            }
    except Exception as e:
        logger.debug(f"Could not extract image metadata: {e}")
        return None


def generate_screenshot_hash(url: str, user_id: int, task_type: str) -> str:
    """Generate unique hash for screenshot to detect duplicates"""
    data = f"{url}:{user_id}:{task_type}:{datetime.now().date()}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def check_duplicate_submission(user_id: int, task_type: str, 
                            screenshot_hash: str, hours: int = 24) -> bool:
    """Check if similar submission exists in last N hours"""
    from database import get_db
    db = get_db()
    
    cutoff = int(datetime.now().timestamp() * 1000) - (hours * 3600 * 1000)
    
    # Query recent submissions by this user for this task type
    recent = db.submissions_ref.order_by_child('user_id').equal_to(user_id).get()
    
    if not recent:
        return False
    
    for sub_id, sub in recent.items():
        if (sub.get('task_type') == task_type and 
            sub.get('submitted_at', 0) > cutoff and
            sub.get('status') != 'rejected'):
            # Could add hash comparison here if storing hashes
            return True
    
    return False


def get_task_requirements(task_type: str) -> Dict[str, str]:
    """Get verification requirements for each task type"""
    requirements = {
        'youtube_subscribe': {
            'title': 'YouTube Subscribe',
            'instruction': 'Subscribe to our channel and screenshot the "Subscribed" button',
            'expected_elements': ['Subscribed button', 'Channel name visible', 'Bell icon (optional)'],
            'proof_text_hint': 'Paste your YouTube username (optional)'
        },
        'youtube_like': {
            'title': 'YouTube Like',
            'instruction': 'Like our latest video and screenshot the liked state',
            'expected_elements': ['Thumbs up filled', 'Video title visible', 'Like count'],
            'proof_text_hint': 'Video title or URL'
        },
        'facebook_follow': {
            'title': 'Facebook Follow',
            'instruction': 'Follow our page and screenshot your following status',
            'expected_elements': ['Following/Liked button', 'Page name visible', 'Your profile icon'],
            'proof_text_hint': 'Your Facebook name'
        },
        'instagram_follow': {
            'title': 'Instagram Follow',
            'instruction': 'Follow our Instagram and screenshot the following state',
            'expected_elements': ['Following button', 'Username @digital_rockstar_m', 'Post grid visible'],
            'proof_text_hint': 'Your Instagram username'
        }
    }
    return requirements.get(task_type, requirements['youtube_subscribe'])
