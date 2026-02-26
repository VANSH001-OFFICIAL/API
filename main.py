# SAARE FEATURES ISME HAIN: PROTECT, CHANNELS, REFER, ADDPTS, BROADCAST
import json, os, requests, urllib3, asyncio
from flask import Flask
from threading import Thread, Lock
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
db_lock = Lock()

app = Flask('')
@app.route('/')
def home(): return "🤖 Bot is 100% Active!", 200

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- CONFIG ---
TOKEN = "8645433687:AAH_pMfMPzFviHKh3DDWxIZqDZNLs05UmCs"
ADMIN_IDS = [7117775366, 7259309072, 1180177016] 
CHANNELS = ["@verifiedpaisabots", "@RARE_API"] 
DATA_FILE = "master_db.json"
API_KEY = "PAID_SELL12"
BASE_API_URL = "https://tg-user-id-to-number-m7hl.onrender.com"

# --- DB HANDLER ---
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

def escape_md(text):
    return "".join(f"\\{c}" if c in r"_*[]()~`>#+-=|{}.!" else c for c in str(text))

async def is_joined(user_id, context):
    try:
        for ch in CHANNELS:
            m = await context.bot.get_chat_member(chat_id=ch, user_id=user_id)
            if m.status in ["left", "kicked"]: return False
        return True
    except: return True 

# --- CORE LOGIC ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['wait'] = False
    uid = str(update.effective_user.id)
    db = load_data()
    if uid not in db["users"]:
        ref = context.args[0] if context.args and context.args[0].isdigit() else None
        if ref and ref in db["users"] and ref != uid:
            db["users"][ref]["points"] = db["users"][ref].get("points", 0) + 1
            try: await context.bot.send_message(chat_id=int(ref), text="🎁 *Referral Bonus!* You earned +1 Point.")
            except: pass
        db["users"][uid] = {"points": 3, "refer_count": 0}
        save_data(db)
    
    kb = ReplyKeyboardMarkup([[KeyboardButton("🔍 Get Number Details")], [KeyboardButton("💰 My Balance"), KeyboardButton("👥 Refer & Earn")]], resize_keyboard=True)
    # Fixed Warning: Using raw string or escaping properly
    await update.message.reply_text(r"🚀 *Spy Eye Master Online!*" + "\nUse the menu below to start.", reply_markup=kb, parse_mode=ParseMode.MARKDOWN_V2)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = update.message.text
    db = load_data()

    if text == "💰 My Balance":
        pts = db["users"].get(uid, {}).get("points", 0)
        await update.message.reply_text(f"💳 *Your Balance:* `{pts} Points`", parse_mode=ParseMode.MARKDOWN_V2)

    elif text == "👥 Refer & Earn":
        b = await context.bot.get_me()
        link = f"https://t.me/{b.username}?start={uid}"
        await update.message.reply_text(f"🔗 *Referral Link:* \n`{escape_md(link)}`", parse_mode=ParseMode.MARKDOWN_V2)

    elif text == "🔍 Get Number Details":
        if not await is_joined(int(uid), context):
            btns = [[InlineKeyboardButton("📢 Join Channel 1", url=f"https://t.me/{CHANNELS[0][1:]}")], [InlineKeyboardButton("📢 Join Channel 2", url=f"https://t.me/{CHANNELS[1][1:]}")]]
            return await update.message.reply_text(r"⚠️ *Join our channels first!*", reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.MARKDOWN_V2)
        if db["users"].get(uid, {}).get("points", 0) < 3:
            return await update.message.reply_text(r"❌ *Need 3 Points!*", parse_mode=ParseMode.MARKDOWN_V2)
        context.user_data['wait'] = True
        await update.message.reply_text(r"🔢 *Send Target Telegram ID:*", parse_mode=ParseMode.MARKDOWN_V2)

    elif context.user_data.get('wait'):
        target = text.strip()
        context.user_data['wait'] = False
        if not target.isdigit(): return
        
        # PROTECTION FEATURE
        if int(target) in ADMIN_IDS:
            return await update.message.reply_text(r"🛡️ *ID Protected!*", parse_mode=ParseMode.MARKDOWN_V2)

        m = await update.message.reply_text(r"🛰️ *Searching Database...*", parse_mode=ParseMode.MARKDOWN_V2)
        try:
            # 20s Timeout added as requested
            res = requests.get(f"{BASE_API_URL}/api/number={target}?api_key={API_KEY}", timeout=20).json()
            if "result" in res:
                db["users"][uid]["points"] -= 3
                db["total_searches"] = db.get("total_searches", 0) + 1
                save_data(db)
                await m.edit_text(f"✅ *Found:* `{escape_md(res['result']['number'])}`", parse_mode=ParseMode.MARKDOWN_V2)
            else: await m.edit_text(r"❌ *No Data Found.*", parse_mode=ParseMode.MARKDOWN_V2)
        except requests.exceptions.Timeout:
            await m.edit_text(r"⚠️ *Search Timeout!* API is busy.", parse_mode=ParseMode.MARKDOWN_V2)
        except: 
            await m.edit_text(r"⚠️ *System Error!* Try again.", parse_mode=ParseMode.MARKDOWN_V2)

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
                await update.message.reply_text(f"✅ Added {amt} to {tid}")
            else: await update.message.reply_text("User ID not found.")
        except: pass
    elif text == "/stats":
        await update.message.reply_text(f"📊 *Users:* {len(db['users'])} | *Searches:* {db.get('total_searches',0)}")
    elif text.startswith("/broadcast"):
        msg = text.replace("/broadcast", "").strip()
        if not msg: return
        sent = 0
        for u in db["users"]:
            try: 
                await context.bot.send_message(chat_id=int(u), text=f"📢 *ANNOUNCEMENT*\n\n{msg}", parse_mode=ParseMode.MARKDOWN_V2)
                sent += 1
                await asyncio.sleep(0.05)
            except: pass
        await update.message.reply_text(f"✅ Broadcast Sent to {sent} users.")

if __name__ == '__main__':
    Thread(target=run, daemon=True).start()
    bot = ApplicationBuilder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(MessageHandler(filters.COMMAND & filters.User(user_id=ADMIN_IDS), admin_panel))
    bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    
    print("🚀 Bot Started with 0 Warnings!")
    bot.run_polling(drop_pending_updates=True)
