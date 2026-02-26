import json, os, requests, urllib3, asyncio
from flask import Flask
from threading import Thread, Lock
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

# Warnings and DB Lock
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
db_lock = Lock()

# --- WEB SERVER (For Render) ---
app = Flask('')
@app.route('/')
def home(): return "🤖 Spy Eye Master is Online!", 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- CONFIG ---
TOKEN = "8645433687:AAH_pMfMPzFviHKh3DDWxIZqDZNLs05UmCs"
ADMIN_IDS = [7117775366, 7259309072] 
CHANNELS = ["@verifiedpaisabots", "@RARE_API"] 
DATA_FILE = "final_db.json" # New file to avoid old corruption
API_KEY = "PAID_SELL12"
BASE_API_URL = "https://tg-user-id-to-number-m7hl.onrender.com"

# --- DATABASE HANDLER ---
def load_data():
    with db_lock:
        if not os.path.exists(DATA_FILE):
            d = {"users": {}, "total_searches": 0}
            with open(DATA_FILE, "w") as f: json.dump(d, f)
            return d
        try:
            with open(DATA_FILE, "r") as f: return json.load(f)
        except: return {"users": {}, "total_searches": 0}

def save_data(data):
    with db_lock:
        try:
            with open(DATA_FILE, "w") as f: json.dump(data, f, indent=4)
        except: pass

# --- JOIN CHECK (WITH BYPASS) ---
async def is_joined(user_id, context):
    try:
        for ch in CHANNELS:
            member = await context.bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status in ["left", "kicked"]: return False
        return True
    except: return True # Bypass on error

# --- BOT LOGIC ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    db = load_data()
    
    if uid not in db["users"]:
        # REFERRAL SYSTEM
        ref = context.args[0] if context.args and context.args[0].isdigit() else None
        if ref and ref in db["users"] and ref != uid:
            db["users"][ref]["points"] = db["users"][ref].get("points", 0) + 1
            try: await context.bot.send_message(chat_id=int(ref), text="🎁 <b>Referral Bonus!</b> Someone joined via your link. +1 Point.")
            except: pass
        db["users"][uid] = {"points": 3, "refer_count": 0}
        save_data(db)
    
    kb = ReplyKeyboardMarkup([[KeyboardButton("🔍 Get Number Details")], [KeyboardButton("💰 My Balance"), KeyboardButton("👥 Refer & Earn")]], resize_keyboard=True)
    await update.message.reply_text("🚀 <b>Spy Eye Master Online!</b>\nUse menu below to start.", reply_markup=kb, parse_mode=ParseMode.HTML)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = update.message.text
    db = load_data()

    if text == "💰 My Balance":
        pts = db["users"].get(uid, {}).get("points", 0)
        await update.message.reply_text(f"💳 <b>Balance:</b> <code>{pts} Points</code>", parse_mode=ParseMode.HTML)

    elif text == "👥 Refer & Earn":
        bot_me = await context.bot.get_me()
        link = f"https://t.me/{bot_me.username}?start={uid}"
        await update.message.reply_text(f"🔗 <b>Your Invite Link:</b>\n<code>{link}</code>", parse_mode=ParseMode.HTML)

    elif text == "🔍 Get Number Details":
        if not await is_joined(int(uid), context):
            btns = [[InlineKeyboardButton("Join Channel 1", url=f"https://t.me/{CHANNELS[0][1:]}")], [InlineKeyboardButton("Join Channel 2", url=f"https://t.me/{CHANNELS[1][1:]}")]]
            return await update.message.reply_text("⚠️ <b>Join Channels First!</b>", reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.HTML)
        
        if db["users"].get(uid, {}).get("points", 0) < 3:
            return await update.message.reply_text("❌ <b>Insufficient Balance!</b> Need 3 points per search.", parse_mode=ParseMode.HTML)
        
        context.user_data['wait'] = True
        await update.message.reply_text("🔢 <b>Send the Telegram User ID to search:</b>", parse_mode=ParseMode.HTML)

    elif context.user_data.get('wait'):
        target = text.strip()
        context.user_data['wait'] = False
        if not target.isdigit(): return
        
        # ADMIN PROTECTION
        if int(target) in ADMIN_IDS:
            return await update.message.reply_text("🛡️ <b>This ID is Protected!</b>", parse_mode=ParseMode.HTML)

        m = await update.message.reply_text("🛰️ <b>Searching Database... Please Wait.</b>", parse_mode=ParseMode.HTML)
        try:
            # 20s Timeout
            res = requests.get(f"{BASE_API_URL}/api/number={target}?api_key={API_KEY}", timeout=20).json()
            if "result" in res:
                db["users"][uid]["points"] -= 3
                db["total_searches"] = db.get("total_searches", 0) + 1
                save_data(db)
                await m.edit_text(f"✅ <b>Found:</b> <code>{res['result']['number']}</code>", parse_mode=ParseMode.HTML)
            else:
                await m.edit_text("❌ <b>No records found in database.</b>", parse_mode=ParseMode.HTML)
        except:
            await m.edit_text("⚠️ <b>API Timeout!</b> Server busy, try again later.", parse_mode=ParseMode.HTML)

# --- ADMIN PANEL ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    text = update.message.text
    db = load_data()
    
    if text.startswith("/addpts"):
        try:
            _, tid, amt = text.split()
            if tid in db["users"]:
                db["users"][tid]["points"] += int(amt)
                save_data(db)
                await update.message.reply_text(f"✅ Points added to {tid}")
            else: await update.message.reply_text("User not found.")
        except: pass
    elif text == "/stats":
        await update.message.reply_text(f"📊 <b>Total Users:</b> {len(db['users'])}\n🔎 <b>Total Searches:</b> {db.get('total_searches',0)}", parse_mode=ParseMode.HTML)
    elif text.startswith("/broadcast"):
        msg = text.replace("/broadcast", "").strip()
        for u in db["users"]:
            try: await context.bot.send_message(chat_id=int(u), text=f"📢 <b>Announcement:</b>\n\n{msg}", parse_mode=ParseMode.HTML)
            except: pass
        await update.message.reply_text("✅ Broadcast Sent.")

if __name__ == '__main__':
    # Start Web Server
    Thread(target=run_web, daemon=True).start()
    
    # Start Bot
    bot = ApplicationBuilder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(MessageHandler(filters.COMMAND & filters.User(user_id=ADMIN_IDS), admin_panel))
    bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    
    # Drop pending updates and run
    bot.run_polling(drop_pending_updates=True)
