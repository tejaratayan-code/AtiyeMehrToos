from telegram import Update
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)

# Add web_app_data handler
async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.message.web_app_data.data
    logger.info(f"Received mini app data: {data}")
    await update.message.reply_text(f"داده از مینی اپ دریافت شد: {data}")