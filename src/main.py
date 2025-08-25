import os
import logging
from typing import Optional, Set
from dotenv import load_dotenv
from telegram import Update, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from trmnl_utils import TrmnlUtils
from pdf_utils import (
    get_pdf_file_name,
    convert_pdf_to_images,
    get_pdf_page_image,
    build_pdf_nav_keyboard
)
from epub_utils import convert_epub_to_pdf
from bot_utils import BotMessageHandler, BotAuthHandler, TRMNLHandler

load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TRMNL_CONFIG = {
    "WIDTH": int(os.getenv("TRMNL_WIDTH", "480")),
    "HEIGHT": int(os.getenv("TRMNL_HEIGHT", "800")),
    "API_BASE": os.getenv("TRMNL_API_BASE", "https://usetrmnl.com/api"),
    "PLUGIN_UUID": os.getenv("TRMNL_PLUGIN_UUID", "")
}

FILTER_USER_IDS: Set[str] = {
    uid.strip() 
    for uid in os.getenv("FILTER_USER_IDS", "").split(",") 
    if uid.strip()
}

# Initialize TRMNL utility client
trmnl_utils = TrmnlUtils(TRMNL_CONFIG["API_BASE"], TRMNL_CONFIG["PLUGIN_UUID"])

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.WARNING
)

logger = logging.getLogger(__name__)

async def process_pdf_page(
    context: ContextTypes.DEFAULT_TYPE,
    update: Update,
    user_id: int,
    file_name: str,
    page: int,
    total_pages: Optional[int] = None,
    reply_photo: bool = True
) -> None:
    try:
        if not os.path.exists(file_name):
            await BotMessageHandler.send_error(
                update, 
                "PDF file not found or access denied.",
                f"File not found: {file_name}"
            )
            return

        images = convert_pdf_to_images(file_name)
        if not images:
            await BotMessageHandler.send_error(
                update,
                "Failed to convert PDF to images.",
                f"PDF conversion failed: {file_name}"
            )
            return

        if page < 1 or page > len(images):
            await BotMessageHandler.send_error(
                update,
                f"Page {page} is out of range (1-{len(images)})."
            )
            return

        img_byte_array = get_pdf_page_image(images, page)
        total_pages = total_pages or len(images)
        keyboard = build_pdf_nav_keyboard(page, total_pages, user_id)

        try:
            response = (
                await update.message.reply_photo(photo=img_byte_array, reply_markup=keyboard)
                if reply_photo
                else await update.edit_message_media(
                    media=InputMediaPhoto(img_byte_array),
                    reply_markup=keyboard
                )
            )
        except Exception as e:
            await BotMessageHandler.send_error(
                update,
                "Failed to send image. Please try again.",
                f"Failed to send/edit message: {str(e)}"
            )
            return

        file_id = response.photo[-1].file_id if hasattr(response, 'photo') and response.photo else None
        if not file_id:
            await BotMessageHandler.send_error(
                update,
                "Failed to process image",
                "No image file_id found in response"
            )
            return

        await TRMNLHandler(trmnl_utils).process_trmnl_response(context, update, file_id)

    except Exception as e:
        await BotMessageHandler.send_error(
            update,
            "An error occurred while processing the PDF.",
            f"An unexpected error occurred: {str(e)}"
        )

