"""
🗄️ Database Module - Firebase Realtime Database Operations
Handles all CRUD operations with proper error handling and data validation.
"""
import firebase_admin
from firebase_admin import credentials, db, auth
from datetime import datetime, timedelta
import hashlib
import secrets
from typing import Optional, Dict, List, Any
from config import current_config
import logging

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
def init_firebase():
    """Initialize Firebase Admin SDK with service account"""
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(current_config.FIREBASE_CONFIG)
            firebase_admin.initialize_app(cred, {
                'databaseURL': current_config.FRONTEND_FIREBASE['databaseURL']
            })
            logger.info("✅ Firebase Admin SDK initialized")
            return True
    except Exception as e:
        logger.error(f"❌ Firebase initialization failed: {e}")
        return False
    return True


class Database:
    """Firebase Realtime Database Operations"""
    
    def __init__(self):
        self.users_ref = db.reference('users')
        self.tasks_ref = db.reference('tasks')
        self.submissions_ref = db.reference('submissions')
        self.referrals_ref = db.reference('referrals')
        self.admin_ref = db.reference('admin')
        self.logs_ref = db.reference('logs')
    
    # ─────────────────────────────────────────────────────────────────────
    # 👤 User Operations
    # ─────────────────────────────────────────────────────────────────────
    
    def create_user(self, telegram_id: int, username: str, first_name: str, 
                   referral_code: Optional[str] = None) -> Dict[str, Any]:
        """Create new user with referral tracking"""
        timestamp = int(datetime.now().timestamp() * 1000)
        user_ref = self.users_ref.child(str(telegram_id))
        
        # Generate unique referral code
        my_referral_code = self._generate_referral_code(telegram_id)
        
        user_data = {
            'telegram_id': telegram_id,
            'username': username,
            'first_name': first_name,
            'referral_code': my_referral_code,
            'referred_by': referral_code,
            'points': 0,
            'pending_points': 0,
            'total_earned': 0,
            'total_withdrawn': 0,
            'tasks_completed': 0,
            'joined_at': timestamp,
            'last_active': timestamp,
            'is_banned': False,
            'ip_hash': None,  # Set via security module
            'device_fingerprint': None
        }
        
        user_ref.set(user_data)
        
        # Handle referral bonus
        if referral_code:
            self._process_referral(referral_code, telegram_id)
        
        logger.info(f"✅ User created: {telegram_id} | Referral: {my_referral_code}")
        return {**user_data, 'referral_link': f"{current_config.WEBAPP_URL}?ref={my_referral_code}"}
    
    def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user by Telegram ID"""
        user = self.users_ref.child(str(telegram_id)).get()
        return user if user else None
    
    def update_user(self, telegram_id: int, updates: Dict[str, Any]) -> bool:
        """Partial update of user data"""
        try:
            updates['last_active'] = int(datetime.now().timestamp() * 1000)
            self.users_ref.child(str(telegram_id)).update(updates)
            return True
        except Exception as e:
            logger.error(f"Update user failed: {e}")
            return False
    
    def add_points(self, telegram_id: int, points: int, 
                  transaction_type: str, description: str = '') -> bool:
        """Atomically add points with transaction history"""
        try:
            user_ref = self.users_ref.child(str(telegram_id))
            timestamp = int(datetime.now().timestamp() * 1000)
            
            # Use Firebase transaction for atomic update
            def transaction(current):
                if current is None:
                    return None  # User doesn't exist
                current['points'] = (current.get('points', 0) or 0) + points
                current['total_earned'] = (current.get('total_earned', 0) or 0) + points
                
                # Add to history
                history = current.get('history', {}) or {}
                history[f"{timestamp}_{secrets.token_hex(4)}"] = {
                    'points': points,
                    'type': transaction_type,
                    'description': description,
                    'timestamp': timestamp,
                    'balance_after': current['points']
                }
                current['history'] = history
                return current
            
            result = user_ref.transaction(transaction)
            return result is not None
        except Exception as e:
            logger.error(f"Add points failed: {e}")
            return False
    
    def _generate_referral_code(self, telegram_id: int) -> str:
        """Generate unique 8-char referral code"""
        base = hashlib.sha256(f"{telegram_id}{secrets.token_hex(8)}".encode()).hexdigest()[:8]
        # Ensure uniqueness
        code = base.upper()
        counter = 0
        while self.users_ref.order_by_child('referral_code').equal_to(code).get():
            code = (base + str(counter)).upper()[:8]
            counter += 1
        return code
    
    def _process_referral(self, referral_code: str, new_user_id: int):
        """Process referral bonus for referrer"""
        # Find referrer
        referrer = self.users_ref.order_by_child('referral_code').equal_to(referral_code).get()
        if referrer:
            referrer_id = list(referrer.keys())[0]
            # Add bonus to referrer
            self.add_points(
                int(referrer_id), 
                current_config.REFERRAL_BONUS,
                'referral_bonus',
                f"New user joined: {new_user_id}"
            )
            # Record referral
            self.referrals_ref.child(f"{referrer_id}/{new_user_id}").set({
                'joined_at': int(datetime.now().timestamp() * 1000),
                'bonus_awarded': current_config.REFERRAL_BONUS
            })
    
    # ─────────────────────────────────────────────────────────────────────
    # 📋 Task & Submission Operations
    # ─────────────────────────────────────────────────────────────────────
    
    def create_submission(self, telegram_id: int, task_type: str, 
                         screenshot_url: str, proof_text: str = '') -> str:
        """Create pending task submission"""
        submission_id = secrets.token_urlsafe(16)
        timestamp = int(datetime.now().timestamp() * 1000)
        
        submission_data = {
            'id': submission_id,
            'user_id': telegram_id,
            'task_type': task_type,  # youtube_sub, youtube_like, fb_follow, ig_follow, etc.
            'screenshot_url': screenshot_url,
            'proof_text': proof_text[:500],  # Limit length
            'status': 'pending',  # pending, approved, rejected
            'submitted_at': timestamp,
            'reviewed_at': None,
            'reviewed_by': None,
            'points_awarded': 0,
            'rejection_reason': None
        }
        
        self.submissions_ref.child(submission_id).set(submission_data)
        
        # Add to user's pending submissions
        self.users_ref.child(str(telegram_id)).child('pending_submissions').child(submission_id).set({
            'task_type': task_type,
            'submitted_at': timestamp
        })
        
        logger.info(f"📝 Submission created: {submission_id} | User: {telegram_id}")
        return submission_id
    
    def get_pending_submissions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get submissions pending admin review"""
        submissions = self.submissions_ref.order_by_child('status').equal_to('pending').limit_to_first(limit).get()
        if not submissions:
            return []
        
        result = []
        for sub_id, data in submissions.items():
            # Fetch user info for context
            user = self.get_user(data.get('user_id'))
            result.append({
                'id': sub_id,
                **data,
                'user_info': {
                    'username': user.get('username') if user else 'Unknown',
                    'first_name': user.get('first_name') if user else 'Unknown',
                    'current_points': user.get('points', 0) if user else 0
                } if user else None
            })
        return sorted(result, key=lambda x: x.get('submitted_at', 0), reverse=True)
    
    def review_submission(self, submission_id: str, admin_id: int, 
                         approved: bool, reason: str = None) -> bool:
        """Admin review: approve or reject submission"""
        try:
            submission = self.submissions_ref.child(submission_id).get()
            if not submission or submission.get('status') != 'pending':
                return False
            
            telegram_id = submission['user_id']
            timestamp = int(datetime.now().timestamp() * 1000)
            points = current_config.SOCIAL_POINTS if approved else 0
            
            # Update submission
            updates = {
                'status': 'approved' if approved else 'rejected',
                'reviewed_at': timestamp,
                'reviewed_by': admin_id,
                'points_awarded': points,
                'rejection_reason': reason if not approved else None
            }
            self.submissions_ref.child(submission_id).update(updates)
            
            if approved:
                # Award points to user
                self.add_points(telegram_id, points, 'task_approved', f"Submission: {submission_id}")
                # Update user stats
                self.users_ref.child(str(telegram_id)).update({
                    'tasks_completed': db.Increment(1),
                    'pending_submissions/{submission_id}': None  # Remove from pending
                })
            else:
                # Just remove from pending
                self.users_ref.child(str(telegram_id)).child('pending_submissions').child(submission_id).remove()
            
            # Log the action
            self.logs_ref.push().set({
                'action': 'submission_review',
                'admin_id': admin_id,
                'submission_id': submission_id,
                'user_id': telegram_id,
                'approved': approved,
                'reason': reason,
                'timestamp': timestamp
            })
            
            logger.info(f"🔍 Submission {submission_id} {'approved' if approved else 'rejected'} by admin {admin_id}")
            return True
        except Exception as e:
            logger.error(f"Review submission failed: {e}")
            return False
    
    # ─────────────────────────────────────────────────────────────────────
    # 📢 Admin Operations
    # ─────────────────────────────────────────────────────────────────────
    
    def broadcast_message(self, admin_id: int, message: str, 
                         target_users: Optional[List[int]] = None) -> Dict[str, int]:
        """Send broadcast/push notification to users"""
        if admin_id not in current_config.ADMIN_USER_IDS:
            return {'error': 'Unauthorized', 'sent': 0}
        
        timestamp = int(datetime.now().timestamp() * 1000)
        broadcast_id = secrets.token_urlsafe(12)
        
        # Record broadcast
        self.admin_ref.child('broadcasts').child(broadcast_id).set({
            'admin_id': admin_id,
            'message': message[:1000],
            'target_count': len(target_users) if target_users else 'all',
            'sent_at': timestamp,
            'delivery_status': {}
        })
        
        sent_count = 0
        users_to_notify = target_users or self._get_all_user_ids()
        
        for user_id in users_to_notify:
            try:
                # Add to user's notifications
                self.users_ref.child(str(user_id)).child('notifications').push().set({
                    'id': broadcast_id,
                    'message': message,
                    'read': False,
                    'sent_at': timestamp,
                    'type': 'broadcast'
                })
                sent_count += 1
            except:
                continue  # Skip failed deliveries
        
        return {'success': True, 'sent': sent_count, 'broadcast_id': broadcast_id}
    
    def _get_all_user_ids(self) -> List[int]:
        """Get all active user IDs (for broadcasts)"""
        users = self.users_ref.order_by_child('is_banned').equal_to(False).get()
        return [int(uid) for uid in users.keys()] if users else []
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Get platform-wide statistics"""
        users = self.users_ref.get() or {}
        submissions = self.submissions_ref.get() or {}
        
        total_users = len([u for u in users.values() if not u.get('is_banned', False)])
        total_points_distributed = sum(u.get('total_earned', 0) for u in users.values())
        pending_reviews = len([s for s in submissions.values() if s.get('status') == 'pending'])
        
        return {
            'total_users': total_users,
            'total_points_distributed': total_points_distributed,
            'total_usd_equivalent': total_points_distributed / current_config.POINTS_PER_DOLLAR,
            'pending_reviews': pending_reviews,
            'total_submissions': len(submissions),
            'approval_rate': self._calculate_approval_rate(submissions)
        }
    
    def _calculate_approval_rate(self, submissions: Dict) -> float:
        """Calculate submission approval percentage"""
        reviewed = [s for s in submissions.values() if s.get('status') in ['approved', 'rejected']]
        if not reviewed:
            return 0.0
        approved = len([s for s in reviewed if s.get('status') == 'approved'])
        return round((approved / len(reviewed)) * 100, 1)
    
    # ─────────────────────────────────────────────────────────────────────
    # 🔒 Security Helpers
    # ─────────────────────────────────────────────────────────────────────
    
    def record_user_access(self, telegram_id: int, ip_address: str, 
                          device_fingerprint: Optional[str] = None) -> Dict[str, bool]:
        """Track user access for anti-fraud detection"""
        if not current_config.ENABLE_IP_TRACKING:
            return {'allowed': True}
        
        ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()
        timestamp = int(datetime.now().timestamp() * 1000)
        
        # Check for multiple accounts on same IP
        existing_users = self.users_ref.order_by_child('ip_hash').equal_to(ip_hash).get()
        account_count = len(existing_users) if existing_users else 0
        
        # Allow if under limit or if it's the same user
        user = self.get_user(telegram_id)
        is_same_user = user and user.get('ip_hash') == ip_hash
        
        allowed = account_count < current_config.MAX_ACCOUNTS_PER_IP or is_same_user
        
        if allowed and user:
            # Update user's IP hash
            self.update_user(telegram_id, {
                'ip_hash': ip_hash,
                'device_fingerprint': device_fingerprint,
                'last_ip_access': timestamp
            })
        
        # Log access attempt
        self.logs_ref.push().set({
            'type': 'access_attempt',
            'user_id': telegram_id,
            'ip_hash': ip_hash,
            'device_fingerprint': device_fingerprint,
            'allowed': allowed,
            'account_count_on_ip': account_count,
            'timestamp': timestamp
        })
        
        return {
            'allowed': allowed,
            'account_count_on_ip': account_count,
            'max_allowed': current_config.MAX_ACCOUNTS_PER_IP
        }


# Global database instance
db_instance = None

def get_db() -> Database:
    """Get singleton database instance"""
    global db_instance
    if db_instance is None:
        if init_firebase():
            db_instance = Database()
        else:
            raise RuntimeError("Failed to initialize database")
    return db_instance
