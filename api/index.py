import os
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template, send_from_directory

app = Flask(__name__)

def init_firebase():
    if not firebase_admin._apps:
        try:
            p_key = os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n').strip('"').strip("'")
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": "ultimatemediasearch",
                "private_key": p_key,
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "token_uri": "https://oauth2.googleapis.com/token",
            })
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
            })
        except Exception as e:
            print(f"Firebase Init Error: {e}")

@app.route('/favicon.ico')
def favicon():
    return '', 204  # Favicon ka error khatam karne ke liye

@app.route('/')
def home():
    return "Bot is Live!"

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', 'Guest')
    pts = 0
    ad_link = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"
    
    try:
        init_firebase()
        u_data = db.reference(f'users/{uid}').get()
        if u_data:
            pts = u_data.get('pts', 0)
    except:
        pts = 0

    return render_template('dashboard.html', pts=pts, uid=uid, ad_link=ad_link)
