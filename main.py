import json, os, requests, urllib3, asyncio, time
from flask import Flask
from threading import Thread, Lock
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
db_lock = Lock()

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "🤖 Spy Eye Master is 100% Active!", 200

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

Thread(target=run, daemon=True).start()

# --- CONFIG ---
TOKEN = "8645433687:AAH_pMfMPzFviHKh3DDWxIZqDZNLs05UmCs"
ADMIN_IDS = [7117775366, 7259309072] 
CHANNELS = ["@verifiedpaisabots", "@RARE_API"]
DATA_FILE = "master_db.json" # Nayi file for fresh start
API_KEY = "PAID_SELL12"
BASE_API_URL = "https://tg-user-id-to-number-m7hl.onrender.com"

# --- DATABASE HANDLER ---
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
        except Exception as e: print(f"DB Save Error: {e}")

def escape_md(text):
    return "".join(f"\\{c}" if c in r"_*[]()~`>#+-=|{}.!" else c for c in str(text))

# --- JOIN CHECK ---
async def is_joined(user_id, context):
    try:
        for ch in CHANNELS:
            m = await context.bot.get_chat_member(chat_id=ch, user_id=user_id)
            if m.status in ["left", "kicked"]: return False
        return True
    except: return True 

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['wait'] = False
    uid = str(update.effective_user.id)
    db = load_data()

    if uid not in db["users"]:
        ref = context.args[0] if context.args and context.args[0].isdigit() else None
        if ref and ref in db["users"] and ref != uid:
            db["users"][ref]["points"] = db["users"][ref].get("points", 0) + 1
            db["users"][ref]["refer_count"] = db["users"][ref].get("refer_count", 0) + 1
            try: await context.bot.send_message(chat_id=int(ref), text="🎁 *Referral Alert!* You earned 1 point.")
            except: pass
        db["users"][uid] = {"points": 3, "refer_count": 0}
        save_data(db)

    kb = ReplyKeyboardMarkup([[KeyboardButton("🔍 Get Number Details")], [KeyboardButton("💰 My Balance"), KeyboardButton("👥 Refer & Earn")]], resize_keyboard=True)
    await update.message.reply_text(f"🚀 *Spy Eye Master Online\!*\nUse the menu to start\.", reply_markup=kb, parse_mode=ParseMode.MARKDOWN_V2)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = update.message.text
    db = load_data()

    if text == "💰 My Balance":
        pts = db["users"].get(uid, {}).get("points", 0)
        await update.message.reply_text(f"💳 *Balance:* `{pts} Points`", parse_mode=ParseMode.MARKDOWN_V2)

    elif text == "👥 Refer & Earn":
        bot_info = await context.bot.get_me()
        link = f"https://t.me/{bot_info.username}?start={uid}"
        await update.message.reply_text(f"🔗 *Your Link:* `{escape_md(link)}`", parse_mode=ParseMode.MARKDOWN_V2)

    elif text == "🔍 Get Number Details":
        if not await is_joined(int(uid), context):
            btns = [[InlineKeyboardButton("Join Channel 1", url=f"https://t.me/{CHANNELS[0][1:]}")], [InlineKeyboardButton("Join Channel 2", url=f"https://t.me/{CHANNELS[1][1:]}")]]
            return await update.message.reply_text("⚠️ *Join channels first\!*", reply_markup=InlineKeyboardMarkup(btns))
        
        if db["users"].get(uid, {}).get("points", 0) < 3:
            return await update.message.reply_text("❌ *Need 3 Points\!*")
        
        context.user_data['wait'] = True
        await update.message.reply_text("🔢 *Send Telegram ID to Search:*")

    elif context.user_data.get('wait'):
        target = text.strip()
        context.user_data['wait'] = False
        if not target.isdigit(): return
        
        # Admin Protection
        if int(target) in ADMIN_IDS:
            return await update.message.reply_text("🛡️ *ID Protected\!*")

        m = await update.message.reply_text("🛰️ *Searching Database...*")
        
        # API Search with Timeout
        try:
            loop = asyncio.get_event_loop()
            # 20 second timeout for API response
            response = await loop.run_in_executor(None, lambda: requests.get(f"{BASE_API_URL}/api/number={target}?api_key={API_KEY}", timeout=20, verify=False))
            res = response.json()
            
            if "result" in res:
                db["users"][uid]["points"] -= 3
                db["total_searches"] = db.get("total_searches", 0) + 1
                save_data(db)
                await m.edit_text(f"✅ *Found:* `{res['result']['number']}`")
            else:
                await m.edit_text("❌ *No Data Found.*")
        except requests.exceptions.Timeout:
            await m.edit_text("⚠️ *Timeout\!* API is taking too long. Try again later.")
        except Exception as e:
            await m.edit_text("⚠️ *Error\!* Something went wrong.")

# --- ADMIN COMMANDS ---
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
            else: await update.message.reply_text("User not in DB.")
        except: await update.message.reply_text("Use: `/addpts ID AMT`")

    elif text == "/stats":
        await update.message.reply_text(f"📊 *Users:* {len(db['users'])}\n🔎 *Searches:* {db.get('total_searches',0)}")

    elif text.startswith("/broadcast"):
        msg = text.replace("/broadcast", "").strip()
        if not msg: return await update.message.reply_text("Send message after command.")
        sent, fail = 0, 0
        for user in db["users"]:
            try:
                await context.bot.send_message(chat_id=int(user), text=f"📢 *Announcement*\n\n{msg}", parse_mode=ParseMode.MARKDOWN_V2)
                sent += 1
                await asyncio.sleep(0.05)
            except: fail += 1
        await update.message.reply_text(f"✅ Sent: {sent}, Fail: {fail}")

if __name__ == '__main__':
    bot = ApplicationBuilder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(MessageHandler(filters.COMMAND & filters.User(user_id=ADMIN_IDS), admin_panel))
    bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    bot.run_polling(drop_pending_updates=True)
