import telegram
import os
import asyncio
from pymongo import MongoClient
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# توکن و تنظیمات
TOKEN = os.getenv('TOKEN')
MONGO_URI = os.getenv('MONGO_URI')
ADMIN_ID = 1607082886

# اتصال به MongoDB
client = MongoClient(MONGO_URI)
db = client['telegram_bot']
photos_collection = db['photos']
channels_collection = db['channels']
users_collection = db['users']

# توابع دیتابیس
def initialize_db():
    if photos_collection.count_documents({}) == 0:
        photos_collection.insert_one({
            "data": {
                "🤐دیدن عکس زن سپهر حیدری🤐": "https://cdn.rokna.net/thumbnail/...",
                "🤯دیدن عکس سانسوری ساسی😳": "https://cdn.rokna.net/thumbnail/...",
                "😬دیدن عکس رونالدو و زنش😵": "https://cdn.rokna.net/servev2/...",
                "😍دیدن عکس علی دایی و زنش🫢": "https://cdn.pishnahadevizheh.com/servev2/..."
            }
        })
    if channels_collection.count_documents({}) == 0:
        channels_collection.insert_one({"data": ['@tehrankhabari_ir']})
    if users_collection.count_documents({}) == 0:
        users_collection.insert_one({"users": [], "banned": []})

def load_photos():
    doc = photos_collection.find_one()
    return doc["data"] if doc else {}

def save_photos(photos):
    photos_collection.update_one({}, {"$set": {"data": photos}}, upsert=True)

def load_channels():
    doc = channels_collection.find_one()
    return doc["data"] if doc else []

def save_channels(channels):
    channels_collection.update_one({}, {"$set": {"data": channels}}, upsert=True)

def load_users():
    doc = users_collection.find_one()
    return doc if doc else {"users": [], "banned": []}

def save_users(users):
    users_collection.update_one({}, {"$set": {"users": users["users"], "banned": users["banned"]}}, upsert=True)

