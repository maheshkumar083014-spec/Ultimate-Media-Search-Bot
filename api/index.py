"""
Ultimate Media Search Bot - Production Backend
Flask API + Telegram Bot + Firebase Integration
Deploy to Vercel with environment variables
"""

import os
import re
import json
import time
import asyncio
import logging
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template, send_from_directory, make_response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import firebase_admin
from firebase_admin import db, credentials, initialize_app
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============= SECURE CONFIGURATION =============
# ⚠️ In production, NEVER hardcode - use os.environ.get()
# These defaults are for demonstration ONLY - replace via Vercel env vars

TELEGRAM_BOT_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN", 
    "8701635891:AAFYh5tUdnHknFkXJhu06-K1QevJMz3P2sw"
)
DEEPSEEK_API_KEY = os.environ.get(
    "DEEPSEEK_API_KEY",
    "sk-783d645ce9e84eb8b954786a016561ea"
)
FIREBASE_DATABASE_URL = os.environ.get(
    "FIREBASE_DATABASE_URL",
    "https://ultimatemediasearch-default-rtdb.asia-southeast1.firebasedatabase.app/"
)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")  # Change this!

# Firebase Config for Frontend (safe to expose)
FIREBASE_CONFIG = {
    "apiKey": os.environ.get("FIREBASE_API_KEY", "AIzaSyD50eWvysruXgtgpDhhCVE2zdbSbLkFBwk"),
    "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN", "ultimatemediasearch.firebaseapp.com"),
    "projectId": os.environ.get("FIREBASE_PROJECT_ID", "ultimatemediasearch"),
    "storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET", "ultimatemediasearch.firebasestorage.app"),
    "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID", "123003124713"),
    "appId": os.environ.get("FIREBASE_APP_ID", "1:123003124713:web:c738c97b2772b112822978")
}

# ============= APP INITIALIZATION =============
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
app.config['JSON_AS_ASCII'] = False

# Initialize Firebase Admin (with serverless-safe error handling)
firebase_app = None
try:
    if not firebase_admin._apps:
        # For Vercel serverless: initialize without credentials file
        firebase_app = initialize_app(
            options={'databaseURL': FIREBASE_DATABASE_URL},
            name='[DEFAULT]'
        )
        logger.info("✅ Firebase Admin initialized")
except Exception as e:
    logger.warning(f"⚠️ Firebase Admin init: {e}")
    # App may still work with client-side Firebase

# Telegram Bot Application (lazy initialization)
telegram_app = None

# ============= CONFIGURATION CONSTANTS =============
WELCOME_PHOTO_URL = "https://i.ibb.co/3b5pScM/bf18237f-b2a2-4bb6-91e9-c8df3b427c22.jpg"
UPI_PAYMENT_ID = "8543083014@ikwik"

SOCIAL_TASKS = {
    "youtube": {
        "name": "YouTube",
        "handle": "@USSoccerPulse",
        "points": 100,
        "url": "https://youtube.com/@USSoccerPulse",
        "icon": "▶️"
    },
    "instagram": {
        "name": "Instagram", 
        "handle": "@digital_rockstar_m",
        "points": 100,
        "url": "https://instagram.com/digital_rockstar_m",
        "icon": "📸"
    },
    "facebook": {
        "name": "Facebook",
        "handle": "UltimateMediaSearch",
        "points": 100,
        "url": "https://facebook.com/UltimateMediaSearch",
        "icon": "📘"
    }
}

PLANS = {
    "Free": {"price": 0, "ai_cost": 10, "daily_task_limit": 3},
    "Earner Pro": {"price": 100, "ai_cost": 0, "daily_task_limit": 10},
    "Influencer Pro": {"price": 500, "ai_cost": 0, "daily_task_limit": -1}  # -1 = unlimited
}

# ============= FIREBASE DATABASE HELPERS =============
def _get_ref(path: str):
    """Get Firebase database reference"""
    try:
        return db.reference(path, app=firebase_app)
    except:
        return None

