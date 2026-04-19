import os
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template

# Flask ko batana padega ki templates folder root mein hai
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(__file__), '../templates'))

def init_firebase():
    if not firebase_admin._apps:
        try:
            # Environment variables se credentials uthana
            raw_key = os.getenv("FIREBASE_PRIVATE_KEY", "")
            p_key = raw_key.replace('\\n', '\n').strip('"').strip("'")
            c_email = os.getenv("FIREBASE_CLIENT_EMAIL")
            
            if p_key and c_email:
                cred = credentials.Certificate({
                    "type": "service_account",
                    "project_id": "ultimatemediasearch",
                    "private_key": p_key,
                    "client_email": c_email,
                    "token_uri": "https://oauth2.googleapis.com/token",
                })
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'
                })
        except Exception as e:
            print(f"Firebase Error: {e}")

@app.route('/')
def home():
    return "Bot is Live! 🚀"

@app.route('/dashboard')
def dashboard():
    uid = request.args.get('id', 'Guest')
    # Bot se name pass hoga, nahi toh 'Explorer' dikhega
    user_name = request.args.get('name', 'Explorer') 
    pts = 0
    ad_link = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"
    
    try:
        init_firebase()
        if firebase_admin._apps:
            u_data = db.reference(f'users/{uid}').get()
            if u_data:
                pts = u_data.get('pts', 0)
    except:
        pts = 0

    return render_template('dashboard.html', pts=pts, uid=uid, ad_link=ad_link, user_name=user_name)
