import logging

from aiogram import Router, Bot, F
from aiogram.exceptions import TelegramBadRequest, TelegramNotFound, TelegramForbiddenError
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import ChatMemberUpdated, Message, CallbackQuery

from bot.config import Config
from bot.db import Repo
from bot.db.models import User

from bot.keyboards import user as kb
from bot.keyboards import admin as admin_kb

router = Router()


@router.message(CommandStart())
@router.callback_query(F.data == 'cancel')
async def start(message: Message | CallbackQuery, state: FSMContext, repo: Repo, user: User, config: Config, bot: Bot):
    await state.clear()

    if not user:
        user = await repo.add_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
        await bot.send_message(chat_id=config.channel.users, text="🔔 <b>Реєстрація користувача</b>:\n"
                                                                  f"<b>» ID</b>:  {message.from_user.id}\n"
                                                                  f"<b>» Нік</b>:  {message.from_user.full_name}\n"
                                                                  f"{f'<b>» Юзернейм</b>:  @{message.from_user.username}' if message.from_user.username else ''}", reply_markup=admin_kb.new_user(user))

    if user.is_partner:
        if message.__class__ == CallbackQuery:
            try:
                await message.message.delete()
            except Exception:
                pass
            await message.message.answer('🤝 <b>Меню партнера</b>: ', reply_markup=kb.menu())
            return

        await message.answer('🤝 <b>Меню партнера</b>: ', reply_markup=kb.menu())