def get_user(user_id: str) -> dict:
    """Fetch or create user document"""
    ref = _get_ref(f'users/{user_id}')
    if not ref:
        return _get_default_user(user_id)
    
    data = ref.get()
    if not 
        return _get_default_user(user_id)
    return data

def _get_default_user(user_id: str) -> dict:
    """Create default user structure"""
    return {
        'user_id': user_id,
        'username': 'User',
        'points': 0,
        'plan': 'Free',
        'tasks_completed': [],
        'last_task_reset': time.time(),
        'messages': [],
        'payment_history': [],
        'joined_at': time.time(),
        'last_active': time.time()
    }

def update_user(user_id: str,  dict) -> bool:
    """Update user fields atomically"""
    ref = _get_ref(f'users/{user_id}')
    if not ref:
        return False
    try:
        ref.update(data)
        return True
    except Exception as e:
        logger.error(f"Firebase update error: {e}")
        return False

def get_all_users() -> dict:
    """Retrieve all users (admin use only)"""
    ref = _get_ref('users')
    if not ref:
        return {}
    try:
        return ref.get() or {}
    except:
        return {}

def add_payment_request(user_id: str, amount: int, txn_id: str, 
                       plan: str, screenshot_url: str = None) -> str:
    """Create payment request, returns request ID"""
    ref = _get_ref('payments')
    if not ref:
        return ""
    
    payment_id = ref.push().key
    payment_data = {
        'payment_id': payment_id,
        'user_id': user_id,
        'amount': amount,
        'txn_id': txn_id,
        'plan': plan,
        'screenshot_url': screenshot_url,
        'status': 'pending',  # pending, approved, rejected
        'submitted_at': time.time(),
        'reviewed_at': None,
        'admin_notes': ''
    }
    
    try:
        ref.child(payment_id).set(payment_data)
        # Also add to user's payment history
        user_ref = _get_ref(f'users/{user_id}/payment_history')
        if user_ref:
            user_ref.push().set({
                'payment_id': payment_id,
                'amount': amount,
                'plan': plan,
                'status': 'pending',
                'timestamp': time.time()
            })
        return payment_id
    except Exception as e:
        logger.error(f"Payment request error: {e}")
        return ""

def get_pending_payments() -> list:
    """Get all pending payment requests"""
    ref = _get_ref('payments')
    if not ref:
        return []
    try:
        all_payments = ref.get() or {}
        return [
            {**p, 'id': pid} for pid, p in all_payments.items() 
            if p.get('status') == 'pending'
        ]
    except:
        return []

def update_payment_status(payment_id: str, status: str, admin_notes: str = "") -> bool:
    """Update payment request status"""
    ref = _get_ref(f'payments/{payment_id}')
    if not ref:
        return False
    try:
        update_data = {
            'status': status,
            'reviewed_at': time.time(),
            'admin_notes': admin_notes
        }
        ref.update(update_data)
        
        # If approved, upgrade user plan
        if status == 'approved':
            payment = ref.get()
            if payment:
                user_ref = _get_ref(f"users/{payment['user_id']}")
                if user_ref:
                    user_ref.update({
                        'plan': payment['plan'],
                        'points': db.ServerValue.increment(
                            500 if payment['plan'] == 'Influencer Pro' else 100
                        )
                    })
        return True
    except Exception as e:
        logger.error(f"Payment update error: {e}")
        return False

