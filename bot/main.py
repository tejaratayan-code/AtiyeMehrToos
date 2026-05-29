import asyncio
import os
import logging
import secrets
import string
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, MenuButtonWebApp, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode
from telegram.error import TelegramError

from shared.database import SessionLocal, User, get_or_create_user, Base, engine

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MINIAPP_URL = os.getenv("MINIAPP_URL", "https://miniapp.atiyemehrtoos.ir")
DOWNLOADS_DIR = "Downloads"
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Global bots for cross-platform sending
tg_bot = None
bale_bot = None

def generate_link_code(length=12):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db = SessionLocal()
    try:
        db_user = get_or_create_user(
            db,
            tg_id=user.id if 'tapi.bale.ai' not in str(context.bot.base_url) else None,
            bale_id=user.id if 'tapi.bale.ai' in str(context.bot.base_url) else None,
            username=user.username,
            first_name=user.first_name
        )
    finally:
        db.close()

    keyboard = [[InlineKeyboardButton("🚀 باز کردن مینی اپ", web_app=WebAppInfo(url=MINIAPP_URL))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"سلام {user.first_name}!\n\n"
        "به ربات آتیه مهر طوس خوش آمدید.\n"
        "• /link برای اتصال اکانت بله و تلگرام\n"
        "• /profile برای مشاهده پروفایل\n"
        "• فایل زیر ۲۰ مگ بفرستید تا به پلتفرم دیگر منتقل شود",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "دستورات ربات آتیه مهر طوس:\n\n"
        "/start - شروع و منو\n"
        "/link - دریافت کد اتصال بله ↔ تلگرام\n"
        "/profile - نمایش پروفایل کامل کاربر\n"
        "/help - این راهنما\n\n"
        "فایل (عکس، ویدیو، سند) زیر ۲۰ مگابایت بفرستید → به پلتفرم دیگر منتقل می‌شود.\n"
        "کد اتصال را از یک ربات کپی کرده و در ربات دیگر paste کنید."
    )

async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تولید کد اتصال و ارسال پیام connect:..."""
    user = update.effective_user
    platform = 'bale' if 'tapi.bale.ai' in str(context.bot.base_url) else 'tg'
    
    db = SessionLocal()
    try:
        db_user = get_or_create_user(
            db, 
            tg_id=user.id if platform == 'tg' else None,
            bale_id=user.id if platform == 'bale' else None,
            username=user.username,
            first_name=user.first_name
        )
        
        code = generate_link_code()
        db_user.link_code = code
        db_user.link_code_platform = platform
        db.commit()
        
        other_platform = 'Bale' if platform == 'tg' else 'Tel'
        connect_msg = f"connect:{other_platform}:UserID:{user.id}:{code}"
        
        await update.message.reply_text(
            f"✅ کد اتصال شما:\n\n"
            f"<code>{connect_msg}</code>\n\n"
            f"این پیام را کپی کنید و در ربات <b>{'تلگرام' if platform == 'bale' else 'بله'}</b> ارسال کنید.\n"
            "این کار اکانت‌های شما را به هم لینک می‌کند."
        , parse_mode=ParseMode.HTML)
    finally:
        db.close()

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    platform = 'bale' if 'tapi.bale.ai' in str(context.bot.base_url) else 'tg'
    
    db = SessionLocal()
    try:
        db_user = get_or_create_user(
            db,
            tg_id=user.id if platform == 'tg' else None,
            bale_id=user.id if platform == 'bale' else None
        )
        
        is_linked = bool(db_user.tg_user_id and db_user.bale_user_id)
        status = "✅ متصل" if is_linked else "❌ هنوز متصل نشده"
        
        profile_text = (
            f"👤 <b>پروفایل شما</b>\n\n"
            f"📅 تاریخ عضویت: {db_user.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"👤 نام کاربری: @{db_user.username or 'ندارد'}\n"
            f"🆔 یوزرنیم: {db_user.first_name}\n\n"
            f"🔗 وضعیت پل بله-تلگرام: {status}\n"
            f"🆔 ID تلگرام: {db_user.tg_user_id or 'ثبت نشده'}\n"
            f"🆔 ID بله: {db_user.bale_user_id or 'ثبت نشده'}\n\n"
            f"{'برای اتصال از دستور /link استفاده کنید.' if not is_linked else 'فایل‌ها و پیام‌ها بین دو پلتفرم سینک هستند.'}"
        )
        await update.message.reply_text(profile_text, parse_mode=ParseMode.HTML)
    finally:
        db.close()

async def connect_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر پیام‌های connect:... برای لینک کردن"""
    text = update.message.text.strip()
    if not text.startswith("connect:"):
        return
    
    parts = text.split(":")
    if len(parts) != 5:
        await update.message.reply_text("فرمت کد اشتباه است. لطفاً دقیقاً همان پیامی که از ربات دیگر دریافت کردید را ارسال کنید.")
        return
    
    _, target_platform, _, source_user_id_str, code = parts
    try:
        source_user_id = int(source_user_id_str)
    except ValueError:
        await update.message.reply_text("UserID باید عدد باشد.")
        return
    
    current_platform = 'bale' if 'tapi.bale.ai' in str(context.bot.base_url) else 'tg'
    current_user_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        # پیدا کردن کاربری که کد را تولید کرده
        source_user = db.query(User).filter(
            User.link_code == code,
            User.link_code_platform == ('tg' if target_platform.lower() == 'tel' else 'bale')
        ).first()
        
        if not source_user:
            await update.message.reply_text("کد منقضی یا نامعتبر است. دوباره /link بزنید.")
            return
        
        # لینک کردن
        if current_platform == 'tg':
            source_user.tg_user_id = current_user_id
        else:
            source_user.bale_user_id = current_user_id
        
        source_user.link_code = None
        source_user.link_code_platform = None
        source_user.linked_at = datetime.utcnow()
        db.commit()
        
        await update.message.reply_text(
            "🎉 اکانت‌های شما با موفقیت لینک شدند!\n"
            "حالا می‌توانید فایل بین بله و تلگرام منتقل کنید و پروفایل مشترک داشته باشید."
        )
        
    except Exception as e:
        logger.error(f"Error linking: {e}")
        await update.message.reply_text("خطا در لینک کردن. لطفاً دوباره تلاش کنید.")
    finally:
        db.close()

async def file_transfer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتقال فایل بین پلتفرم‌ها (زیر ۲۰ مگ)"""
    message = update.message
    user = update.effective_user
    platform = 'bale' if 'tapi.bale.ai' in str(context.bot.base_url) else 'tg'
    
    # تشخیص نوع فایل
    file = None
    file_name = "file"
    file_size = 0
    
    if message.document:
        file = message.document
        file_name = file.file_name or "document"
        file_size = file.file_size
    elif message.photo:
        file = message.photo[-1]  # بزرگترین سایز
        file_name = f"photo_{user.id}_{int(datetime.now().timestamp())}.jpg"
        file_size = file.file_size
    elif message.video:
        file = message.video
        file_name = file.file_name or "video.mp4"
        file_size = file.file_size
    else:
        return  # فقط فایل‌های پشتیبانی شده
    
    if file_size > 20 * 1024 * 1024:
        await message.reply_text("❌ فایل بزرگتر از ۲۰ مگابایت است. لطفاً فایل کوچک‌تر بفرستید.")
        return
    
    db = SessionLocal()
    try:
        db_user = get_or_create_user(
            db,
            tg_id=user.id if platform == 'tg' else None,
            bale_id=user.id if platform == 'bale' else None
        )
        
        if not (db_user.tg_user_id and db_user.bale_user_id):
            await message.reply_text("❌ ابتدا اکانت‌های بله و تلگرام را با دستور /link لینک کنید.")
            return
        
        # دانلود فایل
        file_obj = await context.bot.get_file(file.file_id)
        local_path = os.path.join(DOWNLOADS_DIR, file_name)
        await file_obj.download_to_drive(local_path)
        
        # تعیین پلتفرم و بات دیگر
        if platform == 'tg':
            other_bot = bale_bot
            other_chat_id = db_user.bale_user_id
            other_name = "بله"
        else:
            other_bot = tg_bot
            other_chat_id = db_user.tg_user_id
            other_name = "تلگرام"
        
        if not other_bot:
            await message.reply_text("خطای داخلی: بات دیگر در دسترس نیست.")
            os.remove(local_path)
            return
        
        # ارسال فایل به پلتفرم دیگر
        with open(local_path, 'rb') as f:
            await other_bot.send_document(
                chat_id=other_chat_id,
                document=InputFile(f, filename=file_name),
                caption=f"📎 فایل از {platform.upper()} دریافت شد"
            )
        
        os.remove(local_path)
        
        await message.reply_text(
            f"✅ فایل با موفقیت به اکانت {other_name} شما ارسال شد و از هاست حذف گردید."
        )
        
    except TelegramError as e:
        logger.error(f"Telegram error during file transfer: {e}")
        await message.reply_text("خطا در ارسال فایل به پلتفرم دیگر.")
        if os.path.exists(local_path):
            os.remove(local_path)
    except Exception as e:
        logger.error(f"Error in file transfer: {e}")
        await message.reply_text("خطای غیرمنتظره. لطفاً دوباره تلاش کنید.")
    finally:
        db.close()

def register_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("link", link_command))
    app.add_handler(CommandHandler("profile", profile_command))
    
    # هندلر connect
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, connect_handler))
    
    # هندلر فایل‌ها (سند، عکس، ویدیو)
    file_filter = filters.Document.ALL | filters.PHOTO | filters.VIDEO
    app.add_handler(MessageHandler(file_filter, file_transfer_handler))

async def main():
    global tg_bot, bale_bot
    
    tg_token = os.getenv("TG_TOKEN")
    bale_token = os.getenv("BALE_TOKEN")

    if not tg_token or not bale_token:
        raise ValueError("TG_TOKEN و BALE_TOKEN را در .env تنظیم کنید")

    # ساخت بات‌ها
    tg_app = ApplicationBuilder().token(tg_token).build()
    bale_app = (
        ApplicationBuilder()
        .token(bale_token)
        .base_url("https://tapi.bale.ai/bot")
        .base_file_url("https://tapi.bale.ai/file/bot")
        .build()
    )
    
    tg_bot = tg_app.bot
    bale_bot = bale_app.bot

    register_handlers(tg_app)
    register_handlers(bale_app)

    logger.info("🚀 ربات‌های بله و تلگرام در حال اجرا (با پشتیبانی از لینک و انتقال فایل)...")

    await tg_app.initialize()
    await bale_app.initialize()

    # منوی مینی‌اپ
    try:
        await tg_app.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="مینیاپ", web_app=WebAppInfo(url=MINIAPP_URL))
        )
        await bale_app.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="مینیاپ", web_app=WebAppInfo(url=MINIAPP_URL))
        )
    except Exception as e:
        logger.warning(f"تنظیم منو ممکن نشد: {e}")

    # اجرای همزمان
    tg_task = asyncio.create_task(tg_app.run_polling(allowed_updates=Update.ALL_TYPES))
    bale_task = asyncio.create_task(bale_app.run_polling(allowed_updates=Update.ALL_TYPES))

    await asyncio.gather(tg_task, bale_task)

if __name__ == "__main__":
    asyncio.run(main())