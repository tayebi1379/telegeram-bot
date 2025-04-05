import telegram
import os
import asyncio
from pymongo import MongoClient
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# توکن ربات و MongoDB URI از متغیر محیطی
TOKEN = os.getenv('TOKEN')
MONGO_URI = os.getenv('MONGO_URI')
# آیدی ادمین
ADMIN_ID = 1607082886

# اتصال به MongoDB
client = MongoClient(MONGO_URI)
db = client['telegram_bot']
photos_collection = db['photos']
channels_collection = db['channels']
users_collection = db['users']

# مقداردهی اولیه دیتابیس اگه خالی باشه
def initialize_db():
    if photos_collection.count_documents({}) == 0:
        photos_collection.insert_one({
            "data": {
                "🤐دیدن عکس زن سپهر حیدری🤐": "https://cdn.rokna.net/thumbnail/wOmsWjeamneO/yYGYIWiRH1jE7SFsFf8OS8GtVdPr30fs0wJj5HjN1IuvcJmljcN6H8bAsgVZzpzYCc2Paf9tWNyagVuk0QlPbNxB-KuYdy9P6xL39i3G-Q82HeI91mK-78F62Z5KWk3gNl6RwvjtxurVX_hzZe6NzQ,,/%D8%B3%D9%BE%D9%87%D8%B1+%D8%AD%DB%8C%D8%AF%D8%B1%DB%8C.jpg",
                "🤯دیدن عکس سانسوری ساسی😳": "https://cdn.rokna.net/thumbnail/mHTJunUTOoEL/yYGYIWiRH1jE7SFsFf8OS8GtVdPr30fs0wJj5HjN1IuvcJmljcN6H8bAsgVZzpzYCc2Paf9tWNyagVuk0QlPbNxB-KuYdy9P6xL39i3G-Q82HeI91mK-78F62Z5KWk3gWiOBV6O9LT4lqjAfWapFmw,,/%D8%B3%D8%A7%D8%B3%DB%8C+%D9%85%D8%A7%D9%86%DA%A9%D9%86.jpg",
                "😬دیدن عکس رونالدو و زنش😵": "https://cdn.rokna.net/servev2/f6VBCVS65xWu/Db2f077dXpA,/%D8%B1%D9%88%D9%86%D8%A7%D9%84%D8%AF%D9%88+%D9%88+%D9%87%D9%85%D8%B3%D8%B1%D8%B4.jpg",
                "😍دیدن عکس علی دایی و زنش🫢": "https://cdn.pishnahadevizheh.com/servev2/KGj3qrulKNsb/MnvWRFh5dGY,/%D8%B9%D9%84%DB%8C+%D8%AF%D8%A7%DB%8C%DB%8C.jpg"
            }
        })
    if channels_collection.count_documents({}) == 0:
        channels_collection.insert_one({"data": ['@tehrankhabari_ir']})
    if users_collection.count_documents({}) == 0:
        users_collection.insert_one({"users": [], "banned": []})

# بارگذاری عکس‌ها از MongoDB
def load_photos():
    doc = photos_collection.find_one()
    return doc["data"] if doc else {}

# ذخیره عکس‌ها در MongoDB
def save_photos(photos):
    photos_collection.update_one({}, {"$set": {"data": photos}}, upsert=True)

# بارگذاری کانال‌ها از MongoDB
def load_channels():
    doc = channels_collection.find_one()
    return doc["data"] if doc else []

# ذخیره کانال‌ها در MongoDB
def save_channels(channels):
    channels_collection.update_one({}, {"$set": {"data": channels}}, upsert=True)

# بارگذاری کاربران از MongoDB
def load_users():
    doc = users_collection.find_one()
    return doc if doc else {"users": [], "banned": []}

# ذخیره کاربران در MongoDB
def save_users(users):
    users_collection.update_one({}, {"$set": {"users": users["users"], "banned": users["banned"]}}, upsert=True)