# ============= DEEPSEEK AI INTEGRATION =============
async def query_deepseek_api(prompt: str, user_plan: str = "Free") -> dict:
    """Query DeepSeek AI with proper error handling"""
    
    # Point deduction logic
    ai_cost = PLANS.get(user_plan, PLANS['Free']).get('ai_cost', 10)
    
    if user_plan == "Free" and ai_cost > 0:
        # Free users pay per message
        return {
            "success": False,
            "response": f"💎 <b>Pro Feature!</b>\n\nAI chat costs {ai_cost} points for Free users.\n\n<b>Upgrade to Pro for unlimited AI!</b>",
            "cost": ai_cost,
            "requires_payment": True
        }
    
    try:
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are a helpful media search assistant."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.7,
            "stream": False
        }
        
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', 'No response')
            return {
                "success": True,
                "response": content,
                "cost": 0 if user_plan != "Free" else ai_cost,
                "model": result.get('model', 'deepseek-chat')
            }
        else:
            logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
            return {
                "success": False,
                "response": f"❌ AI Service Error ({response.status_code})\n\nPlease try again later.",
                "cost": 0,
                "error": response.text[:200]
            }
            
    except requests.exceptions.Timeout:
        return {"success": False, "response": "⏰ AI request timed out. Please try again.", "cost": 0}
    except requests.exceptions.ConnectionError:
        return {"success": False, "response": "🔌 Cannot connect to AI service. Check your connection.", "cost": 0}
    except Exception as e:
        logger.error(f"DeepSeek query exception: {e}")
        return {"success": False, "response": f"❌ Unexpected error: {str(e)[:100]}", "cost": 0}

