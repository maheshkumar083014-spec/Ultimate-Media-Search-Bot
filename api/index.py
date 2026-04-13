import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, db

# 1. Firebase Setup
# अपनी Firebase JSON फाइल का पाथ यहाँ डालें
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://your-project-id.firebaseio.com/'
})

# 2. Bot Setup
API_TOKEN = 'YOUR_BOT_TOKEN_HERE'
bot = telebot.TeleBot(API_TOKEN)

# --- Handlers ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    user_ref = db.reference(f'users/{user_id}')
    
    # यूजर अगर नया है तो डेटाबेस में ऐड करें
    if not user_ref.get():
        user_ref.set({
            'name': message.from_user.first_name,
            'points': 0,
            'referrals': 0
        })

    # Welcome Message के साथ Buttons (Inline Keyboard)
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_tasks = types.InlineKeyboardButton("🎯 Tasks", callback_data="tasks")
    btn_wallet = types.InlineKeyboardButton("💰 My Earnings", callback_data="wallet")
    btn_dash = types.InlineKeyboardButton("🌐 Open Dashboard", url="https://your-vercel-app.com")
    
    markup.add(btn_tasks, btn_wallet)
    markup.add(btn_dash)

    bot.reply_to(message, f"नमस्ते {message.from_user.first_name}! 👋\nहमारे Earn Bot में आपका स्वागत है। टास्क पूरे करें और पॉइंट्स कमाएं।", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data == "wallet":
        user_id = str(call.from_user.id)
        points = db.reference(f'users/{user_id}/points').get()
        bot.answer_callback_query(call.id, f"आपके पास {points} पॉइंट्स हैं।")

# बॉट को चालू रखना
bot.polling()