async def handle_pdf_page_nav(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not (query and query.data and update.effective_user):
        logger.warning("Invalid callback query or user")
        return

    user_id = update.effective_user.id
    if not await BotAuthHandler.validate_user_authorization(user_id, update, FILTER_USER_IDS):
        return

    try:
        if not query.data.startswith(("pdf_prev_", "pdf_next_")) or len(query.data.split("_")) != 5:
            await query.answer("Invalid navigation format")
            return

        try:
            _, _, page_str, total_pages_str, _ = query.data.split("_")
            await process_pdf_page(
                context=context,
                update=query,
                user_id=user_id,
                file_name=get_pdf_file_name(user_id),
                page=int(page_str),
                total_pages=int(total_pages_str),
                reply_photo=False
            )
            await query.answer()

        except (ValueError, IndexError) as e:
            await BotMessageHandler.send_error(
                update,
                "Invalid page information",
                f"Error parsing navigation data: {str(e)}"
            )

    except Exception as e:
        await BotMessageHandler.send_error(
            update,
            "Navigation failed. Please try again.",
            f"Error in PDF navigation: {str(e)}"
        )

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle image messages and send them to TRMNL"""
    if not (update.message and update.message.photo):
        logger.warning("Received image handler call without photo")
        return

    user_id = getattr(update.effective_user, 'id', None)
    if not user_id or not await BotAuthHandler.validate_user_authorization(user_id, update, FILTER_USER_IDS):
        await BotMessageHandler.send_error(update, "Could not identify user")
        return

    try:
        # Get the highest resolution photo
        photo = update.message.photo[-1]
        file_id = photo.file_id
        
        # Show processing message
        processing_msg = await update.message.reply_text("📤 Sending image to TRMNL...")
        
        # Send to TRMNL
        await TRMNLHandler(trmnl_utils).process_trmnl_response(context, update, file_id)
        
        # Update message to show success
        await processing_msg.edit_text("✅ Image sent to TRMNL successfully!")
        
    except Exception as e:
        await BotMessageHandler.send_error(
            update,
            "An error occurred while processing your image.",
            f"Unexpected error in image handler: {str(e)}"
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not (update.message and update.message.document):
        logger.warning("Received document handler call without document")
        return

    user_id = getattr(update.effective_user, 'id', None)
    if not user_id or not await BotAuthHandler.validate_user_authorization(user_id, update, FILTER_USER_IDS):
        await BotMessageHandler.send_error(update, "Could not identify user")
        return

    SUPPORTED_TYPES = {
        'application/pdf': '.pdf',
        'application/epub+zip': '.epub'
    }

    document = update.message.document
    if document.mime_type not in SUPPORTED_TYPES:
        await BotMessageHandler.send_error(
            update,
            "Unsupported file type. Please send an image, PDF, or EPUB file."
        )
        return

    try:
        ext = SUPPORTED_TYPES[document.mime_type]
        original_file = f"{user_id}_original{ext}"
        pdf_file = get_pdf_file_name(user_id)

        try:
            file = await document.get_file()
            await file.download_to_drive(original_file)
        except Exception as e:
            await BotMessageHandler.send_error(
                update,
                "Failed to download the file. Please try again.",
                f"Error downloading file: {str(e)}"
            )
            return

        try:
            if ext == '.epub':
                await update.message.reply_text("Converting EPUB to PDF...")
                convert_epub_to_pdf(original_file, pdf_file)
            else:
                os.rename(original_file, pdf_file)
        except Exception as e:
            await BotMessageHandler.send_error(
                update,
                "Failed to process the file. Please try again.",
                f"Error processing file: {str(e)}"
            )
            return
        finally:
            if os.path.exists(original_file):
                os.remove(original_file)

        await process_pdf_page(context, update, user_id, pdf_file, page=1)

    except Exception as e:
        await BotMessageHandler.send_error(
            update,
            "An error occurred while processing your document.",
            f"Unexpected error in document handler: {str(e)}"
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_message = (
        "👋 Welcome to the Telegram to TRMNL Bot!\n\n"
        "Send me any of the following and I'll display it on your TRMNL:\n"
        "• Images (JPG, PNG, GIF, etc.)\n"
        "• PDF files (with page navigation)\n"
        "• EPUB files (automatically converted to PDF)"
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_message = (
        "� *Telegram to TRMNL Bot Help*\n\n"
        "*Supported Content:*\n"
        "• 🖼️ Images: Send any image to display on TRMNL\n"
        "• 📄 PDF files: Navigate through pages with buttons\n"
        "• 📚 EPUB files: Auto-converted to PDF format\n\n"
        "*How to use:*\n"
        "1. Send your content (image/PDF/EPUB)\n"
        "2. For PDFs: Use navigation buttons to browse pages\n"
        "3. Content is automatically sent to your TRMNL display\n\n"
        "For more information, visit:\n"
        "https://github.com/yazdipour/trmnl-telegram-bot-pdf"
    )
    await update.message.reply_text(help_message, parse_mode='Markdown')

def setup_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    
    # Handle images
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    
    # Handle documents (PDF/EPUB)
    document_filter = filters.Document.PDF | filters.Document.FileExtension("epub")
    app.add_handler(MessageHandler(document_filter, handle_document))
    
    # Handle PDF navigation
    app.add_handler(CallbackQueryHandler(handle_pdf_page_nav))

def main() -> None:
    try:
        if not TELEGRAM_BOT_TOKEN:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in the environment.")

        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        setup_handlers(app)
        logger.info("Starting bot...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")
        raise

if __name__ == "__main__":
    main()
