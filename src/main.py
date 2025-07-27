import os
import logging
from dotenv import load_dotenv
from telegram import Update, InputMediaPhoto
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
from trmnl_utils import TrmnlUtils
from pdf_utils import (
    get_pdf_file_name,
    convert_pdf_to_images,
    get_pdf_page_image,
    build_pdf_nav_keyboard
)
load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TRMNL_API_BASE: str = os.getenv("TRMNL_API_BASE", "https://usetrmnl.com/api")
TRMNL_PLUGIN_UUID: str = os.getenv("TRMNL_PLUGIN_UUID", "")
FILTER_USER_IDS_RAW: str = os.getenv("FILTER_USER_IDS", "")
FILTER_USER_IDS = set(uid.strip() for uid in FILTER_USER_IDS_RAW.split(",") if uid.strip()) if FILTER_USER_IDS_RAW else set()

trmnl_utils = TrmnlUtils(TRMNL_API_BASE, TRMNL_PLUGIN_UUID)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG, 
)

async def validate_user_authorization(user_id, update):
    if FILTER_USER_IDS and str(user_id) not in FILTER_USER_IDS:
        await update.message.reply_text("To start, send your ebook here.")
        return False
    return True

async def process_pdf_page(context, update, user_id, file_name, page, total_pages=None, reply_photo=True):
    if not os.path.exists(file_name):
        if update:
            await update.message.reply_text("PDF file not found.")
        return
    images = convert_pdf_to_images(file_name)
    if page < 1 or page > len(images):
        if update:
            await update.message.reply_text("Page out of range.")
        return
    img_byte_array = get_pdf_page_image(images, page)
    if not total_pages:
        total_pages = len(images)
    keyboard = build_pdf_nav_keyboard(page, total_pages, user_id)
    if reply_photo:
        response = await update.message.reply_photo(photo=img_byte_array, reply_markup=keyboard)
    else:
        response = await update.edit_message_media(
            media=InputMediaPhoto(img_byte_array),
            reply_markup=keyboard
        )
    # Get the file_id of the highest resolution image
    file_id = response.photo[-1].file_id if hasattr(response, 'photo') and response.photo else None
    if not file_id:
        if update:
            await update.message.reply_text("No image file_id found.")
        return
    file = await context.bot.get_file(file_id)
    image_url = file.file_path
    success, error = trmnl_utils.send_image_to_webhook(image_url)
    if not success and update:
        await update.message.reply_text(f"Failed to send image URL to TRMNL: {error}")
    elif not success:
        logging.error(f"Failed to send image URL to TRMNL: {error}")

async def handle_pdf_page_nav(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle PDF page navigation callbacks (next/prev)."""
    query = update.callback_query
    if not query or not query.data:
        return
    user_id = update.effective_user.id if update.effective_user else 'unknown'
    if not await validate_user_authorization(user_id, update):
        return
    data = query.data
    if data.startswith("pdf_prev_") or data.startswith("pdf_next_"):
        parts = data.split("_")
        if len(parts) != 5:
            await query.answer("Invalid navigation data.")
            return
        _, _, page_str, total_pages_str, _ = parts
        try:
            page = int(page_str)
            total_pages = int(total_pages_str)
        except ValueError:
            await query.answer("Invalid page info.")
            return
        file_name = get_pdf_file_name(user_id)
        await process_pdf_page(context, query, user_id, file_name, page, total_pages, reply_photo=False)
        await query.answer()

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Convert a PDF to images and send the first page with navigation buttons."""
    document = update.message.document
    user_id = update.effective_user.id if update.effective_user else 'unknown'
    if not await validate_user_authorization(user_id, update):
        return
    if document and document.mime_type == 'application/pdf':
        file = await document.get_file()
        file_name = get_pdf_file_name(user_id)
        await file.download_to_drive(file_name)
        current_page = 1
        await process_pdf_page(context, update, user_id, file_name, current_page)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("To start, send your ebook here.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Get more information from https://github.com/yazdipour/TEBT")

def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in the environment.")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.add_handler(CallbackQueryHandler(handle_pdf_page_nav))

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
