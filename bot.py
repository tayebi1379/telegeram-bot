import telegram
import os
import asyncio
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# توکن ربات از متغیر محیطی
TOKEN = os.getenv('TOKEN')
# آیدی کانال (با @)
CHANNEL_ID = '@tehrankhabari_ir'

# لینک عکس‌ها
PHOTO_SEPEHR_WIFE = 'https://cdn.rokna.net/thumbnail/wOmsWjeamneO/yYGYIWiRH1jE7SFsFf8OS8GtVdPr30fs0wJj5HjN1IuvcJmljcN6H8bAsgVZzpzYCc2Paf9tWNyagVuk0QlPbNxB-KuYdy9P6xL39i3G-Q82HeI91mK-78F62Z5KWk3gNl6RwvjtxurVX_hzZe6NzQ,,/%D8%B3%D9%BE%D9%87%D8%B1+%D8%AD%DB%8C%D8%AF%D8%B1%DB%8C.jpg'
PHOTO_SASY_CENSORED = 'https://cdn.rokna.net/thumbnail/mHTJunUTOoEL/yYGYIWiRH1jE7SFsFf8OS8GtVdPr30fs0wJj5HjN1IuvcJmljcN6H8bAsgVZzpzYCc2Paf9tWNyagVuk0QlPbNxB-KuYdy9P6xL39i3G-Q82HeI91mK-78F62Z5KWk3gWiOBV6O9LT4lqjAfWapFmw,,/%D8%B3%D8%A7%D8%B3%DB%8C+%D9%85%D8%A7%D9%86%DA%A9%D9%86.jpg'
PHOTO_RONALDO_WIFE = 'https://cdn.rokna.net/servev2/f6VBCVS65xWu/Db2f077dXpA,/%D8%B1%D9%88%D9%86%D8%A7%D9%84%D8%AF%D9%88+%D9%88+%D9%87%D9%85%D8%B3%D8%B1%D8%B4.jpg'

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
    keyboard = [
        ["دیدن عکس زن سپهر حیدری"],
        ["دیدن عکس سانسوری ساسی"],
        ["دیدن عکس رونالدو و زنش"]
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
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
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await show_main_menu(update, context)

# تابع جداگانه برای حذف پیام‌ها بعد از ۳۰ ثانیه
async def delete_after_delay(bot, chat_id, photo_message_id, delete_message_id):
    await asyncio.sleep(30)
    await bot.delete_message(chat_id=chat_id, message_id=photo_message_id)
    await bot.delete_message(chat_id=chat_id, message_id=delete_message_id)

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

    # ارسال عکس و پیام حذف
    if message_text == "دیدن عکس زن سپهر حیدری":
        photo_message = await context.bot.send_photo(chat_id=user_id, photo=PHOTO_SEPEHR_WIFE)
        delete_message = await context.bot.send_message(chat_id=user_id, text="این عکس پس از ۳۰ ثانیه حذف می‌شود")
        # اجرای حذف در پس‌زمینه
        asyncio.create_task(delete_after_delay(context.bot, user_id, photo_message.message_id, delete_message.message_id))
        
    elif message_text == "دیدن عکس سانسوری ساسی":
        photo_message = await context.bot.send_photo(chat_id=user_id, photo=PHOTO_SASY_CENSORED)
        delete_message = await context.bot.send_message(chat_id=user_id, text="این عکس پس از ۳۰ ثانیه حذف می‌شود")
        asyncio.create_task(delete_after_delay(context.bot, user_id, photo_message.message_id, delete_message.message_id))
        
    elif message_text == "دیدن عکس رونالدو و زنش":
        photo_message = await context.bot.send_photo(chat_id=user_id, photo=PHOTO_RONALDO_WIFE)
        delete_message = await context.bot.send_message(chat_id=user_id, text="این عکس پس از ۳۰ ثانیه حذف می‌شود")
        asyncio.create_task(delete_after_delay(context.bot, user_id, photo_message.message_id, delete_message.message_id))
        
    else:
        await update.message.reply_text("لطفاً یکی از گزینه‌های منو رو انتخاب کنید!")

    # نمایش دوباره منو بلافاصله
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
