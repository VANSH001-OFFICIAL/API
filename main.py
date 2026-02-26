import json, os, requests, urllib3, asyncio
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "🔥 Spy Eye Bot is 100% Active!", 200

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- CONFIG ---
TOKEN = "8645433687:AAH_pMfMPzFviHKh3DDWxIZqDZNLs05UmCs"
ADMIN_IDS = [7117775366, 7259309072] 
CHANNELS = ["@verifiedpaisabots", "@RARE_API"]
DATA_FILE = "database.json" # Name changed to force new file creation
API_KEY = "PAID_SELL12"
BASE_API_URL = "https://tg-user-id-to-number-m7hl.onrender.com"

# --- DATABASE LOGIC (REPAIRED) ---
def load_data():
    default_data = {"users": {}, "total_searches": 0}
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump(default_data, f)
        return default_data
    try:
        with open(DATA_FILE, "r") as f:
            content = f.read()
            if not content: return default_data
            return json.loads(content)
    except (json.JSONDecodeError, Exception):
        # Agar file corrupt ho jaye toh nayi banaye
        with open(DATA_FILE, "w") as f:
            json.dump(default_data, f)
        return default_data

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving data: {e}")

def escape_md(text):
    return "".join(f"\\{c}" if c in r"_*[]()~`>#+-=|{}.!" else c for c in str(text))

# --- HELPERS ---
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
    user = update.effective_user
    uid = str(user.id)
    db = load_data()

    if uid not in db["users"]:
        ref = context.args[0] if context.args and context.args[0].isdigit() else None
        if ref and ref != uid and ref in db["users"]:
            db["users"][ref]["points"] = db["users"][ref].get("points", 0) + 1
            db["users"][ref]["refer_count"] = db["users"][ref].get("refer_count", 0) + 1
            try: await context.bot.send_message(chat_id=int(ref), text=r"🎁 *Referral Bonus!* Someone joined via your link. +1 Point.", parse_mode=ParseMode.MARKDOWN_V2)
            except: pass
        db["users"][uid] = {"points": 3, "referred_by": ref, "refer_count": 0}
        save_data(db)

    kb = ReplyKeyboardMarkup([[KeyboardButton("🔍 Get Number Details")], [KeyboardButton("💰 My Balance"), KeyboardButton("👥 Refer & Earn")]], resize_keyboard=True)
    await update.message.reply_text(f"🚀 *Welcome {escape_md(user.first_name)}!*\nUse the menu below to start searching.", reply_markup=kb, parse_mode=ParseMode.MARKDOWN_V2)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = update.message.text
    db = load_data()

    if text == "💰 My Balance":
        pts = db["users"].get(uid, {}).get("points", 0)
        await update.message.reply_text(f"💳 *Balance:* `{pts} Points`", parse_mode=ParseMode.MARKDOWN_V2)

    elif text == "👥 Refer & Earn":
        me = await context.bot.get_me()
        link = f"https://t.me/{me.username}?start={uid}"
        await update.message.reply_text(f"🔗 *Your Link:* `{escape_md(link)}`", parse_mode=ParseMode.MARKDOWN_V2)

    elif text == "🔍 Get Number Details":
        if not await is_joined(int(uid), context):
            btns = [[InlineKeyboardButton("📢 Channel 1", url=f"https://t.me/{CHANNELS[0][1:]}")], [InlineKeyboardButton("📢 Channel 2", url=f"https://t.me/{CHANNELS[1][1:]}")]]
            return await update.message.reply_text(r"⚠️ *Join channels first!*", reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.MARKDOWN_V2)
        context.user_data['wait'] = True
        await update.message.reply_text(r"🔢 *Send Telegram ID:*", parse_mode=ParseMode.MARKDOWN_V2)

    elif context.user_data.get('wait'):
        target = text.strip()
        context.user_data['wait'] = False
        if not target.isdigit(): return
        
        m = await update.message.reply_text(r"🛰️ *Searching...*", parse_mode=ParseMode.MARKDOWN_V2)
        try:
            res = requests.get(f"{BASE_API_URL}/api/number={target}?api_key={API_KEY}", timeout=25).json()
            if "result" in res:
                db["users"][uid]["points"] = db["users"][uid].get("points", 3) - 3
                db["total_searches"] = db.get("total_searches", 0) + 1
                save_data(db)
                await m.edit_text(f"✅ *Found:* `{res['result']['number']}`", parse_mode=ParseMode.MARKDOWN_V2)
            else: await m.edit_text(r"❌ *No Data Found.*", parse_mode=ParseMode.MARKDOWN_V2)
        except: await m.edit_text(r"⚠️ *API Error!*", parse_mode=ParseMode.MARKDOWN_V2)

async def admin_cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    cmd = update.message.text.split()
    db = load_data()
    
    if cmd[0] == "/stats":
        await update.message.reply_text(f"📊 *Users:* `{len(db['users'])}` \n🔎 *Searches:* `{db.get('total_searches',0)}`", parse_mode=ParseMode.MARKDOWN_V2)
    elif cmd[0] == "/addpts" and len(cmd) == 3:
        target, amt = cmd[1], int(cmd[2])
        if target in db["users"]:
            db["users"][target]["points"] += amt
            save_data(db)
            await update.message.reply_text(f"✅ Added points to `{target}`.")
        else: await update.message.reply_text("❌ User not in DB.")

if __name__ == '__main__':
    keep_alive()
    bot = ApplicationBuilder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler(["stats", "addpts"], admin_cmds))
    bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    bot.run_polling(drop_pending_updates=True)
