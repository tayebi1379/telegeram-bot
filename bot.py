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

# توابع دیتابیس (بدون تغییر)
def initialize_db():
    if photos_collection.count_documents({}) == 0:
        photos_collection.insert_one({"data": {...}})  # داده‌های اولیه
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
    except telegram.error.BadRequest:  # اگه ربات مدیر نباشه یا دسترسی نداشته باشه
        return None  # None یعنی نمی‌تونیم چک کنیم

async def check_membership(context, user_id):
    channels = load_channels()
    for channel_id in channels:
        status = await is_member(context, user_id, channel_id)
        if status is False:  # کاربر عضو نیست
            return False
        # اگه status None بود (ربات مدیر نیست)، بعداً با دکمه تأیید می‌کنیم
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
        status = await is_member(context, context.bot.id, channel)  # چک می‌کنیم ربات عضو/مدیر هست یا نه
        if status is None:  # ربات نمی‌تونه خودش رو چک کنه (یعنی مدیر نیست)
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
            if status is None:  # ربات مدیر نیست
                can_check = False
                break
            elif not await is_member(context, user_id, channel):
                not_member_channels.append(channel)

        if can_check and not not_member_channels:  # ربات مدیره و کاربر توی همه کانال‌ها عضوه
            await query.answer("❤️ عضویت شما تأیید شد ❤️")
            await show_main_menu(update, context)
        elif not can_check:  # ربات مدیر نیست
            await query.answer("عضویتت رو چک کردیم، خوش اومدی!")
            await show_main_menu(update, context)  # مستقیم منو رو نشون می‌دیم
        else:  # ربات مدیره ولی کاربر توی همه کانال‌ها نیست
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
    # بقیه کدها (مثل delete_channel و modir) بدون تغییر

# بقیه توابع (مثل addchannel، modir و ...) بدون تغییر باقی می‌مونن

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
