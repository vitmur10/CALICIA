from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from bot.db.models import User


class AdminFilter(BaseFilter):
    async def __call__(self, event: TelegramObject, user: None | User):
        return user.is_admin if user else False


class AdminInlineFilter(BaseFilter):
    async def __call__(self, event: TelegramObject, user: None | User):
        return user.is_admin and event.query.startswith('user:') if user else False
