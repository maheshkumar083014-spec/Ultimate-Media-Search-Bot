"""
🚀 Vercel Serverless Entry Point - FIXED
"""
import os
import sys
from flask import Flask, send_from_directory
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import main app
try:
    from app import app as application
except Exception as e:
    print(f"❌ Error importing app: {e}", file=sys.stderr)
    # Create fallback app
    application = Flask(__name__)
    
    @application.route('/')
    def fallback():
        return {
            "error": "App initialization failed",
            "details": str(e),
            "env_loaded": bool(os.getenv('BOT_TOKEN'))
        }, 500

# Add favicon route to prevent 404
@application.route('/favicon.ico')
def favicon():
    """Serve favicon or return 204 No Content"""
    try:
        return send_from_directory(
            os.path.join(application.root_path, 'static'),
            'favicon.ico',
            mimetype='image/vnd.microsoft.icon'
        )
    except:
        # Return empty 204 if favicon doesn't exist
        return '', 204

# Health check endpoint
@application.route('/health')
def health():
    return {
        "status": "healthy",
        "service": "telegram-earning-bot",
        "firebase_loaded": bool(os.getenv('FIREBASE_PROJECT_ID')),
        "bot_token_set": bool(os.getenv('BOT_TOKEN'))
    }, 200

# For Vercel
app = application

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    application.run(host='0.0.0.0', port=port, debug=False)
