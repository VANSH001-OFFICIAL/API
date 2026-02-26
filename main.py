import json, os, requests, urllib3, asyncio
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
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
DATA_FILE = "users_db.json"
API_KEY = "PAID_SELL12"

# --- DATABASE ---
def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f: json.dump({"users": {}, "protected_ids": ADMIN_IDS, "total_searches": 0}, f)
    try:
        with open(DATA_FILE, "r") as f: return json.load(f)
    except: return {"users": {}, "protected_ids": ADMIN_IDS, "total_searches": 0}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=4)

def escape_md(text):
    return "".join(f"\\{c}" if c in r"_*[]()~`>#+-=|{}.!" else c for c in str(text))

# --- HELPERS ---
async def is_joined(user_id, context):
    for ch in CHANNELS:
        try:
            m = await context.bot.get_chat_member(chat_id=ch, user_id=user_id)
            if m.status in ["left", "kicked"]: return False
        except: return False
    return True

# --- ADMIN COMMANDS ---
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    db = load_data()
    msg = f"📊 *SYSTEM STATS*\n\n👥 *Total Users:* `{len(db['users'])}`" + f"\n🔎 *Total Searches:* `{db.get('total_searches', 0)}`"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

async def add_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    try:
        target_id = context.args[0]
        amount = int(context.args[1])
        db = load_data()
        if target_id in db["users"]:
            db["users"][target_id]["points"] += amount
            save_data(db)
            await update.message.reply_text(f"✅ Points Updated! New Balance: `{db['users'][target_id]['points']}`", parse_mode=ParseMode.MARKDOWN_V2)
            try: await context.bot.send_message(chat_id=int(target_id), text=f"🎁 *Admin Credit!* \n\nAdmin has added *{amount} Points* to your account.", parse_mode=ParseMode.MARKDOWN_V2)
            except: pass
        else: await update.message.reply_text("❌ User ID not found.")
    except: await update.message.reply_text("💡 Usage: `/addpts <ID> <AMOUNT>`")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    if not context.args:
        return await update.message.reply_text("💡 Usage: `/broadcast Your message here`")
    
    msg_to_send = " ".join(context.args)
    db = load_data()
    users = db["users"].keys()
    
    sent = 0
    failed = 0
    progress = await update.message.reply_text(f"📢 *Broadcasting to {len(users)} users...*", parse_mode=ParseMode.MARKDOWN_V2)

    for user_id in users:
        try:
            await context.bot.send_message(chat_id=int(user_id), text=f"📢 *BROADCAST*\n\n{msg_to_send}", parse_mode=ParseMode.MARKDOWN_V2)
            sent += 1
            await asyncio.sleep(0.05) # Rate limit protection
        except:
            failed += 1
    
    await progress.edit_text(f"✅ *Broadcast Finished!*\n\n🚀 *Sent:* `{sent}`\n❌ *Failed:* `{failed}`", parse_mode=ParseMode.MARKDOWN_V2)

# --- USER COMMANDS ---
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

    if not await is_joined(user.id, context):
        btns = [[InlineKeyboardButton("📢 Join Channel 1", url=f"https://t.me/{CHANNELS[0][1:]}")],
                [InlineKeyboardButton("📢 Join Channel 2", url=f"https://t.me/{CHANNELS[1][1:]}")],
                [InlineKeyboardButton("✅ Verify & Start Bot", callback_data="verify")]]
        return await update.message.reply_text(f"🚀 *Welcome to Spy Eye Bot!*", reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.MARKDOWN_V2)

    pts = db["users"].get(uid, {}).get("points", 0)
    kb = ReplyKeyboardMarkup([[KeyboardButton("🔍 Get Number Details")], [KeyboardButton(f"💰 Balance: {pts} Pts")], [KeyboardButton("👥 Refer & Earn")]], resize_keyboard=True)
    await update.message.reply_text(f"✅ *Access Granted!*", reply_markup=kb, parse_mode=ParseMode.MARKDOWN_V2)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = update.message.text
    db = load_data()

    if not await is_joined(update.effective_user.id, context): return

    if "💰 Balance" in text:
        pts = db["users"].get(uid, {}).get("points", 0)
        kb = ReplyKeyboardMarkup([[KeyboardButton("🔍 Get Number Details")], [KeyboardButton(f"💰 Balance: {pts} Pts")], [KeyboardButton("👥 Refer & Earn")]], resize_keyboard=True)
        await update.message.reply_text(f"💳 *Available Balance:* `{pts} Pts`", reply_markup=kb, parse_mode=ParseMode.MARKDOWN_V2)

    elif text == "👥 Refer & Earn":
        me = await context.bot.get_me()
        link = f"https://t.me/{me.username}?start={uid}"
        msg = f"👥 *Refers:* `{db['users'].get(uid, {}).get('refer_count', 0)}`" + f"\n🔗 *Link:* `{escape_md(link)}`"
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

    elif text == "🔍 Get Number Details":
        if db["users"].get(uid, {}).get("points", 0) < 3:
            return await update.message.reply_text(r"❌ *Need 3 Points!*", parse_mode=ParseMode.MARKDOWN_V2)
        context.user_data['wait'] = True
        await update.message.reply_text(r"🔢 *Send Target Telegram ID:*", parse_mode=ParseMode.MARKDOWN_V2)

    elif context.user_data.get('wait'):
        target = text.strip()
        context.user_data['wait'] = False
        if target.isdigit() and int(target) in ADMIN_IDS:
            return await update.message.reply_text(r"🛡️ *ID Protected!*", parse_mode=ParseMode.MARKDOWN_V2)
        
        m = await update.message.reply_text(r"🛰️ *Searching...*", parse_mode=ParseMode.MARKDOWN_V2)
        try:
            res = requests.get(f"https://tg-user-id-to-number-m7hl.onrender.com/api/number={target}?api_key={API_KEY}", timeout=35, verify=False).json()
            if "result" in res and "number" in res["result"]:
                db["users"][uid]["points"] -= 3
                db["total_searches"] = db.get("total_searches", 0) + 1
                save_data(db)
                await m.edit_text(f"✅ *Found:* `{escape_md(res['result']['number'])}`", parse_mode=ParseMode.MARKDOWN_V2)
            else: await m.edit_text(r"❌ *No Data Found*", parse_mode=ParseMode.MARKDOWN_V2)
        except: await m.edit_text(r"⚠️ *API Error!*", parse_mode=ParseMode.MARKDOWN_V2)

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.data == "verify":
        if await is_joined(update.effective_user.id, context):
            await update.callback_query.answer("✅ Verified!")
            await update.callback_query.message.delete()
            await start(update, context)
        else: await update.callback_query.answer("❌ Join channels first!", show_alert=True)

if __name__ == '__main__':
    keep_alive()
    bot = ApplicationBuilder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("stats", admin_stats))
    bot.add_handler(CommandHandler("addpts", add_points))
    bot.add_handler(CommandHandler("broadcast", broadcast))
    bot.add_handler(CallbackQueryHandler(callback))
    bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    bot.run_polling(drop_pending_updates=True)
