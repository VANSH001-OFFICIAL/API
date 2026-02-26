import json
import os
import requests
import urllib3
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from telegram.constants import ParseMode

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- WEB SERVER (Render Compatible) ---
app = Flask('')

@app.route('/')
def home():
    return "Spy Eye Bot is Running on Render!", 200

@app.route('/health')
def health():
    return "OK", 200

def run():
    # Render automatically sets a PORT environment variable
    port = int(os.environ.get("PORT", 8080))
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

# --- DATABASE HELPERS ---
def load_data():
    default = {"users": {}, "protected_ids": ADMIN_IDS, "total_searches": 0}
    if not os.path.exists(DATA_FILE): return default
    with open(DATA_FILE, "r") as f:
        try:
            db = json.load(f)
            if "protected_ids" not in db: db["protected_ids"] = ADMIN_IDS
            return db
        except: return default

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def escape_md(text):
    return "".join(f"\\{c}" if c in r"_*[]()~`>#+-=|{}.!" else c for c in str(text))

# --- FORCE JOIN CHECK ---
async def is_joined(user_id, context):
    for channel in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]: return False
        except: return False
    return True

# --- MAIN MENU & REFERRAL LOGIC ---
async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    uid = str(user.id)
    db = load_data()

    if uid not in db["users"]:
        ref_id = context.args[0] if context.args and context.args[0].isdigit() else None
        if ref_id and ref_id != uid and ref_id in db["users"]:
            db["users"][ref_id]["points"] += 1
            db["users"][ref_id]["refer_count"] += 1
            try:
                await context.bot.send_message(
                    chat_id=int(ref_id), 
                    text="🎁 *Referral Success\!* You earned *1 Point*\.", 
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            except: pass
        db["users"][uid] = {"points": 3, "referred_by": ref_id, "refer_count": 0}
        save_data(db)

    kb = ReplyKeyboardMarkup([[KeyboardButton("📞 Get Number")], [KeyboardButton("💰 Balance"), KeyboardButton("👥 Refer & Earn")]], resize_keyboard=True)
    text = f"👋 *Welcome {escape_md(user.first_name)}\!*\n\n💰 *Balance:* `{db['users'][uid]['points']} Pts`"
    
    if update.callback_query:
        try: await update.callback_query.message.delete()
        except: pass
        await context.bot.send_message(chat_id=user.id, text=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN_V2)

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_joined(update.effective_user.id, context):
        buttons = [[InlineKeyboardButton("📢 Join Channel 1", url=f"https://t.me/{CHANNELS[0][1:]}")],
                   [InlineKeyboardButton("📢 Join Channel 2", url=f"https://t.me/{CHANNELS[1][1:]}")],
                   [InlineKeyboardButton("✅ Verify Joining", callback_data="verify_join")]]
        return await update.message.reply_text("⚠️ *Join our channels to use this bot\!*", reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.MARKDOWN_V2)
    await send_main_menu(update, context, update.effective_user)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = update.message.text
    db = load_data()

    if not await is_joined(update.effective_user.id, context): return

    if text == "💰 Balance":
        await update.message.reply_text(f"💰 *Balance:* `{db['users'].get(uid, {}).get('points', 0)} Pts`", parse_mode=ParseMode.MARKDOWN_V2)
    elif text == "👥 Refer & Earn":
        bot_un = (await context.bot.get_me()).username
        link = f"https://t.me/{bot_un}?start={uid}"
        await update.message.reply_text(f"👥 *Total Refers:* `{db['users'].get(uid, {}).get('refer_count', 0)}`\n🔗 *Your Link:* `{escape_md(link)}`", parse_mode=ParseMode.MARKDOWN_V2)
    elif text == "📞 Get Number":
        if db["users"].get(uid, {}).get("points", 0) < 3: return await update.message.reply_text("❌ *Need 3 Pts\!*", parse_mode=ParseMode.MARKDOWN_V2)
        context.user_data['wait'] = True
        await update.message.reply_text("🔢 *Send Target Telegram ID:*", parse_mode=ParseMode.MARKDOWN_V2)
    elif context.user_data.get('wait'):
        target = text.strip()
        context.user_data['wait'] = False
        if target.isdigit() and int(target) in ADMIN_IDS: return await update.message.reply_text("🛡️ *ID Protected\!*", parse_mode=ParseMode.MARKDOWN_V2)
        
        m = await update.message.reply_text("🔎 *Searching\.\.\.*", parse_mode=ParseMode.MARKDOWN_V2)
        try:
            res = requests.get(f"https://tg-user-id-to-number-m7hl.onrender.com/api/number={target}?api_key={API_KEY}", timeout=40, verify=False).json()
            if "result" in res and "number" in res["result"]:
                db["users"][uid]["points"] -= 3
                save_data(db)
                await m.edit_text(f"✅ *Found:* `{escape_md(res['result']['number'])}`", parse_mode=ParseMode.MARKDOWN_V2)
            else: await m.edit_text("❌ *No Data Found\.*", parse_mode=ParseMode.MARKDOWN_V2)
        except: await m.edit_text("⚠️ *API Error\!*", parse_mode=ParseMode.MARKDOWN_V2)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.data == "verify_join":
        if await is_joined(update.effective_user.id, context):
            await update.callback_query.answer("✅ Verified!")
            await send_main_menu(update, context, update.effective_user)
        else: await update.callback_query.answer("❌ Join both channels first!", show_alert=True)

if __name__ == '__main__':
    keep_alive()
    bot = ApplicationBuilder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CallbackQueryHandler(button_callback))
    bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    bot.run_polling(drop_pending_updates=True)