# تابع بررسی عضویت
async def is_member(context, user_id, channel_id):
    try:
        member = await context.bot.get_chat_member(channel_id, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except telegram.error.BadRequest:
        return None

async def check_membership(context, user_id):
    channels = load_channels()
    for channel_id in channels:
        status = await is_member(context, user_id, channel_id)
        if status is False:
            return False
    return True

def is_banned(user_id):
    users = load_users()
    return str(user_id) in users["banned"]

async def show_main_menu(update, context):
    photos = load_photos()
    keyboard = [[key] for key in photos.keys()]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    if update.message:
        await update.message.reply_text('منوی اصلی:', reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text('منوی اصلی:', reply_markup=reply_markup)

# دستور شروع
async def start(update, context):
    user_id = update.effective_user.id
    username = update.effective_user.username or "بدون نام کاربری"
    
    users = load_users()
    if str(user_id) not in [user["id"] for user in users["users"]]:
        users["users"].append({"id": str(user_id), "username": username})
        save_users(users)

    if is_banned(user_id):
        await update.message.reply_text("شما از ربات بلاک شده‌اید!")
        return

    channels = load_channels()
    keyboard = []
    can_check = True
    for channel in channels:
        status = await is_member(context, context.bot.id, channel)
        if status is None:
            can_check = False
            keyboard.append([InlineKeyboardButton(f"عضویت در {channel}", url=f'https://t.me/{channel[1:]}')])
    
    keyboard.append([InlineKeyboardButton("✅ تأیید عضویت ✅", callback_data='check_membership')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "**سلام دوست عزیزم 😊**\n"
        "**خـــوش اومـــــدی 🌹**\n"
        "برای مشاهده پست لطفاً توی کانال‌ها عضو شو و دکمه تأیید رو بزن ☺",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# مدیریت دکمه‌ها
async def button(update, context):
    query = update.callback_query
    user_id = query.from_user.id

    if is_banned(user_id):
        await query.answer("شما از ربات بلاک شده‌اید!")
        return

    if query.data == 'check_membership':
        channels = load_channels()
        can_check = True
        not_member_channels = []
        
        for channel in channels:
            status = await is_member(context, context.bot.id, channel)
            if status is None:
                can_check = False
                break
            elif not await is_member(context, user_id, channel):
                not_member_channels.append(channel)

        if can_check and not not_member_channels:
            await query.answer("❤️ عضویت شما تأیید شد ❤️")
            await show_main_menu(update, context)
        elif not can_check:
            await query.answer("عضویتت رو چک کردیم، خوش اومدی!")
            await show_main_menu(update, context)
        else:
            await query.answer("🔴 شما هنوز توی همه کانال‌ها عضو نشدید 🔴")
            keyboard = []
            for channel in not_member_channels:
                keyboard.append([InlineKeyboardButton(f"عضویت در {channel}", url=f'https://t.me/{channel[1:]}')])
            keyboard.append([InlineKeyboardButton("✅ تأیید ✅", callback_data='check_membership')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(
                "**لطفاً توی کانال‌های زیر عضو شو و تأیید رو بزن:**",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

# توابع مدیریتی
async def add_photo(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("شما ادمین نیستید!")
        return
    if len(context.args) < 2:
        await update.message.reply_text("لطفاً از فرمت زیر استفاده کنید:\n/addphoto [توضیحات] [لینک عکس]")
        return
    args = " ".join(context.args).split(" ", 1)
    description = args[0].strip()
    photo_url = args[1].strip()
    photos = load_photos()
    photos[description] = photo_url
    save_photos(photos)
    await update.message.reply_text(f"عکس با توضیح '{description}' اضافه شد!")

async def remove_photo(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("شما ادمین نیستید!")
        return
    photos = load_photos()
    if not photos:
        await update.message.reply_text("هیچ عکسی برای حذف وجود نداره!")
        return
    keyboard = [[InlineKeyboardButton(key, callback_data=f'delete_{key}')] for key in photos.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("عکسی که می‌خواهید حذف کنید رو انتخاب کنید:", reply_markup=reply_markup)

async def add_channel(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("شما ادمین نیستید!")
        return
    if not context.args:
        await update.message.reply_text("لطفاً آیدی کانال رو وارد کنید:\n/addchannel @ChannelID")
        return
    channel_id = context.args[0].strip()
    if not channel_id.startswith('@'):
        await update.message.reply_text("آیدی کانال باید با @ شروع بشه!")
        return
    channels = load_channels()
    if channel_id in channels:
        await update.message.reply_text("این کانال قبلاً اضافه شده!")
        return
    channels.append(channel_id)
    save_channels(channels)
    await update.message.reply_text(f"کانال '{channel_id}' اضافه شد!")

async def remove_channel(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("شما ادمین نیستید!")
        return
    channels = load_channels()
    if not channels:
        await update.message.reply_text("هیچ کانالی برای حذف وجود نداره!")
        return
    keyboard = [[InlineKeyboardButton(channel, callback_data=f'delete_channel_{channel}')] for channel in channels]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("کانالی که می‌خواهید حذف کنید رو انتخاب کنید:", reply_markup=reply_markup)

async def users(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("شما ادمین نیستید!")
        return
    users = load_users()
    if not users["users"]:
        await update.message.reply_text("هیچ کاربری ثبت نشده!")
        return
    user_list = "\n".join([f"ID: {user['id']} - @{user['username']}" for user in users["users"]])
    await update.message.reply_text(f"لیست کاربران:\n{user_list}")

async def user_count(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("شما ادمین نیستید!")
        return
    users = load_users()
    count = len(users["users"])
    await update.message.reply_text(f"تعداد کاربران: {count}")

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
    if target_id not in users["banned"]:
        users["banned"].append(target_id)
        save_users(users)
        await update.message.reply_text(f"کاربر با آیدی {target_id} بلاک شد!")
    else:
        await update.message.reply_text("این کاربر قبلاً بلاک شده!")

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
            if await is_member(context, context.bot.id, channel) is None:
                keyboard.append([InlineKeyboardButton(f"عضویت در {channel}", url=f'https://t.me/{channel[1:]}')])
        keyboard.append([InlineKeyboardButton("✅ تأیید ✅", callback_data='check_membership')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "**لطفاً توی کانال‌ها عضو شو و تأیید رو بزن:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return

    if message_text in photos:
        photo_message = await context.bot.send_photo(chat_id=user_id, photo=photos[message_text])
        delete_message = await context.bot.send_message(chat_id=user_id, text="این عکس پس از ۳۰ ثانیه حذف می‌شود")
        asyncio.create_task(delete_after_delay(context.bot, user_id, photo_message.message_id, delete_message.message_id))
    else:
        await update.message.reply_text("لطفاً یکی از گزینه‌های منو رو انتخاب کنید!")
    await show_main_menu(update, context)

async def delete_after_delay(bot, chat_id, photo_message_id, delete_message_id):
    await asyncio.sleep(30)
    await bot.delete_message(chat_id=chat_id, message_id=photo_message_id)
    await bot.delete_message(chat_id=chat_id, message_id=delete_message_id)

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot is running')

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

def run_server():
    server = HTTPServer(('0.0.0.0', 8080), SimpleHandler)
    server.serve_forever()

def main():
    initialize_db()
    application = Application.builder().token(TOKEN).build()

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

    threading.Thread(target=run_server, daemon=True).start()
    application.run_polling()

if __name__ == '__main__':
    main()
