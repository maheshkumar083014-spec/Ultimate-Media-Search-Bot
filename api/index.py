import os, firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, render_template

app = Flask(__name__)

# Firebase ko safe tarike se init karne ke liye
def init_firebase():
    if not firebase_admin._apps:
        try:
            p_key = os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n').strip('"')
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": "ultimatemediasearch",
                "private_key": p_key,
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "token_uri": "https://oauth2.googleapis.com/token",
            })
            firebase_admin.initialize_app(cred, {'databaseURL': 'https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/'})
        except Exception as e:
            print(f"Firebase Error: {e}")

@app.route('/')
def home():
    return "Bot status: Running"

@app.route('/dashboard')
def dashboard():
    init_firebase()
    uid = request.args.get('id', 'Unknown')
    try:
        # User ka data fetch karna
        u_data = db.reference(f'users/{uid}').get() or {"pts": 0}
        pts = u_data.get('pts', 0)
    except:
        pts = 0 # Agar database connect na ho toh zero dikhaye
        
    ad_link = "https://horizontallyresearchpolar.com/r0wbx3kyf?key=8b0a2298684c7cea730312add326101b"
    return render_template('dashboard.html', pts=pts, uid=uid, ad_link=ad_link)