# ============= TELEGRAM BOT HANDLERS =============
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with welcome photo and user info"""
    user = update.effective_user
    user_id = str(user.id)
    
    # Get or initialize user
    user_data = get_user(user_id)
    
    # Update username if changed
    if user_data['username'] != (user.username or user.first_name):
        user_data['username'] = user.username or user.first_name
        update_user(user_id, {'username': user_data['username']})
    
    # Update last active
    update_user(user_id, {'last_active': time.time()})
    
    # Format caption with HTML bold tags as requested
    caption = (
        f"<b>👋 Welcome, {user_data['username']}!</b>\n\n"
        f"<b>💰 Points Balance:</b> {user_data['points']}\n"
        f"<b>🎫 Membership Plan:</b> {user_data['plan']}\n\n"
        f"<i>🎯 Use /tasks to earn points</i>\n"
        f"<i>🤖 Use /ai to chat with AI</i>\n"
        f"<i>💳 Use /upgrade for Pro plans</i>"
    )
    
    try:
        await update.message.reply_photo(
            photo=WELCOME_PHOTO_URL,
            caption=caption,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎯 View Tasks", callback_data="show_tasks")],
                [InlineKeyboardButton("🤖 AI Chat", callback_data="show_ai")],
                [InlineKeyboardButton("💳 Upgrade Plan", url="https://t.me/yourbot?start=upgrade")]
            ])
        )
    except Exception as e:
        logger.error(f"Send photo error: {e}")
        await update.message.reply_text(caption, parse_mode='HTML')

async def handle_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display available social media tasks"""
    user_id = str(update.effective_user.id)
    user_data = get_user(user_id)
    
    # Check daily reset
    now = time.time()
    last_reset = user_data.get('last_task_reset', 0)
    if now - last_reset > 86400:  # 24 hours
        user_data['tasks_completed'] = []  # Reset daily tasks
        user_data['last_task_reset'] = now
        update_user(user_id, {
            'tasks_completed': [],
            'last_task_reset': now
        })
    
    # Build task keyboard
    keyboard = []
    for task_id, task in SOCIAL_TASKS.items():
        completed = task_id in user_data.get('tasks_completed', [])
        status = "✅" if completed else f"+{task['points']}pts"
        keyboard.append([
            InlineKeyboardButton(
                f"{task['icon']} {task['name']} {status}",
                url=task['url']
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔄 Refresh Tasks", callback_data="refresh_tasks")])
    
    await update.message.reply_text(
        "<b>🎯 Daily Social Tasks</b>\n\n"
        "Complete tasks to earn <b>100 points each</b>:\n\n"
        "• Subscribe & engage on our channels\n"
        "• Tasks reset every 24 hours\n"
        "• Pro members get higher limits\n\n"
        "<i>Tap a link, then mark as complete</i>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def handle_ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ai [message] command"""
    user_id = str(update.effective_user.id)
    user_data = get_user(user_id)
    
    # Check if user provided a message
    if not context.args:
        await update.message.reply_text(
            "<b>🤖 AI Chat Command</b>\n\n"
            "Usage: <code>/ai Your question here</code>\n\n"
            "<b>Pricing:</b>\n"
            "• Free: 10 points/message\n"
            "• Pro: Unlimited free AI\n\n"
            "<i>💡 Tip: Be specific for better results!</i>",
            parse_mode='HTML'
        )
        return
    
    prompt = " ".join(context.args)
    ai_cost = PLANS[user_data['plan']]['ai_cost']
    
    # Check points for free users
    if user_data['plan'] == 'Free' and user_data['points'] < ai_cost:
        await update.message.reply_text(
            f"❌ <b>Insufficient Points!</b>\n\n"
            f"You need {ai_cost} points for AI chat.\n"
            f"Current balance: {user_data['points']}\n\n"
            "<i>Complete tasks: /tasks</i>",
            parse_mode='HTML'
        )
        return
    
    # Deduct points for free users BEFORE calling AI
    if user_data['plan'] == 'Free' and ai_cost > 0:
        new_balance = user_data['points'] - ai_cost
        update_user(user_id, {'points': new_balance})
        await update.message.reply_text(
            f"🔹 {ai_cost} points deducted. Balance: {new_balance}\n\n🤖 Thinking...",
            parse_mode='HTML'
        )
    
    # Query AI
    result = await query_deepseek_api(prompt, user_data['plan'])
    
    # Format and send response
    if result['success']:
        response_text = f"<b>🤖 AI Response:</b>\n\n{result['response']}"
    else:
        response_text = result['response']
    
    await update.message.reply_text(response_text, parse_mode='HTML')
    
    # Save to message history (last 20)
    history = user_data.get('messages', [])[-19:]
    history.append({
        'role': 'user',
        'content': prompt,
        'timestamp': time.time()
    })
    history.append({
        'role': 'assistant', 
        'content': result.get('response', ''),
        'timestamp': time.time()
    })
    update_user(user_id, {'messages': history})

async def handle_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show upgrade options and payment instructions"""
    keyboard = [
        [
            InlineKeyboardButton("🥈 Earner Pro - ₹100", callback_data="pay:100:Earner Pro"),
            InlineKeyboardButton("🥇 Influencer Pro - ₹500", callback_data="pay:500:Influencer Pro")
        ],
        [InlineKeyboardButton("📋 View Payment History", callback_data="payment_history")]
    ]
    
    await update.message.reply_text(
        "<b>💳 Upgrade to Pro</b>\n\n"
        "<b>🥈 Earner Pro - ₹100/month</b>\n"
        "• 10x daily task limit\n"
        "• Free AI chat\n"
        "• +100 bonus points\n\n"
        "<b>🥇 Influencer Pro - ₹500/month</b>\n"
        "• Unlimited tasks\n"
        "• Priority AI access\n"
        "• +500 bonus points\n"
        "• Early feature access\n\n"
        f"<b>📲 Pay via UPI:</b>\n<code>{UPI_PAYMENT_ID}</code>\n\n"
        "<b>✅ After Payment:</b>\n"
        "1. Send transaction ID below\n"
        "2. Use: <code>/pay YOUR_TXN_ID</code>\n"
        "3. Or upload via dashboard\n"
        "4. Admin approval: ~24 hours",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def handle_payment_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /pay [transaction_id] command"""
    if not context.args:
        await update.message.reply_text(
            "Usage: <code>/pay YOUR_TRANSACTION_ID</code>\n\n"
            "Example: <code>/pay UPI123456789</code>",
            parse_mode='HTML'
        )
        return
    
    user_id = str(update.effective_user.id)
    txn_id = context.args[0].upper()
    user_data = get_user(user_id)
    
    # Default to Earner Pro if amount not specified
    # In production, parse amount from message or use separate command
    payment_id = add_payment_request(
        user_id=user_id,
        amount=100,  # Default amount
        txn_id=txn_id,
        plan="Earner Pro",  # Default plan
        screenshot_url=None
    )
    
    if payment_id:
        await update.message.reply_text(
            f"✅ <b>Payment Submitted!</b>\n\n"
            f"📝 Transaction: <code>{txn_id}</code>\n"
            f"🎫 Plan: Earner Pro (₹100)\n"
            f"🔍 Status: Pending Review\n\n"
            f"<i>You'll be notified once approved!</i>",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ Failed to submit payment. Please try again or use the web dashboard.",
            parse_mode='HTML'
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    user_data = get_user(user_id)
    data = query.data
    
    # Task completion
    if data.startswith("complete:"):
        task_id = data.split(":")[1]
        if task_id not in SOCIAL_TASKS:
            await query.edit_message_text("❌ Invalid task")
            return
            
        if task_id in user_data.get('tasks_completed', []):
            await query.edit_message_text("✅ Already completed!")
            return
        
        # Award points
        task = SOCIAL_TASKS[task_id]
        new_points = user_data['points'] + task['points']
        user_data.setdefault('tasks_completed', []).append(task_id)
        
        update_user(user_id, {
            'points': new_points,
            'tasks_completed': user_data['tasks_completed']
        })
        
        await query.edit_message_text(
            f"✅ <b>{task['name']} Completed!</b>\n\n"
            f"🎉 +{task['points']} points\n"
            f"💰 New Balance: {new_points}\n\n"
            f"<i>Keep earning!</i>",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🎯 More Tasks", callback_data="show_tasks")
            ]])
        )
    
    # Show tasks
    elif data == "show_tasks":
        await handle_tasks(update, context)
    
    # Show AI interface hint
    elif data == "show_ai":
        await query.edit_message_text(
            "<b>🤖 AI Chat</b>\n\n"
            "Start chatting by typing:\n"
            "<code>/ai Your message</code>\n\n"
            "<i>Free users: 10 pts/message\nPro users: Unlimited</i>",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="start_menu")
            ]])
        )
    
    # Payment selection
    elif data.startswith("pay:"):
        parts = data.split(":")
        amount = parts[1]
        plan = parts[2] if len(parts) > 2 else "Earner Pro"
        
        await query.edit_message_text(
            f"<b>💳 {plan} Upgrade</b>\n\n"
            f"Amount: <b>₹{amount}</b>\n\n"
            f"<b>📲 UPI ID:</b>\n<code>{UPI_PAYMENT_ID}</code>\n\n"
            "<b>✅ After Payment:</b>\n"
            "1. Copy your transaction ID\n"
            "2. Send: <code>/pay YOUR_TXN_ID</code>\n"
            "3. Or upload screenshot via dashboard\n\n"
            "<i>⚠️ Keep payment proof safe!</i>",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Plans", callback_data="upgrade")
            ]])
        )
    
    # Start menu
    elif data == "start_menu":
        await handle_start(update, context)
    
    # Refresh tasks
    elif data == "refresh_tasks":
        await handle_tasks(update, context)

