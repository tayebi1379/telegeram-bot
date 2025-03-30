import telegram
import os
import asyncio
import json
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# توکن ربات از متغیر محیطی
TOKEN = os.getenv('TOKEN')
# آیدی کانال (با @)
CHANNEL_ID = '@tehrankhabari_ir'
# آیدی ادمین (باید آیدی عددی خودت رو بذاری)
ADMIN_ID = 123456789  # آیدی عددی اکانت تلگرامت رو اینجا بذار

# فایل JSON برای ذخیره عکس‌ها
PHOTO_FILE = 'photos.json'

# بارگذاری عکس‌ها از فایل JSON یا مقداردهی اولیه
def load_photos():
    if os.path.exists(PHOTO_FILE):
        with open(PHOTO_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "🤐دیدن عکس زن سپهر حیدری🤐": "https://cdn.rokna.net/thumbnail/wOmsWjeamneO/yYGYIWiRH1jE7SFsFf8OS8GtVdPr30fs0wJj5HjN1IuvcJmljcN6H8bAsgVZzpzYCc2Paf9tWNyagVuk0QlPbNxB-KuYdy9P6xL39i3G-Q82HeI91mK-78F62Z5KWk3gNl6RwvjtxurVX_hzZe6NzQ,,/%D8%B3%D9%BE%D9%87%D8%B1+%D8%AD%DB%8C%D8%AF%D8%B1%DB%8C.jpg",
        "🤯دیدن عکس سانسوری ساسی😳": "https://cdn.rokna.net/thumbnail/mHTJunUTOoEL/yYGYIWiRH1jE7SFsFf8OS8GtVdPr30fs0wJj5HjN1IuvcJmljcN6H8bAsgVZzpzYCc2Paf9tWNyagVuk0QlPbNxB-KuYdy9P6xL39i3G-Q82HeI91mK-78F62Z5KWk3gWiOBV6O9LT4lqjAfWapFmw,,/%D8%B3%D8%A7%D8%B3%DB%8C+%D9%85%D8%A7%D9%86%DA%A9%D9%86.jpg",
        "😬دیدن عکس رونالدو و زنش😵": "https://cdn.rokna.net/servev2/f6VBCVS65xWu/Db2f077dXpA,/%D8%B1%D9%88%D9%86%D8%A7%D9%84%D8%AF%D9%88+%D9%88+%D9%87%D9%85%D8%B3%D8%B1%D8%B4.jpg",
        "😍دیدن عکس علی دایی و زنش🫢": "https://cdn.pishnahadevizheh.com/servev2/KGj3qrulKNsb/MnvWRFh5dGY,/%D8%B9%D9%84%DB%8C+%D8%AF%D8%A7%DB%8C%DB%8C.jpg"
    }

