import telegram
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# توکن ربات که از BotFather گرفتی
import os
TOKEN = os.getenv('TOKEN')
# آیدی کانال (با @)
CHANNEL_ID = '@tehrankhabari_ir'

# لینک عکس‌ها (اینجا باید لینک واقعی بذاری)
PHOTO_SEPEHR_WIFE = 'https://roozno.com/files/fa/news/1402/10/13/339199_245.png'
PHOTO_SASY_CENSORED = 'https://roozno.com/files/fa/news/1402/10/13/339199_245.png'
PHOTO_RONALDO_WIFE = 'https://yasinrahmani.com/wp-content/uploads/2024/03/%D8%A7%D8%B1%D8%A7%D9%85%D8%B4-%D8%AF%D8%B1%D9%88%D9%86%DB%8C-%D8%AF%D8%A7%D8%B1%D9%85.jpg'

# تابع بررسی عضویت کاربر در کانال
async def check_membership(context, user_id):
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except telegram.error.BadRequest:
        return False

# تابع نمایش منوی اصلی
async def show_main_menu(update, context):
    # تعریف دکمه‌ها به صورت Reply Keyboard
    keyboard = [
        ["دیدن عکس زن سپهر حیدری"],
        ["دیدن عکس سانسوری ساسی"],
        ["دیدن عکس رونالدو و زنش"]
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True  # دکمه‌ها اندازه‌ی مناسب داشته باشن
    )
    if update.message:
        await update.message.reply_text('منوی اصلی:', reply_markup=reply_markup)
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='منوی اصلی:',
            reply_markup=reply_markup
        )

# تابع شروع ربات
async def start(update, context):
    user_id = update.effective_user.id
    if not await check_membership(context, user_id):
        join_url = f'https://t.me/{CHANNEL_ID[1:]}'
        await update.message.reply_text(
            f"برای دیدن عکس‌ها، لطفاً اول در کانال {CHANNEL_ID} عضو بشید!\nلینک عضویت: {join_url}\nبعد از عضویت، دوباره /start رو بزنید.",
            reply_markup=ReplyKeyboardRemove()  # حذف منو تا وقتی کاربر عضو نشده
        )
    else:
        await show_main_menu(update, context)

# تابع مدیریت انتخاب گزینه‌ها
async def handle_message(update, context):
    user_id = update.effective_user.id
    message_text = update.message.text

    # بررسی عضویت
    if not await check_membership(context, user_id):
        join_url = f'https://t.me/{CHANNEL_ID[1:]}'
        await update.message.reply_text(
            f"شما هنوز در کانال {CHANNEL_ID} عضو نشدید!\nلینک عضویت: {join_url}\nبعد از عضویت، دوباره /start رو بزنید.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    # ارسال عکس بر اساس انتخاب کاربر
    if message_text == "دیدن عکس زن سپهر حیدری":
        await context.bot.send_photo(chat_id=user_id, photo=PHOTO_SEPEHR_WIFE)
    elif message_text == "دیدن عکس سانسوری ساسی":
        await context.bot.send_photo(chat_id=user_id, photo=PHOTO_SASY_CENSORED)
    elif message_text == "دیدن عکس رونالدو و زنش":
        await context.bot.send_photo(chat_id=user_id, photo=PHOTO_RONALDO_WIFE)
    else:
        await update.message.reply_text("لطفاً یکی از گزینه‌های منو رو انتخاب کنید!")

    # نمایش دوباره منو بعد از هر عملیات
    await show_main_menu(update, context)

# تابع اصلی
def main():
    application = Application.builder().token(TOKEN).build()

    # هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
