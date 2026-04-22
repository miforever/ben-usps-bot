import asyncio
import logging
from datetime import datetime

from aiogram import Bot
from aiogram.enums import ParseMode

from src.config import get_settings

logger = logging.getLogger(__name__)


class ErrorNotifier:
    """Throttled error notifications to admin users."""

    def __init__(self):
        self.last_notification_time = datetime.min
        self.lock = asyncio.Lock()

    async def notify(self, error_message: str, bot: Bot):
        settings = get_settings()
        if not settings.ERROR_NOTIFICATION_ENABLED:
            return

        async with self.lock:
            current_time = datetime.now()
            time_since_last = (current_time - self.last_notification_time).total_seconds()

            if time_since_last < settings.ERROR_NOTIFICATION_DELAY:
                logger.debug(f"Skipping notification, only {time_since_last}s since last")
                return

            self.last_notification_time = current_time

        truncated = error_message[:3500]
        formatted_message = (
            f"🚨 <b>Bot Error Alert</b> 🚨\n\n"
            f"<pre>{truncated}</pre>\n\n"
            f"<b>Time:</b> {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        for user_id in settings.ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=formatted_message,
                    parse_mode=ParseMode.HTML,
                )
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