# ذخیره عکس‌ها در فایل JSON
def save_photos(photos):
    with open(PHOTO_FILE, 'w', encoding='utf-8') as f:
        json.dump(photos, f, ensure_ascii=False, indent=4)

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
    photos = load_photos()
    keyboard = [[key] for key in photos.keys()]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    if update.message:
        await update.message.reply_text('منوی اصلی:', reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text('منوی اصلی:', reply_markup=reply_markup)

# تابع شروع ربات با اینلاین کیبورد
async def start(update, context):
    user_id = update.effective_user.id
    join_url = f'https://t.me/{CHANNEL_ID[1:]}'
    keyboard = [
        [InlineKeyboardButton("عضویت در کانال", url=join_url)],
        [InlineKeyboardButton("عضو شدم", callback_data='check_membership')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"برای دیدن عکس‌ها، لطفاً در کانال {CHANNEL_ID} عضو بشید!",
        reply_markup=reply_markup
    )

# تابع مدیریت کلیک روی دکمه‌ها
async def button(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    if query.data == 'check_membership':
        if await check_membership(context, user_id):
            await query.answer("عضویت شما تأیید شد!")
            await show_main_menu(update, context)
        else:
            await query.answer("شما هنوز عضو کانال نشدید!")
            join_url = f'https://t.me/{CHANNEL_ID[1:]}'
            keyboard = [
                [InlineKeyboardButton("عضویت در کانال", url=join_url)],
                [InlineKeyboardButton("عضو شدم", callback_data='check_membership')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(
                f"شما هنوز در کانال {CHANNEL_ID} عضو نشدید! لطفاً عضو بشید و دوباره امتحان کنید.",
                reply_markup=reply_markup
            )
    elif query.data.startswith('delete_'):
        if user_id != ADMIN_ID:
            await query.answer("شما ادمین نیستید!")
            return
        photo_key = query.data[len('delete_'):]
        photos = load_photos()
        if photo_key in photos:
            del photos[photo_key]
            save_photos(photos)
            await query.answer(f"عکس '{photo_key}' حذف شد!")
            await query.message.edit_text("عکس با موفقیت حذف شد!")
        else:
            await query.answer("این عکس پیدا نشد!")

# تابع حذف پیام‌ها بعد از ۳۰ ثانیه
async def delete_after_delay(bot, chat_id, photo_message_id, delete_message_id):
    await asyncio.sleep(30)
    await bot.delete_message(chat_id=chat_id, message_id=photo_message_id)
    await bot.delete_message(chat_id=chat_id, message_id=delete_message_id)

# تابع اضافه کردن عکس جدید (فقط برای ادمین)
async def add_photo(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("شما ادمین نیستید و نمی‌تونید عکس اضافه کنید!")
        return

    if len(context.args) < 2:
        await update.message.reply_text("لطفاً از فرمت زیر استفاده کنید:\n/addphoto [توضیحات] [لینک عکس]\nمثال: /addphoto \"عکس جدید\" https://example.com/photo.jpg\nتوضیحات چند کلمه‌ای رو توی \" نقل‌قول \" بذارید.")
        return

    # گرفتن توضیحات و لینک با پشتیبانی از چند کلمه
    args = " ".join(context.args).split(" ", 1)  # جدا کردن اولین بخش (توضیحات) از بقیه (لینک)
    description = args[0].strip()
    photo_url = args[1].strip() if len(args) > 1 else ""
    
    if not photo_url:
        await update.message.reply_text("لطفاً لینک عکس رو بعد از توضیحات وارد کنید!")
        return

    photos = load_photos()
    photos[description] = photo_url
    save_photos(photos)
    await update.message.reply_text(f"عکس با توضیح '{description}' اضافه شد!")

# تابع حذف عکس (فقط برای ادمین)
async def remove_photo(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("شما ادمین نیستید و نمی‌تونید عکس حذف کنید!")
        return

    photos = load_photos()
    if not photos:
        await update.message.reply_text("هیچ عکسی برای حذف وجود نداره!")
        return

    keyboard = [[InlineKeyboardButton(key, callback_data=f'delete_{key}')] for key in photos.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("عکسی که می‌خواهید حذف کنید رو انتخاب کنید:", reply_markup=reply_markup)

# تابع مدیریت انتخاب گزینه‌ها
async def handle_message(update, context):
    user_id = update.effective_user.id
    message_text = update.message.text
    photos = load_photos()

    if not await check_membership(context, user_id):
        join_url = f'https://t.me/{CHANNEL_ID[1:]}'
        keyboard = [
            [InlineKeyboardButton("عضویت در کانال", url=join_url)],
            [InlineKeyboardButton("عضو شدم", callback_data='check_membership')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"شما هنوز در کانال {CHANNEL_ID} عضو نشدید! لطفاً عضو بشید.",
            reply_markup=reply_markup
        )
        return

    if message_text in photos:
        try:
            photo_message = await context.bot.send_photo(chat_id=user_id, photo=photos[message_text])
            delete_message = await context.bot.send_message(chat_id=user_id, text="این عکس پس از ۳۰ ثانیه حذف می‌شود")
            asyncio.create_task(delete_after_delay(context.bot, user_id, photo_message.message_id, delete_message.message_id))
        except telegram.error.BadRequest as e:
            await update.message.reply_text(f"خطا در نمایش عکس: {e}. لطفاً مطمئن شوید لینک معتبر است.")
    else:
        await update.message.reply_text("لطفاً یکی از گزینه‌های منو رو انتخاب کنید!")
    
    await show_main_menu(update, context)

# سرور ساده برای Render
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot is running')

def run_server():
    server = HTTPServer(('0.0.0.0', 8080), SimpleHandler)
    server.serve_forever()

# تابع اصلی
def main():
    application = Application.builder().token(TOKEN).build()

    # هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addphoto", add_photo))
    application.add_handler(CommandHandler("removephoto", remove_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button))

    # شروع سرور HTTP برای Render
    threading.Thread(target=run_server, daemon=True).start()

    # شروع ربات
    application.run_polling()

if __name__ == '__main__':
    main()