# تابع منوی مدیریتی
async def modir(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("شما ادمین نیستید!")
        return

    keyboard = [
        [InlineKeyboardButton("اضافه کردن عکس", callback_data='add_photo')],
        [InlineKeyboardButton("حذف عکس", callback_data='remove_photo')],
        [InlineKeyboardButton("اضافه کردن کانال", callback_data='add_channel')],
        [InlineKeyboardButton("حذف کانال", callback_data='remove_channel')],
        [InlineKeyboardButton("لیست کاربران", callback_data='list_users')],
        [InlineKeyboardButton("تعداد کاربران", callback_data='count_users')],
        [InlineKeyboardButton("بلاک کاربر", callback_data='ban_user')],
        [InlineKeyboardButton("رفع بلاک کاربر", callback_data='unban_user')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("منوی مدیریت ربات:", reply_markup=reply_markup)

# تابع بررسی عضویت کاربر در یک کانال خاص
async def is_member(context, user_id, channel_id):
    try:
        member = await context.bot.get_chat_member(channel_id, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except telegram.error.BadRequest:
        return False

# تابع بررسی عضویت کاربر در همه کانال‌ها
async def check_membership(context, user_id):
    channels = load_channels()
    for channel_id in channels:
        if not await is_member(context, user_id, channel_id):
            return False
    return True

# تابع بررسی بلاک بودن کاربر
def is_banned(user_id):
    users = load_users()
    return str(user_id) in users["banned"]

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
    username = update.effective_user.username or "بدون نام کاربری"
    
    # ذخیره کاربر جدید
    users = load_users()
    if str(user_id) not in [user["id"] for user in users["users"]]:
        users["users"].append({"id": str(user_id), "username": username})
        save_users(users)

    if is_banned(user_id):
        await update.message.reply_text("شما از ربات بلاک شده‌اید!")
        return

    channels = load_channels()
    keyboard = []
    for channel in channels:
        if not await is_member(context, user_id, channel):
            keyboard.append([InlineKeyboardButton("👈عــضــویــت👉", url=f'https://t.me/{channel[1:]}')])
    keyboard.append([InlineKeyboardButton("✅تایید✅", callback_data='check_membership')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "**سلام دوست عزیزم 😊**\n"
        "**خـــوش اومـــــدی 🌹**\n"
        "برای مشاهده پست لطفا اینجاها جوین شو و دکمه تأیید رو بزن ☺",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# تابع نمایش لیست کاربران (فقط برای ادمین)
async def users(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("شما ادمین نیستید!")
        return

    users = load_users()
    if not users["users"]:
        await update.message.reply_text("هیچ کاربری هنوز ثبت نشده!")
        return

    user_list = "\n".join([f"ID: {user['id']} - @{user['username']}" for user in users["users"]])
    await update.message.reply_text(f"لیست کاربران:\n{user_list}")

# تابع نمایش تعداد کاربران (فقط برای ادمین)
async def user_count(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("شما ادمین نیستید!")
        return

    users = load_users()
    count = len(users["users"])
    await update.message.reply_text(f"تعداد کاربران: {count}")

# تابع بلاک کردن کاربر (فقط برای ادمین)
async def ban(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("شما ادمین نیستید!")
        return

    if not context.args:
        await update.message.reply_text("لطفاً آیدی کاربر رو وارد کنید:\n/ban <user_id>")
        return

    target_id = context.args[0]
    users = load_users()
    if target_id in [user["id"] for user in users["users"]]:
        if target_id not in users["banned"]:
            users["banned"].append(target_id)
            save_users(users)
            await update.message.reply_text(f"کاربر با آیدی {target_id} بلاک شد!")
        else:
            await update.message.reply_text("این کاربر قبلاً بلاک شده!")
    else:
        await update.message.reply_text("این کاربر پیدا نشد!")

# تابع رفع بلاک کاربر (فقط برای ادمین)
async def unban(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("شما ادمین نیستید!")
        return

    if not context.args:
        await update.message.reply_text("لطفاً آیدی کاربر رو وارد کنید:\n/unban <user_id>")
        return

    target_id = context.args[0]
    users = load_users()
    if target_id in users["banned"]:
        users["banned"].remove(target_id)
        save_users(users)
        await update.message.reply_text(f"کاربر با آیدی {target_id} از بلاک خارج شد!")
    else:
        await update.message.reply_text("این کاربر بلاک نشده بود!")

# تابع مدیریت کلیک روی دکمه‌ها
async def button(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    print(f"Button clicked: {query.data}")

    if is_banned(user_id):
        await query.answer("شما از ربات بلاک شده‌اید!")
        return

    if query.data == 'check_membership':
        if await check_membership(context, user_id):
            await query.answer("❤️عضویت شما تأیید شد❤️")
            await show_main_menu(update, context)
        else:
            await query.answer("🔴شما هنوز در همه کانال‌ها عضو نشدید🔴")
            channels = load_channels()
            keyboard = []
            for channel in channels:
                if not await is_member(context, user_id, channel):
                    keyboard.append([InlineKeyboardButton("👈عــضــویــت👉", url=f'https://t.me/{channel[1:]}')])
            keyboard.append([InlineKeyboardButton("✅تایید✅", callback_data='check_membership')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(
                "**سلام دوست عزیزم 😊**\n"
                "**خـــوش اومـــــدی 🌹**\n"
                "برای مشاهده پست لطفا اینجاها جوین شو و دکمه تأیید رو بزن ☺",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    elif query.data.startswith('delete_channel_'):
        if user_id != ADMIN_ID:
            await query.answer("شما ادمین نیستید!")
            return
        channel_id = query.data[len('delete_channel_'):]
        channels = load_channels()
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
    # مدیریت دکمه‌های جدید منوی /modir
    elif query.data == 'add_photo':
        await query.answer()
        await query.message.edit_text("لطفاً از فرمت زیر استفاده کنید:\n/addphoto [توضیحات] [لینک عکس]\nمثال: /addphoto \"عکس جدید\" https://example.com/photo.jpg")
    elif query.data == 'remove_photo':
        if user_id != ADMIN_ID:
            await query.answer("شما ادمین نیستید!")
            return
        photos = load_photos()
        if not photos:
            await query.answer("هیچ عکسی برای حذف وجود نداره!")
            await query.message.edit_text("هیچ عکسی برای حذف وجود نداره!")
        else:
            keyboard = [[InlineKeyboardButton(key, callback_data=f'delete_{key}')] for key in photos.keys()]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text("عکسی که می‌خواهید حذف کنید رو انتخاب کنید:", reply_markup=reply_markup)
    elif query.data == 'add_channel':
        await query.answer()
        await query.message.edit_text("لطفاً آیدی کانال رو وارد کنید:\n/addchannel @ChannelID")
    elif query.data == 'remove_channel':
        if user_id != ADMIN_ID:
            await query.answer("شما ادمین نیستید!")
            return
        channels = load_channels()
        if not channels:
            await query.answer("هیچ کانالی برای حذف وجود نداره!")
            await query.message.edit_text("هیچ کانالی برای حذف وجود نداره!")
        else:
            keyboard = [[InlineKeyboardButton(channel, callback_data=f'delete_channel_{channel}')] for channel in channels]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text("کانالی که می‌خواهید حذف کنید رو انتخاب کنید:", reply_markup=reply_markup)
    elif query.data == 'list_users':
        if user_id != ADMIN_ID:
            await query.answer("شما ادمین نیستید!")
            return
        users = load_users()
        if not users["users"]:
            await query.answer("هیچ کاربری ثبت نشده!")
            await query.message.edit_text("هیچ کاربری هنوز ثبت نشده!")
        else:
            user_list = "\n".join([f"ID: {user['id']} - @{user['username']}" for user in users["users"]])
            await query.message.edit_text(f"لیست کاربران:\n{user_list}")
    elif query.data == 'count_users':
        if user_id != ADMIN_ID:
            await query.answer("شما ادمین نیستید!")
            return
        users = load_users()
        count = len(users["users"])
        await query.message.edit_text(f"تعداد کاربران: {count}")
    elif query.data == 'ban_user':
        await query.answer()
        await query.message.edit_text("لطفاً آیدی کاربر رو وارد کنید:\n/ban <user_id>")
    elif query.data == 'unban_user':
        await query.answer()
        await query.message.edit_text("لطفاً آیدی کاربر رو وارد کنید:\n/unban <user_id>")

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

    if is_banned(user_id):
        await update.message.reply_text("شما از ربات بلاک شده‌اید!")
        return

    if not await check_membership(context, user_id):
        channels = load_channels()
        keyboard = []
        for channel in channels:
            if not await is_member(context, user_id, channel):
                keyboard.append([InlineKeyboardButton("👈عــضــویــت👉", url=f'https://t.me/{channel[1:]}')])
        keyboard.append([InlineKeyboardButton("✅تایید✅", callback_data='check_membership')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "**سلام دوست عزیزم 😊**\n"
            "**خـــوش اومـــــدی 🌹**\n"
            "برای مشاهده پست لطفا اینجاها جوین شو و دکمه تأیید رو بزن ☺",
            reply_markup=reply_markup,
            parse_mode='Markdown'
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
    # مقداردهی اولیه دیتابیس
    initialize_db()

    application = Application.builder().token(TOKEN).build()

    # هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addphoto", add_photo))
    application.add_handler(CommandHandler("removephoto", remove_photo))
    application.add_handler(CommandHandler("addchannel", add_channel))
    application.add_handler(CommandHandler("removechannel", remove_channel))
    application.add_handler(CommandHandler("users", users))
    application.add_handler(CommandHandler("usercount", user_count))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("unban", unban))
    application.add_handler(CommandHandler("modir", modir))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button))

    # شروع سرور HTTP برای Render
    threading.Thread(target=run_server, daemon=True).start()

    # شروع ربات
    application.run_polling()

if __name__ == '__main__':
    main()
