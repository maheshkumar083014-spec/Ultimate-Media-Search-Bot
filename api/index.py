@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    try:
        # Check variables first
        db_url = os.environ.get('FIREBASE_DB_URL')
        service_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
        
        if not db_url or not service_json:
            bot.send_message(message.chat.id, "❌ Error: Vercel settings mein variables missing hain!")
            return

        user_ref = db.reference(f'users/{user_id}').get()
        if not user_ref:
            db.reference(f'users/{user_id}').set({
                "username": message.from_user.username or "User",
                "points": 0,
                "status": "free"
            })
        
        bot.send_message(message.chat.id, "✅ Connection Success! Aapka bot kaam kar raha hai.")
    except Exception as e:
        # Ye line aapko batayegi ki asli problem kya hai
        bot.send_message(message.chat.id, f"⚠️ Debug Error: {str(e)}")
