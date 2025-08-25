from typing import Optional, Any, Set
from telegram import Update
import logging

logger = logging.getLogger(__name__)

class BotMessageHandler:
    @staticmethod
    async def send_error(update: Optional[Update], message: str, log_message: Optional[str] = None) -> None:
        if log_message:
            logger.error(log_message)
        if update and hasattr(update, 'message'):
            await update.message.reply_text(message)
        elif update and hasattr(update, 'callback_query'):
            await update.callback_query.answer(message)

class BotAuthHandler:
    @staticmethod
    async def validate_user_authorization(user_id: int, update: Update, filter_user_ids: Set[str]) -> bool:
        if filter_user_ids and str(user_id) not in filter_user_ids:
            await update.message.reply_text("Unauthorized. Access denied.")
            logger.warning(f"Unauthorized access attempt by user {user_id}")
            return False
        return True

class TRMNLHandler:
    def __init__(self, trmnl_utils):
        self.trmnl_utils = trmnl_utils

    async def process_trmnl_response(self, context: Any, update: Update, file_id: str) -> None:
        try:
            file = await context.bot.get_file(file_id)
            success, error = self.trmnl_utils.send_image_to_webhook(file.file_path)
            if not success:
                await BotMessageHandler.send_error(
                    update,
                    "Failed to send to TRMNL. Please check your TRMNL configuration.",
                    f"Failed to send image to TRMNL: {error}"
                )
            else:
                logger.info(f"Successfully sent image to TRMNL: {file.file_path}")
        except Exception as e:
            await BotMessageHandler.send_error(
                update,
                "Failed to process image for TRMNL",
                f"Error processing TRMNL response: {str(e)}"
            )
