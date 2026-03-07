from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.db.models import User
from bot.structrures.callback_data import UserData


def universal(text: str, callback_data: CallbackData | str):
    kb = InlineKeyboardBuilder()

    kb.button(text=text, callback_data=callback_data)

    return kb.as_markup()


def menu():
    kb = InlineKeyboardBuilder()

    kb.button(text='Користувачі', switch_inline_query_current_chat='user:')
    kb.button(text='↻ Оновити товари', callback_data='update_goods')
    kb.adjust(1)

    return kb.as_markup()


def new_user(u: User):
    kb = InlineKeyboardBuilder()

    kb.button(text='👤 Про користувача', callback_data=UserData(id=u.id))
    kb.button(text='👥 Зробити користувачем' if u.is_partner else '👥 Зробити партнером', callback_data=UserData(id=u.id, action='demote' if u.is_partner else 'promote'))
    kb.adjust(1)

    return kb.as_markup()


def user(u: User):
    kb = InlineKeyboardBuilder()

    kb.button(text='Профіль', url=u.url)
    kb.button(text='👥 Зробити користувачем' if u.is_partner else '👥 Зробити партнером', callback_data=UserData(id=u.id, action='demote' if u.is_partner else 'promote'))
    kb.button(text='👑 Забрати права адміна' if u.is_admin else '👑 Надати права адміна', callback_data=UserData(id=u.id, action='is_admin'))
    if u.is_partner:
        kb.button(text=f'🌀 Джерело: {u.source_name}', callback_data=UserData(id=u.id, action='promote'))
    kb.adjust(1)

    return kb.as_markup()


def sources_list(u: User, sources: dict):
    kb = InlineKeyboardBuilder()

    for source_id in sources.keys():
        kb.button(text=sources[source_id], callback_data=UserData(id=u.id, action='source', int_value=source_id))
    kb.button(text='« Назад', callback_data=UserData(id=u.id))
    kb.adjust(1)

    return kb.as_markup()