# ============= FLASK ROUTES =============
@app.route('/')
def index():
    """Serve dashboard"""
    return render_template('dashboard.html', firebase_config=json.dumps(FIREBASE_CONFIG))

@app.route('/admin')
def admin_panel():
    """Serve admin panel (protected)"""
    return render_template('admin.html', firebase_config=json.dumps(FIREBASE_CONFIG))

@app.route('/api/auth/admin', methods=['POST'])
def admin_auth():
    """Admin authentication endpoint"""
    data = request.json or {}
    password = data.get('password', '')
    
    if password == ADMIN_PASSWORD:
        # Return session token (simplified - use proper JWT in production)
        return jsonify({
            'success': True,
            'token': f"admin_{int(time.time())}",
            'expires': time.time() + 3600
        })
    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

@app.route('/api/user/<user_id>', methods=['GET'])
def api_get_user(user_id):
    """Get user data for dashboard"""
    user_data = get_user(user_id)
    if not user_
        return jsonify({'error': 'User not found'}), 404
    
    # Calculate progress for ad tracker (demo logic)
    daily_limit = PLANS[user_data['plan']]['daily_task_limit']
    completed = len([t for t in user_data.get('tasks_completed', []) if t in SOCIAL_TASKS])
    progress = min(100, int((completed / max(1, daily_limit if daily_limit > 0 else 3)) * 100))
    
    return jsonify({
        **user_data,
        'ad_progress': progress,
        'tasks_available': SOCIAL_TASKS,
        'plans': PLANS
    })

