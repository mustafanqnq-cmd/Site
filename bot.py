import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters

# إعدادات التسجيل (Logs)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# المتغيرات (تأكد من إضافتها في Railway)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
DEV_NAME = os.environ.get("DEV_NAME", "المطور")

# تخزين الربط (عشان نعرف نرد على مين)
forwarded_map = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # لو الشخص هو المطور (يظهر له لوحة التحكم)
    if user.id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("إحصائيات البوت 📊", callback_data="stats")],
            [InlineKeyboardButton("إضافة قناة إجبارية 📢", callback_data="set_channel")]
        ]
        await update.message.reply_text("أهلاً بك يا مطور، هذه هي لوحة التحكم الخاصة بك:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # إذا كان مستخدم عادي (يظهر له كليشة الترحيب)
    # الرابط هنا يربط الاسم ببروفايل المطور باستخدام ID الخاص به
    welcome_text = (
        f"أهلاً بك في بوت ألسَايت الخاص بِ (<a href='tg://user?id={ADMIN_ID}'>{DEV_NAME}</a>)\n"
        "اكتب رسالتك هُنا وراح توصل للمطور مباشرة، وراح يرد بأقرب وقت بخصوص التنصيب أو أي استفسار إذا كانت هُنالك مُشكلة، ."
    )
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=constants.ParseMode.HTML
    )

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message

    # لو الرسالة جاية من المطور (رد على مستخدم)
    if user.id == ADMIN_ID:
        if msg.reply_to_message:
            original_id = msg.reply_to_message.message_id
            target_user_id = forwarded_map.get(original_id)
            if target_user_id:
                try:
                    await context.bot.copy_message(
                        chat_id=target_user_id,
                        from_chat_id=ADMIN_ID,
                        message_id=msg.message_id,
                    )
                    await msg.reply_text("✅ تم إرسال الرد للمستخدم.")
                except Exception as e:
                    await msg.reply_text(f"❌ فشل الإرسال: {e}")
            else:
                await msg.reply_text("⚠️ لم أتمكن من العثور على المستخدم (قد يكون البوت أعاد التشغيل).")
        return

    # لو الرسالة جاية من مستخدم عادي -> إرسالها للمطور
    info = f"📩 رسالة من: {user.full_name} (@{user.username or 'لا يوجد'})\nID: {user.id}"
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=info)
        forwarded = await context.bot.copy_message(
            chat_id=ADMIN_ID,
            from_chat_id=msg.chat_id,
            message_id=msg.message_id,
        )
        forwarded_map[forwarded.message_id] = user.id
        await msg.reply_text("✅ تم استلام رسالتك، راح يتم الرد عليك قريبًا.")
    except Exception as e:
        log.error(f"Error forwarding message: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_user_message))
    
    log.info("البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()

