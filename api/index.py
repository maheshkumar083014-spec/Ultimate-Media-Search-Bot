@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    
    # ✅ Create/Update user in Firestore
    user_ref = db.collection('users').document(str(user_id))
    user_doc = user_ref.get()
    
    if not user_doc.exists:
        user_ref.set({
            'userId': str(user_id),
            'name': name,
            'username': message.from_user.username or '',
            'balance': 0,
            'adsViewed': 0,
            'totalEarned': 0,
            'joinedAt': firestore.SERVER_TIMESTAMP,
            'lastActive': firestore.SERVER_TIMESTAMP,
            'isBanned': False
        })
    else:
        user_ref.update({'lastActive': firestore.SERVER_TIMESTAMP, 'name': name})
    
    # 🖼️ Welcome Photo URL (As per your requirement)
    photo_url = "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg"
    
    # 🔘 Inline Button with Dashboard URL
    markup = types.InlineKeyboardMarkup()
    dashboard_url = f"https://ultimate-media-search-bot-t7kj.vercel.app/dashboard?id={user_id}&name={name}"
    btn = types.InlineKeyboardButton("Open Dashboard 🚀", url=dashboard_url)
    markup.add(btn)
    
    # 📝 Professional Welcome Caption
    caption = (
        f"👋 <b>Welcome, {name}!</b>\n\n"
        "🎯 <b>Ultimate Media Search Bot</b>\n\n"
        "✨ Earn money by completing simple tasks:\n"
        "• View Ads: +25 points\n"
        "• Social Tasks: +100 points\n"
        "• Daily Rewards available!\n\n"
        "💰 <b>Withdrawal:</b> $1 = 100 points\n\n"
        "🚀 Click below to start earning!"
    )
    
    # 📤 Send Photo + Caption + Button
    bot.send_photo(message.chat.id, photo_url, caption=caption, reply_markup=markup)
