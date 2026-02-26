import json
import os
import requests
import urllib3
import asyncio
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from telegram.constants import ParseMode

# SSL Warnings fix
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- WEB SERVER ---
app = Flask('')

@app.route('/')
def home():
    return "Spy Eye Bot is Active!", 200

def run():
    # Render ke liye port 10000 default hota hai, ye use handle karega
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- CONFIG ---
TOKEN = "8645433687:AAH_pMfMPzFviHKh3DDWxIZqDZNLs05UmCs"
ADMIN_IDS = [7117775366, 7259309072] 
CHANNELS = ["@verifiedpaisabots", "@BLACK_SELLERXBIO"]
DATA_FILE = "users_db.json"
API_KEY = "PAID_SELL12"

# --- DATABASE HELPERS (Persistent Fix) ---
def load_data():
    # Agar file nahi hai ya khali hai, toh default data banao
    default = {"users": {}, "protected_ids": ADMIN_IDS, "total_searches": 0}
    if not os.path.exists(DATA_FILE):
        save_data(default)
        return default
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            # Ensure users key exists
            if "users" not in data: data["users"] = {}
            return data
    except (json.JSONDecodeError, Exception):
        return default

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def escape_md(text):
    # Python 3.14 safe escape
    return "".join(f"\\{c}" if c in r"_*[]()~`>#+-=|{}.!" else c for c in str(text))

# --- FORCE JOIN CHECK ---
async def is_joined(user_id, context):
    for channel in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]: return False
        except: return False
    return True

# --- MAIN MENU ---
async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    uid = str(user.id)
    db = load_data()

    if uid not in db["users"]:
        # Referral Logic
        ref_id = context.args[0] if context.args and context.args[0].isdigit() else None
        if ref_id and ref_id != uid and ref_id in db["users"]:
            db["users"][ref_id]["points"] = db["users"][ref_id].get("points", 0) + 1
            db["users"][ref_id]["refer_count"] = db["users"][ref_id].get("refer_count", 0) + 1
            try:
                await context.bot.send_message(chat_id=int(ref_id), text="🎁 *Referral Success!* You earned *1 Point*.", parse_mode=ParseMode.MARKDOWN_V2)
            except: pass
        
        db["users"][uid] = {"points": 3, "referred_by": ref_id, "refer_count": 0}
        save_data(db)

    kb = ReplyKeyboardMarkup([[KeyboardButton("📞 Get Number")], [KeyboardButton("💰 Balance"), KeyboardButton("👥 Refer & Earn")]], resize_keyboard=True)
    text = f"👋 *Welcome {escape_md(user.first_name)}!*\n\n💰 *Balance:* `{db['users'][uid]['points']} Pts`"
    
    if update.callback_query:
        try: await update.callback_query.message.delete()
        except: pass
        await context.bot.send_message(chat_id=user.id, text=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN_V2)

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_joined(user.id, context):
        buttons = [[InlineKeyboardButton("📢 Join Channel 1", url=f"https://t.me/{CHANNELS[0][1:]}")],
                   [InlineKeyboardButton("📢 Join Channel 2", url=f"https://t.me/{CHANNELS[1][1:]}")],
                   [InlineKeyboardButton("✅ Verify Joining", callback_data="verify_join")]]
        return await update.message.reply_text("⚠️ *Join our channels to use this bot!*", reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.MARKDOWN_V2)
    await send_main_menu(update, context, user)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = update.message.text
    db = load_data()

    if not await is_joined(update.effective_user.id, context): return

    if text == "💰 Balance":
        pts = db["users"].get(uid, {}).get("points", 0)
        await update.message.reply_text(f"💰 *Balance:* `{pts} Pts`", parse_mode=ParseMode.MARKDOWN_V2)
    
    elif text == "👥 Refer & Earn":
        bot_info = await context.bot.get_me()
        link = f"https://t.me/{bot_info.username}?start={uid}"
        ref_count = db["users"].get(uid, {}).get("refer_count", 0)
        await update.message.reply_text(f"👥 *Total Refers:* `{ref_count}`\n🔗 *Your Link:* `{escape_md(link)}`", parse_mode=ParseMode.MARKDOWN_V2)
    
    elif text == "📞 Get Number":
        if db["users"].get(uid, {}).get("points", 0) < 3:
            return await update.message.reply_text("❌ *Need 3 Pts!*", parse_mode=ParseMode.MARKDOWN_V2)
        context.user_data['wait'] = True
        await update.message.reply_text("🔢 *Send Target Telegram ID:*", parse_mode=ParseMode.MARKDOWN_V2)
    
    elif context.user_data.get('wait'):
        target = text.strip()
        context.user_data['wait'] = False
        if target.isdigit() and int(target) in ADMIN_IDS:
            return await update.message.reply_text("🛡️ *ID Protected!*", parse_mode=ParseMode.MARKDOWN_V2)
        
        m = await update.message.reply_text("🔎 *Searching...*", parse_mode=ParseMode.MARKDOWN_V2)
        try:
            res = requests.get(f"https://tg-user-id-to-number-vnmc.onrender.com/api/number={target}?api_key={API_KEY}", timeout=30, verify=False).json()
            if "result" in res and "number" in res["result"]:
                db["users"][uid]["points"] -= 3
                save_data(db)
                await m.edit_text(f"✅ *Found:* `{escape_md(res['result']['number'])}`", parse_mode=ParseMode.MARKDOWN_V2)
            else:
                await m.edit_text("❌ *No Data Found.*", parse_mode=ParseMode.MARKDOWN_V2)
        except:
            await m.edit_text("⚠️ *API Error!*", parse_mode=ParseMode.MARKDOWN_V2)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.data == "verify_join":
        if await is_joined(update.effective_user.id, context):
            await update.callback_query.answer("✅ Verified!")
            await send_main_menu(update, context, update.effective_user)
        else:
            await update.callback_query.answer("❌ Join both channels first!", show_alert=True)

if __name__ == '__main__':
    keep_alive()
    bot = ApplicationBuilder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CallbackQueryHandler(button_callback))
    bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    bot.run_polling(drop_pending_updates=True)
