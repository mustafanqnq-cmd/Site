import os
import json
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply

# ----------------- الڤارات -----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "")

bot = telebot.TeleBot(BOT_TOKEN)

# ----------------- قاعدة البيانات (JSON) -----------------
DB_FILE = "bot_data.json"

def load_data():
    default_data = {
        "users": [],
        "modes": {},
        "bot_name": "بوت التواصل الرسمي",
        "dev_name": "المطور",
        "dev_link": "https://t.me/CC99V"
    }
    if not os.path.exists(DB_FILE):
        return default_data
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # دمج الخيارات الافتراضية في حال وجود مفاتيح ناقصة
            for key, val in default_data.items():
                if key not in data:
                    data[key] = val
            return data
    except:
        return default_data

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ----------------- دالة فحص الاشتراك -----------------
def check_subscription(user_id):
    if not FORCE_SUB_CHANNEL:
        return True
    
    channel = FORCE_SUB_CHANNEL if FORCE_SUB_CHANNEL.startswith("@") else f"@{FORCE_SUB_CHANNEL}"
    
    try:
        member = bot.get_chat_member(channel, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except Exception as e:
        print(f"Error checking subscription: {e}")
        return True

# ----------------- لوحة التحكم والإعدادات للأدمن -----------------
def get_admin_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📊 إحصائيات البوت", callback_data="bot_stats"))
    markup.add(InlineKeyboardButton("⚙️ إعدادات الاسم والمطور", callback_data="bot_settings"))
    return markup

def get_settings_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✏️ تغيير اسم البوت", callback_data="set_bot_name"))
    markup.add(InlineKeyboardButton("👤 تغيير اسم المطور", callback_data="set_dev_name"))
    markup.add(InlineKeyboardButton("🔗 تغيير رابط/يوزر المطور", callback_data="set_dev_link"))
    markup.add(InlineKeyboardButton("🔙 العودة للوحة الرئيسية", callback_data="admin_home"))
    return markup

# ----------------- أوامر البوت -----------------
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    data = load_data()
    
    if user_id not in data["users"]:
        data["users"].append(user_id)
        save_data(data)

    # 1. لوحة المطور (الأدمن)
    if user_id == ADMIN_ID:
        bot.send_message(user_id, "أهلاً بك أيها المطور في لوحة التحكم الخاصة بك ⚙️", reply_markup=get_admin_keyboard())
        return

    # 2. فحص الاشتراك الإجباري للمستخدمين
    if not check_subscription(user_id):
        channel_clean = FORCE_SUB_CHANNEL.replace('@', '')
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("اشترك في القناة أولاً 📢", url=f"https://t.me/{channel_clean}"))
        bot.send_message(user_id, "عذراً، يجب عليك الاشتراك في قناة المشروع أولاً لتتمكن من استخدام البوت.", reply_markup=markup)
        return

    # 3. واجهة المستخدم العادي
    current_mode = data["modes"].get(str(user_id), "known")
    mode_text = "المعروف 👤" if current_mode == "known" else "الخفي 👻"
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(f"تغيير الوضع (الحالي: {mode_text})", callback_data="toggle_mode"))
    
    bot_name = data.get("bot_name", "بوت التواصل الرسمي")
    dev_name = data.get("dev_name", "المطور")
    dev_link = data.get("dev_link", "https://t.me/CC99V")

    welcome_text = (
        f"أهلاً بك في **[{bot_name}]** 👋\n"
        f"تطوير وإدارة: [{dev_name}]({dev_link})\n\n"
        f"أرسل رسالتك (نص، صورة، فيديو، ملف) وسيتم إيصالها للمطور مباشرة.\n"
        f"يمكنك التبديل بين إرسال الرسالة باسمك أو بشكل مخفي من الزر أدناه."
    )
    bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode="Markdown", disable_web_page_preview=True)

