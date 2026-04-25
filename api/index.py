import os, json, time, secrets, logging
import flask
from flask import Flask, request, render_template, redirect, url_for
import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, db
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
FIREBASE_DB_URL = os.environ.get("FIREBASE_DB_URL")
FIREBASE_SERVICE_ACCOUNT = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
WELCOME_IMAGE_URL = os.environ.get("WELCOME_IMAGE_URL")
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "change_me_strong_secret")
UPI_ID = os.environ.get("UPI_ID", "8543083014@mbk")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")
VERCEL_URL = os.environ.get("VERCEL_URL")

# ---------- Debug: peek at the variable ----------
if FIREBASE_SERVICE_ACCOUNT:
    logger.info(f"FIREBASE_SERVICE_ACCOUNT starts with: {FIREBASE_SERVICE_ACCOUNT[:30]}...")
else:
    logger.error("❌ FIREBASE_SERVICE_ACCOUNT is completely missing!")
    raise RuntimeError("FIREBASE_SERVICE_ACCOUNT not set.")

# ---------- Firebase init ----------
try:
    cred_json = json.loads(FIREBASE_SERVICE_ACCOUNT)
    cred = credentials.Certificate(cred_json)
    firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DB_URL})
    logger.info("Firebase initialized successfully.")
except Exception as e:
    logger.error(f"Firebase init failed. Variable content: {FIREBASE_SERVICE_ACCOUNT[:50]}")
    raise e

# ... rest of the code is identical to the full version I gave earlier
# (just copy the command/route handlers from any previous complete code)
