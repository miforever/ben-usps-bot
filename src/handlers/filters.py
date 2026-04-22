from aiogram import types
from aiogram.filters import BaseFilter

from src.config import get_settings


class PrivateChatOnlyFilter(BaseFilter):
    """Only allow messages from private chats."""

    async def __call__(self, message: types.Message) -> bool:
        return message.chat.type == "private"


class IsAdminFilter(BaseFilter):
    """Only allow messages from users listed in ADMIN_IDS."""

    async def __call__(self, message: types.Message) -> bool:
        if not message.from_user:
            return False
        return message.from_user.id in get_settings().ADMIN_IDS
