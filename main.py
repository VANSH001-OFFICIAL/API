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
def home(): return "🔥 Spy Eye Bot is Live!", 200

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
DATA_FILE = "users_db.json"
API_KEY = "PAID_SELL12"
BASE_API_URL = "https://tg-user-id-to-number-m7hl.onrender.com"

# --- DATABASE ---
def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f: json.dump({"users": {}, "total_searches": 0}, f)
    try:
        with open(DATA_FILE, "r") as f: return json.load(f)
    except: return {"users": {}, "total_searches": 0}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=4)

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
    user = update.effective_user
    uid = str(user.id)
    db = load_data()

    if uid not in db["users"]:
        ref = context.args[0] if context.args and context.args[0].isdigit() else None
        if ref and ref != uid and ref in db["users"]:
            db["users"][ref]["points"] = db["users"][ref].get("points", 0) + 1
            db["users"][ref]["refer_count"] = db["users"][ref].get("refer_count", 0) + 1
            try: await context.bot.send_message(chat_id=int(ref), text=r"🎁 *Referral Alert!*" + "\n\nSomeone joined via your link. You earned *1 Point*.", parse_mode=ParseMode.MARKDOWN_V2)
            except: pass
        db["users"][uid] = {"points": 3, "referred_by": ref, "refer_count": 0}
        save_data(db)

    kb = ReplyKeyboardMarkup([
        [KeyboardButton("🔍 Get Number Details")],
        [KeyboardButton("💰 My Balance"), KeyboardButton("👥 Refer & Earn")]
    ], resize_keyboard=True)
    
    welcome_msg = (
        f"🚀 *Welcome to Spy Eye Bot {escape_md(user.first_name)}!*" + "\n\n"
        r"⚡ *The most powerful OSINT tool on Telegram.*" + "\n"
        r"━━━━━━━━━━━━━━━━━━━━━━━━" + "\n"
        f"👤 *Your Name:* `{escape_md(user.first_name)}` \n"
        f"🆔 *Your ID:* `{uid}`\n"
        r"━━━━━━━━━━━━━━━━━━━━━━━━" + "\n"
        r"👇 *Use the menu below to start searching database.*"
    )
    await update.message.reply_text(welcome_msg, reply_markup=kb, parse_mode=ParseMode.MARKDOWN_V2)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = update.message.text
    db = load_data()

    if text == "💰 My Balance":
        pts = db["users"].get(uid, {}).get("points", 0)
        msg = (f"💳 *ACCOUNT STATUS*\n\n"
               f"💰 *Available Balance:* `{pts} Points` \n"
               f"👤 *User ID:* `{uid}`\n\n"
               r"🎁 _Refer friends to earn more points for free!_")
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

    elif text == "👥 Refer & Earn":
        me = await context.bot.get_me()
        link = f"https://t.me/{me.username}?start={uid}"
        ref_count = db["users"].get(uid, {}).get("refer_count", 0)
        ref_msg = (f"👥 *REFERRAL DASHBOARD*\n\n"
                   f"📈 *Total Successful Refers:* `{ref_count}`\n"
                   r"🎁 *Reward:* `1 Point per valid refer`" + "\n\n"
                   r"🔗 *Your Unique Referral Link:*" + "\n"
                   f"`{escape_md(link)}`")
        await update.message.reply_text(ref_msg, parse_mode=ParseMode.MARKDOWN_V2)

    elif text == "🔍 Get Number Details":
        if not await is_joined(int(uid), context):
            btns = [
                [InlineKeyboardButton("📢 Join Channel 1", url=f"https://t.me/{CHANNELS[0][1:]}")],
                [InlineKeyboardButton("📢 Join Channel 2", url=f"https://t.me/{CHANNELS[1][1:]}")]
            ]
            return await update.message.reply_text(r"⚠️ *ACCESS DENIED!*" + "\n\nPlease join our official channels to use this search tool.", reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.MARKDOWN_V2)
        
        if db["users"].get(uid, {}).get("points", 0) < 3:
            return await update.message.reply_text(r"❌ *INSUFFICIENT BALANCE!*" + "\n\nYou need at least *3 Points* for one search. Refer friends to earn more.", parse_mode=ParseMode.MARKDOWN_V2)
        
        context.user_data['wait'] = True
        await update.message.reply_text(r"🔢 *DATABASE SEARCH*" + "\n\nPlease enter the *Telegram User ID* of the target to fetch details:", parse_mode=ParseMode.MARKDOWN_V2)

    elif context.user_data.get('wait'):
        target = text.strip()
        context.user_data['wait'] = False
        if target.isdigit() and int(target) in ADMIN_IDS:
            return await update.message.reply_text(r"🛡️ *SECURITY ALERT!*" + "\n\nThis ID is protected by our system and cannot be accessed.", parse_mode=ParseMode.MARKDOWN_V2)
        
        m = await update.message.reply_text(r"🛰️ *Connecting to database...*", parse_mode=ParseMode.MARKDOWN_V2)
        try:
            res = requests.get(f"{BASE_API_URL}/api/number={target}?api_key={API_KEY}", timeout=25).json()
            if "result" in res:
                db["users"][uid]["points"] -= 3
                db["total_searches"] = db.get("total_searches", 0) + 1
                save_data(db)
                await m.edit_text(f"✅ *MATCH FOUND!*" + f"\n\n👤 *Target ID:* `{target}`\n📞 *Phone Number:* `{res['result']['number']}`", parse_mode=ParseMode.MARKDOWN_V2)
            else: 
                await m.edit_text(r"❌ *DATA NOT FOUND*" + "\n\nNo records found for this ID in our leaked database.", parse_mode=ParseMode.MARKDOWN_V2)
        except: 
            await m.edit_text(r"⚠️ *SYSTEM ERROR!*" + "\n\nAPI is currently overloaded or down. Please try again after some time.", parse_mode=ParseMode.MARKDOWN_V2)

# --- ADMIN ---
async def admin_cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    cmd = update.message.text.split()
    db = load_data()
    
    if cmd[0] == "/stats":
        await update.message.reply_text(f"📊 *SYSTEM STATS*\n\n👥 *Total Users:* `{len(db['users'])}` \n🔎 *Total Searches:* `{db.get('total_searches',0)}`", parse_mode=ParseMode.MARKDOWN_V2)
    elif cmd[0] == "/addpts" and len(cmd) == 3:
        target, amt = cmd[1], int(cmd[2])
        if target in db["users"]:
            db["users"][target]["points"] += amt
            save_data(db)
            await update.message.reply_text(f"✅ Successfully added `{amt}` points to user `{target}`.", parse_mode=ParseMode.MARKDOWN_V2)
        else:
            await update.message.reply_text("❌ User ID not found in database.")

if __name__ == '__main__':
    keep_alive()
    bot = ApplicationBuilder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler(["stats", "addpts"], admin_cmds))
    bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    bot.run_polling(drop_pending_updates=True)
