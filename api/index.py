"""
🚀 Vercel Serverless Entry Point
Wraps Flask app for serverless deployment.
"""
from app import app as application

# Vercel expects 'app' or 'application' as the WSGI callable
app = application

# For local testing
if __name__ == '__main__':
    application.run(host='0.0.0.0', port=8080, debug=False)
