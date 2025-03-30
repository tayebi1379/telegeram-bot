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
# آیدی ادمین (باید آیدی عددی خودت رو بذاری)
ADMIN_ID = 1607082886  # آیدی عددی اکانت تلگرامت رو اینجا بذار

# فایل‌های JSON برای ذخیره عکس‌ها و کانال‌ها
PHOTO_FILE = 'photos.json'
CHANNEL_FILE = 'channels.json'

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

# بارگذاری کانال‌ها از فایل JSON یا مقداردهی اولیه
def load_channels():
    if os.path.exists(CHANNEL_FILE):
        with open(CHANNEL_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return ['@tehrankhabari_ir']  # کانال اولیه

# ذخیره کانال‌ها در فایل JSON
def save_channels(channels):
    with open(CHANNEL_FILE, 'w', encoding='utf-8') as f:
        json.dump(channels, f, ensure_ascii=False, indent=4)

# تابع بررسی عضویت کاربر در همه کانال‌ها
async def check_membership(context, user_id):
    channels = load_channels()
    for channel_id in channels:
        try:
            member = await context.bot.get_chat_member(channel_id, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except telegram.error.BadRequest:
            return False
    return True

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
    channels = load_channels()
    keyboard = [
        [InlineKeyboardButton(f"عضویت در {channel}", url=f'https://t.me/{channel[1:]}')] for channel in channels
    ]
    keyboard.append([InlineKeyboardButton("عضو شدم", callback_data='check_membership')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"برای دیدن عکس‌ها، لطفاً در کانال‌های زیر عضو بشید:\n" + "\n".join(channels),
        reply_markup=reply_markup
    )

# تابع مدیریت کلیک روی دکمه‌ها
async def button(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    print(f"Button clicked: {query.data}")  # دیباگ برای چک کردن ورودی

    if query.data == 'check_membership':
        if await check_membership(context, user_id):
            await query.answer("عضویت شما تأیید شد!")
            await show_main_menu(update, context)
        else:
            await query.answer("شما هنوز در همه کانال‌ها عضو نشدید!")
            channels = load_channels()
            keyboard = [
                [InlineKeyboardButton(f"عضویت در {channel}", url=f'https://t.me/{channel[1:]}')] for channel in channels
            ]
            keyboard.append([InlineKeyboardButton("عضو شدم", callback_data='check_membership')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(
                f"شما هنوز در همه کانال‌ها عضو نشدید! لطفاً عضو بشید و دوباره امتحان کنید:\n" + "\n".join(channels),
                reply_markup=reply_markup
            )
    elif query.data.startswith('delete_channel_'):
        if user_id != ADMIN_ID:
            await query.answer("شما ادمین نیستید!")
            return
        channel_id = query.data[len('delete_channel_'):]
        channels = load_channels()
        print(f"Attempting to delete channel: {channel_id}, Current channels: {channels}")  # دیباگ
        if channel_id in channels:
            channels.remove(channel_id)
            save_channels(channels)
            await query.answer(f"کانال '{channel_id}' حذف شد!")
            await query.message.edit_text(f"کانال '{channel_id}' با موفقیت حذف شد!")
        else:
            await query.answer("این کانال پیدا نشد!")
            await query.message.edit_text(f"کانال '{channel_id}' پیدا نشد!")
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
            await query.message.edit_text("عکس پیدا نشد!")

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
        await update.message.reply_text("لطفاً از فرمت زیر استفاده کنید:\n/addphoto [توضیحات] [لینک عکس]\nمثال: /addphoto \"عکس جدید\" https://example.com/photo.jpg")
        return

    args = " ".join(context.args).split(" ", 1)
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

# تابع اضافه کردن کانال جدید (فقط برای ادمین)
async def add_channel(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("شما ادمین نیستید و نمی‌تونید کانال اضافه کنید!")
        return

    if not context.args:
        await update.message.reply_text("لطفاً آیدی کانال رو وارد کنید:\n/addchannel @ChannelID")
        return

    channel_id = context.args[0].strip()
    if not channel_id.startswith('@'):
        await update.message.reply_text("آیدی کانال باید با @ شروع بشه، مثل @ChannelID")
        return

    channels = load_channels()
    if channel_id in channels:
        await update.message.reply_text("این کانال قبلاً اضافه شده!")
        return

    channels.append(channel_id)
    save_channels(channels)
    await update.message.reply_text(f"کانال '{channel_id}' اضافه شد!")

# تابع حذف کانال (فقط برای ادمین)
async def remove_channel(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("شما ادمین نیستید و نمی‌تونید کانال حذف کنید!")
        return

    channels = load_channels()
    if not channels:
        await update.message.reply_text("هیچ کانالی برای حذف وجود نداره!")
        return

    keyboard = [[InlineKeyboardButton(channel, callback_data=f'delete_channel_{channel}')] for channel in channels]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("کانالی که می‌خواهید حذف کنید رو انتخاب کنید:", reply_markup=reply_markup)

# تابع مدیریت انتخاب گزینه‌ها
async def handle_message(update, context):
    user_id = update.effective_user.id
    message_text = update.message.text
    photos = load_photos()

    if not await check_membership(context, user_id):
        channels = load_channels()
        keyboard = [
            [InlineKeyboardButton(f"عضویت در {channel}", url=f'https://t.me/{channel[1:]}')] for channel in channels
        ]
        keyboard.append([InlineKeyboardButton("عضو شدم", callback_data='check_membership')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"شما هنوز در همه کانال‌ها عضو نشدید! لطفاً عضو بشید:\n" + "\n".join(channels),
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
    application.add_handler(CommandHandler("addchannel", add_channel))
    application.add_handler(CommandHandler("removechannel", remove_channel))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button))

    # شروع سرور HTTP برای Render
    threading.Thread(target=run_server, daemon=True).start()

    # شروع ربات
    application.run_polling()

if __name__ == '__main__':
    main()
