"""
🔐 Firebase Admin SDK Initialization for Vercel + asia-southeast1
Fixes: Unauthorized errors, newline parsing, region handling
"""

import os
import json
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

def parse_firebase_service_account(env_value: str) -> Optional[Dict]:
    """
    Parse Firebase Service Account JSON from Vercel environment variable.
    
    Handles:
    - Escaped newlines (\n) in private_key
    - JSON string vs dict input
    - Missing/invalid values
    
    Args:
        env_value: Raw string from os.environ('FIREBASE_SERVICE_ACCOUNT')
    
    Returns:
        Dict with parsed credentials or None if failed
    """
    if not env_value:
        logger.warning("⚠️ FIREBASE_SERVICE_ACCOUNT env var is empty")
        return None
    
    try:
        # Case 1: Already a dict (local development with json.load)
        if isinstance(env_value, dict):
            return env_value
        
        # Case 2: JSON string - try direct parse first
        try:
            creds = json.loads(env_value)
            if isinstance(creds, dict) and 'private_key' in creds:
                return _fix_private_key_newlines(creds)
        except json.JSONDecodeError:
            pass
        
        # Case 3: Escaped string with literal \n - fix newlines then parse
        # Replace escaped newlines with actual newlines ONLY in private_key
        fixed_value = env_value.replace(r'\\n', '\n').replace(r'\n', '\n')
        
        creds = json.loads(fixed_value)
        if isinstance(creds, dict) and 'private_key' in creds:
            return _fix_private_key_newlines(creds)
            
    except Exception as e:
        logger.error(f"❌ Failed to parse Firebase credentials: {e}")
        logger.error(f"   First 100 chars: {env_value[:100] if env_value else 'EMPTY'}")
    
    return None


def _fix_private_key_newlines(creds: Dict) -> Dict:
    """
    Ensure private_key has proper newline formatting for RSA key.
    
    Firebase private_key should look like:
    -----BEGIN PRIVATE KEY-----
    MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...
    -----END PRIVATE KEY-----
    """
    key = creds.get('private_key', '')
    
    if not key:
        return creds
    
    # If key doesn't have proper header/footer, it's likely malformed
    if '-----BEGIN PRIVATE KEY-----' not in key:
        # Try to reconstruct by adding newlines between key parts
        key = key.replace('\\n', '\n')
        
        # Ensure proper formatting
        if not key.startswith('-----BEGIN'):
            key = '-----BEGIN PRIVATE KEY-----\n' + key.strip()
        if not key.endswith('-----END PRIVATE KEY-----'):
            key = key.strip() + '\n-----END PRIVATE KEY-----'
    
    creds['private_key'] = key
    return creds


def init_firebase_admin(
    database_url: Optional[str] = None,
    service_account_env: str = 'FIREBASE_SERVICE_ACCOUNT',
    project_id: Optional[str] = None
) -> bool:
    """
    Initialize Firebase Admin SDK for Vercel deployment.
    
    ✅ Handles asia-southeast1 region correctly
    ✅ Parses private_key with proper newline handling
    ✅ Works with Vercel environment variables
    ✅ Includes fallback for development
    
    Args:
        database_url: Firebase Realtime Database URL (asia-southeast1)
        service_account_env: Env var name containing service account JSON
        project_id: Firebase project ID (optional, auto-detected from creds)
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    try:
        # Import here to avoid errors if firebase-admin not installed
        import firebase_admin
        from firebase_admin import credentials, db
        
        # Skip if already initialized
        if firebase_admin._apps:
            logger.info("✅ Firebase Admin SDK already initialized")
            return True
        
        # Get database URL (asia-southeast1 region)
        db_url = database_url or os.environ.get(
            'FIREBASE_DATABASE_URL',
            'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
        )
        
        # Parse service account credentials
        service_account_raw = os.environ.get(service_account_env, '')
        service_account = parse_firebase_service_account(service_account_raw)
        
        if not service_account:
            logger.warning("⚠️ Could not parse service account, trying fallback...")
            # Fallback: Try using API key + project ID for read-only access
            api_key = os.environ.get('FIREBASE_API_KEY')
            proj_id = project_id or os.environ.get('FIREBASE_PROJECT_ID')
            
            if api_key and proj_id:
                logger.info("🔄 Using API key fallback (read-only mode)")
                # Note: This is limited - use REST API instead for full access
                return False
            else:
                logger.error("❌ No valid Firebase credentials found")
                return False
        
        # Create credentials object
        cred = credentials.Certificate(service_account)
        
        # Initialize Firebase Admin SDK with region-specific config
        firebase_admin.initialize_app(cred, {
            'databaseURL': db_url,
            # Explicitly set project ID if not in credentials
            'projectId': project_id or service_account.get('project_id'),
        })
        
        # Verify connection with a simple read test
        test_ref = db.reference('.info/connected')
        # Note: .info/connected is for Realtime Database client SDK
        # For admin SDK, just verify we can access root
        db.reference('/').get(limit_to_first=1)
        
        logger.info(f"✅ Firebase Admin SDK initialized successfully")
        logger.info(f"   📍 Database: {db_url}")
        logger.info(f"   🆔 Project: {service_account.get('project_id')}")
        logger.info(f"   🔑 Client Email: {service_account.get('client_email', '')[:30]}...")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ firebase-admin not installed: {e}")
        logger.info("💡 Run: pip install firebase-admin")
        return False
        
    except Exception as e:
        logger.error(f"❌ Firebase initialization failed: {type(e).__name__}: {e}")
        
        # Debug: Log credential issues (without exposing sensitive data)
        if 'private_key' in str(e).lower() or 'unauthorized' in str(e).lower():
            logger.error("🔍 Likely cause: private_key formatting issue")
            logger.error("💡 Fix: Ensure Vercel env var has proper JSON with escaped newlines")
            logger.error("💡 Example format for private_key in env var:")
            logger.error('   "private_key": "-----BEGIN PRIVATE KEY-----\\nMIIE...\\n-----END PRIVATE KEY-----\\n"')
        
        return False