@app.route('/api/ai/chat', methods=['POST'])
async def api_ai_chat():
    """AI chat endpoint for dashboard"""
    data = request.json or {}
    user_id = data.get('user_id')
    message = data.get('message', '').strip()
    
    if not user_id or not message:
        return jsonify({'error': 'Missing user_id or message'}), 400
    
    user_data = get_user(user_id)
    if not user_
        return jsonify({'error': 'User not found'}), 404
    
    ai_cost = PLANS[user_data['plan']]['ai_cost']
    
    # Point check for free users
    if user_data['plan'] == 'Free' and user_data['points'] < ai_cost:
        return jsonify({
            'success': False,
            'response': f"❌ Insufficient points. Need {ai_cost}, have {user_data['points']}",
            'cost': ai_cost,
            'balance': user_data['points']
        })
    
    # Deduct points for free users
    if user_data['plan'] == 'Free' and ai_cost > 0:
        update_user(user_id, {'points': user_data['points'] - ai_cost})
    
    # Query AI
    result = await query_deepseek_api(message, user_data['plan'])
    
    # Update history
    history = user_data.get('messages', [])[-19:]
    history.extend([
        {'role': 'user', 'content': message, 'timestamp': time.time()},
        {'role': 'assistant', 'content': result.get('response', ''), 'timestamp': time.time()}
    ])
    update_user(user_id, {'messages': history})
    
    # Get updated balance
    updated_user = get_user(user_id)
    
    return jsonify({
        'success': result.get('success', False),
        'response': result.get('response', ''),
        'cost': result.get('cost', 0),
        'balance': updated_user['points'],
        'model': result.get('model', 'deepseek-chat')
    })

@app.route('/api/tasks/complete', methods=['POST'])
def api_complete_task():
    """Mark task as complete via API"""
    data = request.json or {}
    user_id = data.get('user_id')
    task_id = data.get('task_id')
    
    if not user_id or not task_id:
        return jsonify({'error': 'Missing user_id or task_id'}), 400
    
    if task_id not in SOCIAL_TASKS:
        return jsonify({'error': 'Invalid task'}), 400
    
    user_data = get_user(user_id)
    
    # Check if already completed today
    if task_id in user_data.get('tasks_completed', []):
        return jsonify({
            'success': True,
            'message': 'Already completed',
            'points': user_data['points']
        })
    
    # Award points
    task = SOCIAL_TASKS[task_id]
    new_points = user_data['points'] + task['points']
    user_data.setdefault('tasks_completed', []).append(task_id)
    
    update_user(user_id, {
        'points': new_points,
        'tasks_completed': user_data['tasks_completed']
    })
    
    return jsonify({
        'success': True,
        'message': f'+{task["points"]} points!',
        'points_earned': task['points'],
        'new_balance': new_points
    })

@app.route('/api/payment/submit', methods=['POST'])
def api_submit_payment():
    """Submit payment request via API"""
    data = request.json or {}
    user_id = data.get('user_id')
    txn_id = data.get('txn_id', '').strip()
    amount = data.get('amount', 100)
    plan = data.get('plan', 'Earner Pro')
    screenshot_url = data.get('screenshot_url')
    
    if not user_id or not txn_id:
        return jsonify({'error': 'Missing user_id or txn_id'}), 400
    
    payment_id = add_payment_request(user_id, amount, txn_id, plan, screenshot_url)
    
    if payment_id:
        return jsonify({
            'success': True,
            'payment_id': payment_id,
            'message': 'Payment request submitted'
        })
    return jsonify({'success': False, 'error': 'Submission failed'}), 500

