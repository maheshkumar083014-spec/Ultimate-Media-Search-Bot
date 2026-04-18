import os, firebase_admin, logging
from firebase_admin import credentials, db
from flask import Flask, request, render_template

app = Flask(__name__)

# Logs enable karein taki error Vercel Dashboard mein dikhe
logging.basicConfig(level=logging.INFO)

def init_firebase():
    if not firebase_admin._apps:
        try:
            # Check variables
            p_key = os.getenv("FIREBASE_PRIVATE_KEY")
            client_email = os.getenv("FIREBASE_CLIENT_EMAIL")
            
            if not p_key or not client_email:
                logging.error("Environment Variables missing!")
                return False

            p_key = p_key.replace('\\n', '\n').strip('"').strip("'")
            
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": "ultimatemediasearch",
                "private_key": p_key,
                "client_email": client_email,
                "token_uri": "https://oauth2.googleapis.com/token",
            })
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
            })
            return True
        except Exception as e:
            logging.error(f"Firebase Init Failed: {e}")
            return False
    return True

@app.route('/')
def home():
    return "Bot is Active and Connected to Telegram!"

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', 'Unknown')
    pts = 0
    if init_firebase():
        try:
            u_data = db.reference(f'users/{uid}').get()
            if u_data:
                pts = u_data.get('pts', 0)
        except Exception as e:
            logging.error(f"Database Read Error: {e}")
    
    # Dashboard render karein bhale hi database fail ho jaye (500 error se bachne ke liye)
    ad_link = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"
    return render_template('dashboard.html', pts=pts, uid=uid, ad_link=ad_link)
