from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, User

from bot.db import Repo


class DbUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        repo: Repo = data["repo"]
        from_user: None | User = data.get("event_from_user")
        if from_user:
            user = await repo.get_user(user_id=from_user.id)
            if user:
                user.full_name = from_user.full_name
                user.username = from_user.username
                repo.session.add(user)
                await repo.session.commit()
        else:
            user = None

        data["user"] = user

        return await handler(event, data)