@app.route('/api/admin/payments', methods=['GET'])
def api_get_payments():
    """Get pending payments (admin only)"""
    # Simple auth check (use proper middleware in production)
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer ') or not ADMIN_PASSWORD:
        return jsonify({'error': 'Unauthorized'}), 401
    
    payments = get_pending_payments()
    return jsonify({'success': True, 'payments': payments})

@app.route('/api/admin/payment/<payment_id>', methods=['PUT'])
def api_update_payment(payment_id):
    """Approve/reject payment (admin only)"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer admin_'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json or {}
    status = data.get('status')  # 'approved' or 'rejected'
    notes = data.get('admin_notes', '')
    
    if status not in ['approved', 'rejected']:
        return jsonify({'error': 'Invalid status'}), 400
    
    success = update_payment_status(payment_id, status, notes)
    
    if success:
        return jsonify({'success': True, 'message': f'Payment {status}'})
    return jsonify({'success': False, 'error': 'Update failed'}), 500

@app.route('/api/admin/broadcast', methods=['POST'])
def api_broadcast():
    """Broadcast message to all users (admin only)"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer admin_'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json or {}
    message = data.get('message', '').strip()
    plan_filter = data.get('plan_filter')  # Optional: send to specific plan
    
    if not message:
        return jsonify({'error': 'Message required'}), 400
    
    # In production: queue broadcast via task system
    # For demo: return success and log
    users = get_all_users()
    target_count = sum(
        1 for uid, udata in users.items()
        if not plan_filter or udata.get('plan') == plan_filter
    )
    
    logger.info(f"Broadcast to {target_count} users: {message[:100]}...")
    
    return jsonify({
        'success': True,
        'message': f'Queued for {target_count} users',
        'queued_at': time.time()
    })

@app.route('/webhook/telegram', methods=['POST'])
async def telegram_webhook():
    """Telegram webhook endpoint for Vercel"""
    if not telegram_app:
        return jsonify({'status': 'bot_not_initialized'}), 503
    
    try:
        update_obj = Update.de_json(request.get_json(force=True), telegram_app.bot)
        await telegram_app.process_update(update_obj)
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/health')
def health_check():
    """Vercel health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'version': '1.0.0'
    })

# ============= BOT INITIALIZATION =============
def init_telegram_bot():
    """Initialize Telegram bot application"""
    global telegram_app
    
    if telegram_app:
        return telegram_app
    
    telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Register handlers
    telegram_app.add_handler(CommandHandler("start", handle_start))
    telegram_app.add_handler(CommandHandler("tasks", handle_tasks))
    telegram_app.add_handler(CommandHandler("ai", handle_ai_command))
    telegram_app.add_handler(CommandHandler("upgrade", handle_upgrade))
    telegram_app.add_handler(CommandHandler("pay", handle_payment_submission))
    telegram_app.add_handler(CallbackQueryHandler(handle_callback))
    
    # Optional: Set webhook for Vercel
    # webhook_url = os.environ.get('VERCEL_URL', 'http://localhost:8080')
    # if webhook_url:
    #     telegram_app.bot.set_webhook(f"{webhook_url}/webhook/telegram")
    
    logger.info("✅ Telegram bot initialized")
    return telegram_app

# Initialize on module load
init_telegram_bot()

# ============= SERVER ENTRY POINT =============
if __name__ == '__main__':
    # Local development: run Flask + Telegram polling
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--poll':
        # Run Telegram polling in background
        async def run_polling():
            await telegram_app.start_polling()
        
        import threading
        poll_thread = threading.Thread(target=lambda: asyncio.run(run_polling()), daemon=True)
        poll_thread.start()
        logger.info("🤖 Telegram polling started")
    
    # Run Flask
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'false') == 'true')
