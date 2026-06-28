import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])

# تخزين بسيط بالذاكرة: نربط آيدي الرسالة المرسلة للأدمن بآيدي المستخدم الأصلي
# عشان لما الأدمن يرد على رسالة معينة، نعرف نرسلها لمين
forwarded_map = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً بك 👋\n"
        "اكتب رسالتك هنا وراح توصل للمطور مباشرة، وراح يردك بأقرب وقت بخصوص التنصيب أو أي استفسار."
    )


async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message

    # لو الرسالة جاية من الأدمن نفسه (يعني رد على مستخدم)
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
                await msg.reply_text("⚠️ ما عرفت لمين أرسل، الرسالة قديمة أو البوت أعاد التشغيل.")
        return

    # رسالة جايه من مستخدم عادي -> ترسل للأدمن
    info = f"📩 رسالة من: {user.full_name} (@{user.username or 'لا يوجد'})\nID: {user.id}"
    await context.bot.send_message(chat_id=ADMIN_ID, text=info)

    forwarded = await context.bot.copy_message(
        chat_id=ADMIN_ID,
        from_chat_id=msg.chat_id,
        message_id=msg.message_id,
    )
    # نخزن الربط عشان لو الأدمن رد على هذي الرسالة بالذات
    forwarded_map[forwarded.message_id] = user.id

    await msg.reply_text("✅ تم استلام رسالتك، راح يتم الرد عليك قريبًا.")


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_user_message))
    log.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