# ----------------- معالجة أزرار الأنلاين (Callbacks) -----------------
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    data = load_data()
    
    if user_id == ADMIN_ID:
        if call.data == "admin_home":
            bot.edit_message_text("أهلاً بك أيها المطور في لوحة التحكم الخاصة بك ⚙️", 
                                  chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_admin_keyboard())
            return
            
        elif call.data == "bot_stats":
            users_count = len(data["users"])
            bot.edit_message_text(f"📊 **إحصائيات البوت:**\n\n👥 إجمالي المستخدمين: {users_count} مستخدم.", 
                                  chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_admin_keyboard(), parse_mode="Markdown")
            return

        elif call.data == "bot_settings":
            bot_name = data.get("bot_name", "غير محدد")
            dev_name = data.get("dev_name", "غير محدد")
            dev_link = data.get("dev_link", "غير محدد")
            
            info_text = (
                "⚙️ **الإعدادات الحالية للبوت:**\n\n"
                f"🤖 **اسم البوت:** {bot_name}\n"
                f"👤 **اسم المطور:** {dev_name}\n"
                f"🔗 **رابط/يوزر المطور:** {dev_link}\n\n"
                "اختر من الأزرار أدناه للتعديل:"
            )
            bot.edit_message_text(info_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_settings_keyboard(), parse_mode="Markdown")
            return

        elif call.data == "set_bot_name":
            msg = bot.send_message(call.message.chat.id, "أرسل الآن **اسم البوت الجديد**:", reply_markup=ForceReply(selective=False))
            bot.register_next_step_handler(msg, save_bot_name)
            return

        elif call.data == "set_dev_name":
            msg = bot.send_message(call.message.chat.id, "أرسل الآن **اسم المطور الظاهر** (مثال: مصطفى السرمدي):", reply_markup=ForceReply(selective=False))
            bot.register_next_step_handler(msg, save_dev_name)
            return

        elif call.data == "set_dev_link":
            msg = bot.send_message(call.message.chat.id, "أرسل الآن **يوزر أو رابط المطور** (مثال: `@CC99V` أو رابط أو ID):", reply_markup=ForceReply(selective=False))
            bot.register_next_step_handler(msg, save_dev_link)
            return

    # أزرار المستخدمين العاديين
    if call.data == "toggle_mode":
        current_mode = data["modes"].get(str(user_id), "known")
        new_mode = "anonymous" if current_mode == "known" else "known"
        data["modes"][str(user_id)] = new_mode
        save_data(data)
        
        mode_text = "المعروف 👤" if new_mode == "known" else "الخفي 👻"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"تغيير الوضع (الحالي: {mode_text})", callback_data="toggle_mode"))
        
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id, f"تم تغيير وضع التواصل إلى: {mode_text}")
        
    elif call.data.startswith("reply_"):
        target_user = call.data.split("_")[1]
        msg = bot.send_message(call.message.chat.id, f"أرسل ردك الآن للمستخدم:\n`{target_user}`", reply_markup=ForceReply(selective=False))
        bot.register_next_step_handler(msg, send_reply_to_user, target_user)

# ----------------- دوال حفظ الإعدادات من الأدمن -----------------
def save_bot_name(message):
    data = load_data()
    data["bot_name"] = message.text.strip()
    save_data(data)
    bot.reply_to(message, f"✅ تم حفظ اسم البوت بنجاح: **{data['bot_name']}**", parse_mode="Markdown", reply_markup=get_admin_keyboard())

def save_dev_name(message):
    data = load_data()
    data["dev_name"] = message.text.strip()
    save_data(data)
    bot.reply_to(message, f"✅ تم حفظ اسم المطور بنجاح: **{data['dev_name']}**", parse_mode="Markdown", reply_markup=get_admin_keyboard())

def save_dev_link(message):
    data = load_data()
    raw_input = message.text.strip()
    
    # معالجة المدخلات (سواء كانت يوزر أو رابط أو أيدي)
    if raw_input.startswith("http://") or raw_input.startswith("https://"):
        link = raw_input
    elif raw_input.startswith("@"):
        link = f"https://t.me/{raw_input.replace('@', '')}"
    elif raw_input.isdigit():
        link = f"tg://user?id={raw_input}"
    else:
        link = f"https://t.me/{raw_input}"

    data["dev_link"] = link
    save_data(data)
    bot.reply_to(message, f"✅ تم حفظ رابط المطور بنجاح: {link}", reply_markup=get_admin_keyboard())

def send_reply_to_user(message, target_user):
    try:
        bot.copy_message(target_user, message.chat.id, message.message_id)
        bot.reply_to(message, "✅ تم إرسال ردك للمستخدم بنجاح.")
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ، ربما قام المستخدم بحظر البوت.\n{e}")

# ----------------- استقبال ورسائل التواصل -----------------
@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker'])
def handle_messages(message):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        if message.reply_to_message and message.reply_to_message.forward_from:
            target_user = message.reply_to_message.forward_from.id
            try:
                bot.copy_message(target_user, message.chat.id, message.message_id)
                bot.reply_to(message, "✅ تم إرسال ردك بنجاح.")
            except:
                bot.reply_to(message, "❌ لم أتمكن من إرسال الرد.")
        return

    if not check_subscription(user_id):
        bot.send_message(user_id, "📢 يجب عليك الاشتراك في القناة أولاً لكي تصل رسالتك.")
        return

    data = load_data()
    user_mode = data["modes"].get(str(user_id), "known")

    bot.send_message(user_id, "✅ تم استلام رسالتك وإرسالها، انتظر الرد...")

    if user_mode == "known":
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
    else:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("رد على هذا المستخدم المخفي 👻", callback_data=f"reply_{user_id}"))
        bot.copy_message(ADMIN_ID, message.chat.id, message.message_id, reply_markup=markup)

if __name__ == "__main__":
    print("Bot is running with dynamic admin settings...")
    bot.infinity_polling(skip_pending=True)
