import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.error import BadRequest

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# جلب المتغيرات
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMINS = [int(x) for x in os.environ.get("ADMIN_ID", "").split(",") if x.strip()]
DEV_NAME = os.environ.get("DEV_NAME", "المطور")

DATA_FILE = "bot_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"subscribers": [], "force_channel": None}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

bot_data = load_data()
forwarded_map = {}
admin_states = {}

async def check_force_sub(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    channel = bot_data.get("force_channel")
    if not channel: return True
    try:
        member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status not in ['left', 'kicked']
    except: return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in bot_data["subscribers"]:
        bot_data["subscribers"].append(user.id)
        save_data(bot_data)

    if user.id in ADMINS:
        keyboard = [
            [InlineKeyboardButton("معلومات البوت 🤖", callback_data="bot_info")],
            [InlineKeyboardButton("عدد المشتركين 👥", callback_data="sub_count")],
            [InlineKeyboardButton("تعيين قناة اشتراك 📢", callback_data="set_channel"), 
             InlineKeyboardButton("حذف القناة 🗑️", callback_data="del_channel")]
        ]
        await update.message.reply_text("مرحباً مطوري، إليك لوحة التحكم:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        is_subbed = await check_force_sub(user.id, context)
        if not is_subbed:
            channel = bot_data.get("force_channel")
            kb = [[InlineKeyboardButton("اشترك بالقناة 📢", url=f"https://t.me/{channel.replace('@', '')}")]]
            await update.message.reply_text("عذراً، اشترك بالقناة أولاً.", reply_markup=InlineKeyboardMarkup(kb))
            return

        dev_id = ADMINS[0]
        # استخدام الرابط المباشر لتيليجرام
        welcome_text = f"أهلاً بك في بوت ألسَايت الخاص بِ [{DEV_NAME}](tg://user?id={dev_id})\nاكتب رسالتك هُنا وراح توصل للمطور مباشرة."
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=constants.ParseMode.MARKDOWN
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMINS: return

    if query.data == "bot_info":
        await query.edit_message_text(f"المشتركين: {len(bot_data['subscribers'])}\nالقناة: {bot_data.get('force_channel')}")
    elif query.data == "sub_count":
        await query.edit_message_text(f"عدد المشتركين: {len(bot_data['subscribers'])}")
    elif query.data == "set_channel":
        admin_states[query.from_user.id] = "waiting_for_channel"
        await query.edit_message_text("أرسل معرف القناة الآن (@channel):")
    elif query.data == "del_channel":
        bot_data["force_channel"] = None
        save_data(bot_data)
        await query.edit_message_text("تم حذف القناة.")

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message

    if user.id in ADMINS and admin_states.get(user.id) == "waiting_for_channel":
        bot_data["force_channel"] = msg.text
        save_data(bot_data)
        admin_states.pop(user.id)
        await msg.reply_text("تم حفظ القناة.")
        return

    if user.id in ADMINS and msg.reply_to_message:
        target_id = forwarded_map.get(msg.reply_to_message.message_id)
        if target_id:
            await context.bot.copy_message(target_id, from_chat_id=user.id, message_id=msg.message_id)
            await msg.reply_text("تم الإرسال.")
        return

    # توجيه الرسالة
    for admin_id in ADMINS:
        fwd = await context.bot.copy_message(admin_id, from_chat_id=msg.chat_id, message_id=msg.message_id)
        forwarded_map[fwd.message_id] = user.id
    await msg.reply_text("تم استلام رسالتك.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_user_message))
    app.run_polling()

if __name__ == "__main__":
    main()
