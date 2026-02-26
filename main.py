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
                    text=f"<b>🎁 Referral Success!</b>\n\nNew user joined via your link.\n<b>+1 Point</b> added to your balance!",
                    parse_mode=ParseMode.HTML
                )
            except: pass
        db["users"][uid] = {"points": 3}
        save_data(db)
    
    welcome_text = (
        f"<b>🛰 Spy Eye Master V3</b>\n\n"
        f"Get the mobile number linked to any Telegram User ID instantly using our premium database.\n\n"
        f"<b>👤 Your Account:</b>\n"
        f"├ 🆔 <b>ID:</b> <code>{uid}</code>\n"
        f"└ 💰 <b>Balance:</b> <code>{db['users'][uid]['points']} Points</code>\n\n"
        f"<i>Select an option below to start your search.</i>"
    )
    
    kb = ReplyKeyboardMarkup([
        [KeyboardButton("🔍 Get Number")], 
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
            f"<b>💳 Wallet Overview</b>\n\n"
            f"💵 <b>Current Balance:</b> <code>{pts} Points</code>\n"
            f"📊 <b>Tier:</b> {'Premium' if pts > 10 else 'Basic'}\n\n"
            f"<i>Cost: 3 points per number search.</i>",
            parse_mode=ParseMode.HTML
        )

    elif text == "👥 Invite Friends":
        bot_me = await context.bot.get_me()
        link = f"https://t.me/{bot_me.username}?start={uid}"
        invite_text = (
            f"<b>👥 Refer & Earn</b>\n\n"
            f"Share your link and get <b>1 Point</b> for every unique user.\n\n"
            f"🔗 <b>Your Link:</b>\n<code>{link}</code>"
        )
        await update.message.reply_text(invite_text, parse_mode=ParseMode.HTML)

    elif text == "🔍 Get Number":
        if not await check_membership(int(uid), context):
            msg = (
                "<b>🚫 Membership Required!</b>\n\n"
                "Join our channels to unlock the <b>Get Number</b> tool."
            )
            btns = [
                [InlineKeyboardButton("📢 Channel 1", url="https://t.me/verifiedpaisabots")], 
                [InlineKeyboardButton("📢 Channel 2", url="https://t.me/RARE_API")]
            ]
            return await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.HTML)
        
        if db["users"].get(uid, {}).get("points", 0) < 3:
            return await update.message.reply_text("<b>❌ Low Balance!</b>\n\nYou need 3 points. Invite friends to get more.", parse_mode=ParseMode.HTML)
        
        context.user_data['waiting_id'] = True
        await update.message.reply_text("<b>🔢 Number Lookup</b>\n\nEnter the <b>Telegram User ID</b> to find their mobile number:", parse_mode=ParseMode.HTML)

    elif context.user_data.get('waiting_id'):
        target = text.strip()
        context.user_data['waiting_id'] = False
        if not target.isdigit(): return
        
        if int(target) in ADMIN_IDS:
            return await update.message.reply_text("<b>🛡 Access Restricted!</b>\n\nAdmin data is encrypted and protected.", parse_mode=ParseMode.HTML)

        m = await update.message.reply_text("<b>🛰 Querying Database...</b>", parse_mode=ParseMode.HTML)
        try:
            res = requests.get(f"{BASE_API_URL}/api/number={target}?api_key={API_KEY}", timeout=15).json()
            if "result" in res:
                db["users"][uid]["points"] -= 3
                db["total_searches"] = db.get("total_searches", 0) + 1
                save_data(db)
                final_msg = (
                    f"<b>✅ Number Found!</b>\n\n"
                    f"👤 <b>User ID:</b> <code>{target}</code>\n"
                    f"📞 <b>Mobile Number:</b> <code>{res['result']['number']}</code>"
                )
                await m.edit_text(final_msg, parse_mode=ParseMode.HTML)
            else:
                await m.edit_text("<b>❌ Result: Not Found</b>\n\nThis ID is not in our database.", parse_mode=ParseMode.HTML)
        except:
            await m.edit_text("<b>⚠️ Server Error!</b>\n\nPlease try again later.", parse_mode=ParseMode.HTML)

# --- ADMIN PANEL ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    cmd = update.message.text
    db = load_data()
    
    if cmd == "/stats":
        stats_text = (
            f"<b>📊 Spy Eye Stats</b>\n\n"
            f"👥 <b>Users:</b> <code>{len(db['users'])}</code>\n"
            f"🔎 <b>Total Searches:</b> <code>{db.get('total_searches',0)}</code>"
        )
        await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)
        
    elif cmd.startswith("/addpts"):
        try:
            _, tid, amt = cmd.split()
            if tid in db["users"]:
                db["users"][tid]["points"] += int(amt)
                save_data(db)
                await update.message.reply_text(f"✅ Credited {amt} points to {tid}")
        except: pass
    
    elif cmd.startswith("/broadcast"):
        msg = cmd.replace("/broadcast", "").strip()
        for u in db["users"]:
            try: await context.bot.send_message(chat_id=int(u), text=f"📢 <b>ADMIN:</b>\n\n{msg}", parse_mode=ParseMode.HTML)
            except: pass
        await update.message.reply_text("✅ Sent.")

if __name__ == '__main__':
    Thread(target=run_web, daemon=True).start()
    bot = ApplicationBuilder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(MessageHandler(filters.COMMAND & filters.User(user_id=ADMIN_IDS), admin_panel))
    bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    bot.run_polling(drop_pending_updates=True)
