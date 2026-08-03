import os
import json
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply

# ----------------- الڤارات -----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "")

bot = telebot.TeleBot(BOT_TOKEN)

# ----------------- قاعدة البيانات -----------------
DB_FILE = "bot_data.json"

def load_data():
    if not os.path.exists(DB_FILE):
        return {"users": [], "modes": {}}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {"users": [], "modes": {}}

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

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
        # في حال وجود مشكلة في صلاحيات البوت بالقناة نمرر المستخدم مؤقتاً لكي لا يتعطل البوت
        return True

# ----------------- أوامر البوت -----------------
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    data = load_data()
    
    if user_id not in data["users"]:
        data["users"].append(user_id)
        save_data(data)

    # 1. الاستثناء الفوري للمطور (الأدمن)
    if user_id == ADMIN_ID:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📊 إحصائيات البوت", callback_data="bot_stats"))
        bot.send_message(user_id, "أهلاً بك أيها المطور في لوحة التحكم الخاصة بك ⚙️", reply_markup=markup)
        return

    # 2. فحص الاشتراك الإجباري لباقي المستخدمين
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
    
    welcome_text = (
        "أهلاً بك في بوت التواصل الخاص بالمشروع 👋\n\n"
        "أرسل رسالتك (نص، صورة، فيديو، ملف) وسيتم إيصالها للمطور مباشرة.\n"
        "يمكنك التبديل بين إرسال الرسالة باسمك أو بشكل مخفي من الزر أدناه."
    )
    bot.send_message(user_id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    data = load_data()
    
    if call.data == "bot_stats" and user_id == ADMIN_ID:
        users_count = len(data["users"])
        bot.edit_message_text(f"📊 **إحصائيات البوت:**\n\n👥 إجمالي المستخدمين: {users_count} مستخدم.", 
                              chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        
    elif call.data == "toggle_mode":
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

def send_reply_to_user(message, target_user):
    try:
        bot.copy_message(target_user, message.chat.id, message.message_id)
        bot.reply_to(message, "✅ تم إرسال ردك للمستخدم بنجاح.")
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ، ربما قام المستخدم بحظر البوت.\n{e}")

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
    print("Bot is running...")
    bot.infinity_polling(skip_pending=True)
