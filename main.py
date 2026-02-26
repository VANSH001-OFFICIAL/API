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
def home(): return "🤖 Spy Eye Premium is Online!", 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)

# --- CONFIG ---
TOKEN = "8645433687:AAH_pMfMPzFviHKh3DDWxIZqDZNLs05UmCs"
ADMIN_IDS = [7117775366, 7259309072] 
CHANNELS = ["@verifiedpaisabots", "@RARE_API"] 
DATA_FILE = "users_v3.json" 
API_KEY = "PAID_SELL12"
BASE_API_URL = "https://tg-user-id-to-number-m7hl.onrender.com"

# --- DB HANDLER ---
def load_data():
    with db_lock:
        if not os.path.exists(DATA_FILE):
            return {"users": {}, "total_searches": 0}
        try:
            with open(DATA_FILE, "r") as f: return json.load(f)
        except: return {"users": {}, "total_searches": 0}

def save_data(data):
    with db_lock:
        try:
            with open(DATA_FILE, "w") as f: json.dump(data, f, indent=4)
        except: pass

# --- JOIN CHECK ---
async def check_membership(user_id, context):
    try:
        for ch in CHANNELS:
            member = await context.bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status in ["left", "kicked", "restricted"]:
                return False
        return True
    except:
        return True 

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    db = load_data()
    
    if uid not in db["users"]:
        ref = context.args[0] if context.args and context.args[0].isdigit() else None
        if ref and ref in db["users"] and ref != uid:
            db["users"][ref]["points"] = db["users"][ref].get("points", 0) + 1
            try:
                await context.bot.send_message(
                    chat_id=int(ref), 
                    text=f"<b>🎁 Referral Success!</b>\n\nUser <pre>{uid}</pre> joined via your link.\n<b>+1 Point</b> has been added to your wallet!",
                    parse_mode=ParseMode.HTML
                )
            except: pass
        db["users"][uid] = {"points": 3}
        save_data(db)
    
    welcome_text = (
        f"<b>👋 Welcome to Spy Eye Master!</b>\n\n"
        f"I am the most advanced <b>Telegram ID to Mobile Number</b> lookup bot. "
        f"Search through millions of leaked records instantly.\n\n"
        f"<b>🛠 Your Stats:</b>\n"
        f"├ 👤 <b>User ID:</b> <code>{uid}</code>\n"
        f"└ 💰 <b>Balance:</b> <code>{db['users'][uid]['points']} Points</code>\n\n"
        f"<i>Use the menu buttons below to navigate!</i>"
    )
    
    kb = ReplyKeyboardMarkup([
        [KeyboardButton("🔍 Search Database")], 
        [KeyboardButton("💰 My Wallet"), KeyboardButton("👥 Invite Friends")]
    ], resize_keyboard=True)
    
    await update.message.reply_text(welcome_text, reply_markup=kb, parse_mode=ParseMode.HTML)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = update.message.text
    db = load_data()

    if text == "💰 My Wallet":
        pts = db["users"].get(uid, {}).get("points", 0)
        await update.message.reply_text(
            f"<b>💳 Your Wallet Balance</b>\n\n"
            f"💰 <b>Current Points:</b> <code>{pts} Points</code>\n"
            f"📈 <b>Status:</b> {'Active' if pts > 0 else 'Low Balance'}\n\n"
            f"<i>1 Search = 3 Points. Share your link to earn more!</i>",
            parse_mode=ParseMode.HTML
        )

    elif text == "👥 Invite Friends":
        bot_me = await context.bot.get_me()
        link = f"https://t.me/{bot_me.username}?start={uid}"
        invite_text = (
            f"<b>👥 Refer & Earn Program</b>\n\n"
            f"Share your link with friends. For every user who joins via your link, "
            f"you will receive <b>1 Point</b> instantly!\n\n"
            f"🔗 <b>Your Unique Link:</b>\n<code>{link}</code>"
        )
        await update.message.reply_text(invite_text, parse_mode=ParseMode.HTML)

    elif text == "🔍 Search Database":
        if not await check_membership(int(uid), context):
            msg = (
                "<b>🚫 Access Denied!</b>\n\n"
                "To use our database, you must be a member of our official channels. "
                "Please join them and try again."
            )
            btns = [
                [InlineKeyboardButton("📢 Join Channel 1", url="https://t.me/verifiedpaisabots")], 
                [InlineKeyboardButton("📢 Join Channel 2", url="https://t.me/RARE_API")]
            ]
            return await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.HTML)
        
        if db["users"].get(uid, {}).get("points", 0) < 3:
            return await update.message.reply_text("<b>❌ Insufficient Points!</b>\n\nYou need at least 3 points to perform a search.", parse_mode=ParseMode.HTML)
        
        context.user_data['waiting_id'] = True
        await update.message.reply_text("<b>🔢 Targeted Search</b>\n\nPlease enter the <b>Telegram User ID</b> of the target to fetch details:", parse_mode=ParseMode.HTML)

    elif context.user_data.get('waiting_id'):
        target = text.strip()
        context.user_data['waiting_id'] = False
        if not target.isdigit(): return
        
        if int(target) in ADMIN_IDS:
            return await update.message.reply_text("<b>🛡 Protected Profile!</b>\n\nThis ID belongs to our Admin and cannot be searched.", parse_mode=ParseMode.HTML)

        m = await update.message.reply_text("<b>🛰 Establishing Connection...</b>\n<i>Searching global database for records.</i>", parse_mode=ParseMode.HTML)
        try:
            res = requests.get(f"{BASE_API_URL}/api/number={target}?api_key={API_KEY}", timeout=15).json()
            if "result" in res:
                db["users"][uid]["points"] -= 3
                db["total_searches"] = db.get("total_searches", 0) + 1
                save_data(db)
                final_msg = (
                    f"<b>✅ Data Found Successfully!</b>\n\n"
                    f"👤 <b>Telegram ID:</b> <code>{target}</code>\n"
                    f"📞 <b>Mobile Number:</b> <code>{res['result']['number']}</code>\n\n"
                    f"<i>3 Points deducted from your balance.</i>"
                )
                await m.edit_text(final_msg, parse_mode=ParseMode.HTML)
            else:
                await m.edit_text("<b>❌ Search Results:</b>\n\nNo matching records found for this ID in our leaked database.", parse_mode=ParseMode.HTML)
        except:
            await m.edit_text("<b>⚠️ System Timeout!</b>\n\nThe server is under heavy load. Please try your search again in a few minutes.", parse_mode=ParseMode.HTML)

# --- ADMIN PANEL ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    cmd = update.message.text
    db = load_data()
    if cmd.startswith("/addpts"):
        try:
            _, tid, amt = cmd.split()
            if tid in db["users"]:
                db["users"][tid]["points"] += int(amt)
                save_data(db)
                await update.message.reply_text(f"✅ Added {amt} points to User {tid}")
            else: await update.message.reply_text("❌ ID not found in database.")
        except: pass

if __name__ == '__main__':
    Thread(target=run_web, daemon=True).start()
    bot = ApplicationBuilder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(MessageHandler(filters.COMMAND & filters.User(user_id=ADMIN_IDS), admin_panel))
    bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    bot.run_polling(drop_pending_updates=True)
