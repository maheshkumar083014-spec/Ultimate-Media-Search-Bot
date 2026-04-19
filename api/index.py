@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    name = message.from_user.first_name

    dashboard_url = f"https://ultimate-media-search-bot-t7kj.vercel.app/dashboard?id={uid}&name={name}"

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("💎 Open Earning Dashboard", url=dashboard_url)
    )

    text = f"""
🔥 *Welcome {name}!* 🚀  

💰 *Start Your Online Earning Journey Today!*  

हर दिन बस 5-10 मिनट देकर आप यहाँ से पैसे कमा सकते हो 👇  

✨ Ads देखो → Points कमाओ  
✨ Social Tasks करो → Fast Earnings  
✨ Points को 💵 में Convert करो  

⚡ *100 Points = $1 Earn*  

🚀 जितना ज्यादा use करोगे उतना ज्यादा earn करोगे  

👉 *Success Tip:*  
Daily active users सबसे ज्यादा earn करते हैं  

👇 नीचे क्लिक करो और earning शुरू करो
"""

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown",
        reply_markup=markup
    )
