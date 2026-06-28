import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.error import BadRequest

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# جلب المتغيرات من بيئة الاستضافة (Railway)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# دعم آيدي واحد أو أكثر (في حال أردت إضافة صديقك معك بنفس البوت مستقبلاً)
ADMINS = [int(x) for x in os.environ.get("ADMIN_ID", "").split(",") if x.strip()]
# اسم المطور الذي سيظهر في كليشة الترحيب
DEV_NAME = os.environ.get("DEV_NAME", "المطور")

# ملف حفظ بيانات البوت (عدد المشتركين والقناة الإجبارية)
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
admin_states = {} # لتتبع حالة المطور (مثل انتظار إرسال معرف القناة)

async def check_force_sub(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    channel = bot_data.get("force_channel")
    if not channel:
        return True # لا توجد قناة مفروضة
    try:
        member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
        if member.status in ['left', 'kicked']:
            return False
        return True
    except BadRequest:
        # إذا كان البوت ليس أدمن أو القناة غير صحيحة، نسمح للمستخدم بالدخول لتجنب توقف البوت
        return True
    except Exception as e:
        log.error(f"Error checking sub: {e}")
        return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # تسجيل المشترك الجديد
    if user.id not in bot_data["subscribers"]:
        bot_data["subscribers"].append(user.id)
        save_data(bot_data)

    if user.id in ADMINS:
        # كليشة ولستة المطور
        keyboard = [
            [InlineKeyboardButton("معلومات البوت 🤖", callback_data="bot_info")],
            [InlineKeyboardButton("عدد المشتركين 👥", callback_data="sub_count")],
            [InlineKeyboardButton("تعيين قناة اشتراك 📢", callback_data="set_channel"), 
             InlineKeyboardButton("حذف القناة 🗑️", callback_data="del_channel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"أهلاً بك يا مطورنا الغالي 👑\n\nإليك لوحة التحكم الخاصة بك:",
            reply_markup=reply_markup
        )
    else:
        # فحص الاشتراك للمستخدمين العاديين
        is_subbed = await check_force_sub(user.id, context)
        if not is_subbed:
            channel = bot_data.get("force_channel")
            keyboard = [[InlineKeyboardButton("اضغط هنا للاشتراك 📢", url=f"https://t.me/{channel.replace('@', '')}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "عذراً عزيزي، يجب عليك الاشتراك في قناة البوت أولاً لتتمكن من إرسال رسائلك.",
                reply_markup=reply_markup
            )
            return

        # جلب الآيدي الخاص بأول مطور في لستة الأدمنية لربطه بالاسم
        dev_id = ADMINS[0] if ADMINS else 0
        
        # كليشة المستخدم العادي مع رابط المطور (HTML)
        welcome_text = (
            f"أهلاً بك في بوت ألسَايت الخاص بِ (<a href='tg://user?id={dev_id}'>{DEV_NAME}</a>)\n"
            "اكتب رسالتك هُنا وراح توصل للمطور مباشرة، وراح يرد بأقرب وقت بخصوص التنصيب أو أي استفسار إذا كانت هُنالك مُشكلة، ."
        )
        
        # استخدام HTML لتفعيل الرابط
        await update.message.reply_text(
            welcome_text,
            parse_mode="HTML"
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if user_id not in ADMINS:
        return

    data = query.data
    if data == "bot_info":
        channel = bot_data.get("force_channel") or "لا توجد"
        text = (
            f"🤖 **معلومات البوت**:\n\n"
            f"▪️ عدد المشتركين الكلي: {len(bot_data['subscribers'])}\n"
            f"▪️ قناة الاشتراك الإجباري: {channel}"
        )
        await query.edit_message_text(text, parse_mode="Markdown")
        
    elif data == "sub_count":
        count = len(bot_data['subscribers'])
        await query.edit_message_text(f"👥 عدد المشتركين الحالي: {count}")
        
    elif data == "set_channel":
        admin_states[user_id] = "waiting_for_channel"
        await query.edit_message_text("حسناً، أرسل الآن معرف القناة (يجب أن يبدأ بـ @)\nمثال: @mychannel\n\n*تأكد من رفع البوت كأدمن في القناة أولاً!*", parse_mode="Markdown")
        
    elif data == "del_channel":
        bot_data["force_channel"] = None
        save_data(bot_data)
        await query.edit_message_text("✅ تم إيقاف الاشتراك الإجباري وحذف القناة بنجاح.")

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message

    # 1. إذا كان المطور في وضع "إضافة قناة"
    if user.id in ADMINS and admin_states.get(user.id) == "waiting_for_channel":
        if msg.text and msg.text.startswith("@"):
            bot_data["force_channel"] = msg.text
            save_data(bot_data)
            admin_states.pop(user.id, None)
            await msg.reply_text(f"✅ تم تعيين القناة {msg.text} كقناة اشتراك إجباري بنجاح.")
        else:
            await msg.reply_text("❌ المعرف غير صحيح، يرجى إرسال معرف يبدأ بـ @")
        return

    # 2. إذا كانت الرسالة من المطور (رد على مستخدم)
    if user.id in ADMINS:
        if msg.reply_to_message:
            original_id = msg.reply_to_message.message_id
            target_user_id = forwarded_map.get(original_id)
            if target_user_id:
                try:
                    await context.bot.copy_message(
                        chat_id=target_user_id,
                        from_chat_id=user.id,
                        message_id=msg.message_id,
                    )
                    await msg.reply_text("✅ تم إرسال الرد للمستخدم.")
                except Exception as e:
                    await msg.reply_text(f"❌ فشل الإرسال (قد يكون المستخدم حظر البوت): {e}")
            else:
                await msg.reply_text("⚠️ ما عرفت لمين أرسل، الرسالة قديمة أو البوت أعاد التشغيل.")
        return

    # 3. رسالة من مستخدم عادي
    # فحص الاشتراك قبل إرسال الرسالة للمطور
    is_subbed = await check_force_sub(user.id, context)
    if not is_subbed:
        channel = bot_data.get("force_channel")
        keyboard = [[InlineKeyboardButton("اضغط هنا للاشتراك 📢", url=f"https://t.me/{channel.replace('@', '')}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await msg.reply_text(
            "عذراً، يجب عليك الاشتراك في قناة البوت أولاً.",
            reply_markup=reply_markup
        )
        return

    # توجيه الرسالة للمطورين
    info = f"📩 رسالة من: {user.full_name} (@{user.username or 'لا يوجد'})\nID: {user.id}"
    for admin_id in ADMINS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=info)
            forwarded = await context.bot.copy_message(
                chat_id=admin_id,
                from_chat_id=msg.chat_id,
                message_id=msg.message_id,
            )
            forwarded_map[forwarded.message_id] = user.id
        except Exception as e:
            log.error(f"Could not forward to admin {admin_id}: {e}")

    await msg.reply_text("✅ تم استلام رسالتك، راح يتم الرد عليك قريبًا.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_user_message))
    log.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
