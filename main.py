import json, os, requests, urllib3, asyncio
from flask import Flask
from threading import Thread, Lock
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
db_lock = Lock()

# --- WEB SERVER (Render PING fix) ---
app = Flask('')
@app.route('/')
def home(): return "🤖 Bot is 100% Active!", 200

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- CONFIG ---
TOKEN = "8645433687:AAH_pMfMPzFviHKh3DDWxIZqDZNLs05UmCs"
ADMIN_IDS = [7117775366, 7259309072] 
CHANNELS = ["@verifiedpaisabots", "@RARE_API"]
DATA_FILE = "master_db.json"
API_KEY = "PAID_SELL12"
BASE_API_URL = "https://tg-user-id-to-number-m7hl.onrender.com"

# --- DATABASE ---
def load_data():
    with db_lock:
        if not os.path.exists(DATA_FILE):
            data = {"users": {}, "total_searches": 0}
            with open(DATA_FILE, "w") as f: json.dump(data, f)
            return data
        try:
            with open(DATA_FILE, "r") as f: return json.load(f)
        except: return {"users": {}, "total_searches": 0}

def save_data(data):
    with db_lock:
        try:
            with open(DATA_FILE, "w") as f: json.dump(data, f, indent=4)
        except Exception as e: print(f"Save Error: {e}")

# --- HELPERS ---
async def is_joined(user_id, context):
    try:
        for ch in CHANNELS:
            m = await context.bot.get_chat_member(chat_id=ch, user_id=user_id)
            if m.status in ["left", "kicked"]: return False
        return True
    except: return True 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['wait'] = False
    uid = str(update.effective_user.id)
    db = load_data()
    if uid not in db["users"]:
        db["users"][uid] = {"points": 3, "refer_count": 0}
        save_data(db)
    kb = ReplyKeyboardMarkup([[KeyboardButton("🔍 Get Number Details")], [KeyboardButton("💰 My Balance"), KeyboardButton("👥 Refer & Earn")]], resize_keyboard=True)
    await update.message.reply_text("🚀 *Bot Online\!*", reply_markup=kb, parse_mode=ParseMode.MARKDOWN_V2)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = update.message.text
    db = load_data()

    if text == "💰 My Balance":
        pts = db["users"].get(uid, {}).get("points", 0)
        await update.message.reply_text(f"💳 *Balance:* `{pts} Points`", parse_mode=ParseMode.MARKDOWN_V2)

    elif text == "🔍 Get Number Details":
        if not await is_joined(int(uid), context):
            return await update.message.reply_text("📢 *Join our channels first\!*")
        if db["users"].get(uid, {}).get("points", 0) < 3:
            return await update.message.reply_text("❌ *Need 3 Points\!*")
        context.user_data['wait'] = True
        await update.message.reply_text("🔢 *Send Telegram ID:*")

    elif context.user_data.get('wait'):
        target = text.strip()
        context.user_data['wait'] = False
        if not target.isdigit(): return
        
        m = await update.message.reply_text("🛰️ *Searching...*")
        try:
            # Added 20s timeout to prevent hanging
            res = requests.get(f"{BASE_API_URL}/api/number={target}?api_key={API_KEY}", timeout=20).json()
            if "result" in res:
                db["users"][uid]["points"] -= 3
                db["total_searches"] = db.get("total_searches", 0) + 1
                save_data(db)
                await m.edit_text(f"✅ *Found:* `{res['result']['number']}`")
            else: await m.edit_text("❌ *Not Found.*")
        except: await m.edit_text("⚠️ *Timeout/Error\!*")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    text = update.message.text
    db = load_data()
    if text.startswith("/addpts"):
        try:
            _, tid, amt = text.split()
            db["users"][tid]["points"] += int(amt)
            save_data(db)
            await update.message.reply_text(f"✅ Added {amt} to {tid}")
        except: pass
    elif text == "/stats":
        await update.message.reply_text(f"📊 *Users:* {len(db['users'])}\n🔎 *Searches:* {db.get('total_searches',0)}")

if __name__ == '__main__':
    Thread(target=run, daemon=True).start()
    bot = ApplicationBuilder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(MessageHandler(filters.COMMAND & filters.User(user_id=ADMIN_IDS), admin_panel))
    bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    
    # Conflict fix: Drop pending updates & Use a fresh connection
    bot.run_polling(drop_pending_updates=True, close_loop=False)
