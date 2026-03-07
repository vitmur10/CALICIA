from datetime import datetime, date, timedelta
from math import ceil, floor

from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from bot.structrures.bot import months, months_length
from bot.structrures.callback_data import ExtractData


def universal(text: str, callback_data: str | CallbackData | None):
    kb = InlineKeyboardBuilder()

    kb.button(text=text, callback_data=callback_data)

    return kb.as_markup()


def menu():
    kb = ReplyKeyboardBuilder()

    kb.button(text='🛒 Замовлення')
    kb.button(text='💼 Профіль')
    kb.adjust(1)

    return kb.as_markup(resize_keyboard=True)


def goods(has_goods: bool = False):
    kb = InlineKeyboardBuilder()

    kb.button(text="Перелік товарів", switch_inline_query_current_chat='')
    if has_goods:
        kb.button(text="Далі »", callback_data='to_fullname')
    kb.button(text='❌ Відхилити', callback_data='cancel')
    kb.adjust(1)

    return kb.as_markup()


def back(callback_data: CallbackData | str):
    kb = InlineKeyboardBuilder()

    kb.button(text='« Назад', callback_data=callback_data)
    kb.button(text='❌ Відхилити', callback_data='cancel')
    kb.adjust(1)

    return kb.as_markup()


def inline_switcher(text: str, callback: CallbackData | str):
    kb = InlineKeyboardBuilder()

    kb.button(text=text, switch_inline_query_current_chat='')
    kb.button(text='« Назад', callback_data=callback)
    kb.button(text='❌ Відхилити', callback_data='cancel')
    kb.adjust(1)

    return kb.as_markup()


def comment_order():
    kb = InlineKeyboardBuilder()

    kb.button(text='Пропустити', callback_data='skip_comment')
    kb.button(text='« Назад', callback_data='to_warehouse')
    kb.button(text='❌ Відхилити', callback_data='cancel')
    kb.adjust(1)

    return kb.as_markup()


def finish_order():
    kb = InlineKeyboardBuilder()

    kb.button(text='Додати', callback_data='add_order')
    kb.button(text='« Назад', callback_data='to_comment')
    kb.button(text='❌ Відхилити', callback_data='cancel')
    kb.adjust(1)

    return kb.as_markup()


def profile():
    kb, now = InlineKeyboardBuilder(), datetime.now()

    kb.button(text='⏱️ Виписка', callback_data=ExtractData(month=now.month - 1))
    kb.button(text='❌ Закрити', callback_data='cancel')
    kb.adjust(1)

    return kb.as_markup()


def weeks(month: int):
    kb = InlineKeyboardBuilder()

    if month - 1 >= 0:
        kb.button(text='«', callback_data=ExtractData(month=month-1))
    else:
        kb.button(text=' ', callback_data=' ')
    kb.button(text=months[month], callback_data=ExtractData())
    if month + 1 < 12:
        kb.button(text='»', callback_data=ExtractData(month=month+1))
    else:
        kb.button(text=' ', callback_data=' ')

    for i in range(5 if month in (2, 5, 7, 10) else 4):
        today = date(year=2025, month=month + 1, day=i * 7 + 1)
        weekday = today.weekday()

        start_of_week = today - timedelta(days=weekday)
        end_of_week = start_of_week + timedelta(days=6)

        kb.button(text=f'{start_of_week.day} - {end_of_week.day}', callback_data=ExtractData(month=month, week=f'{str(start_of_week.month).zfill(2)}.{str(start_of_week.day).zfill(2)} - {str(end_of_week.month).zfill(2)}.{str(end_of_week.day).zfill(2)}'))

    kb.button(text='« Назад', callback_data='to_profile')
    kb.adjust(3, 2, 2, 1)

    return kb.as_markup()


def months_kb():
    kb = InlineKeyboardBuilder()

    for month in months:
        kb.button(text=month, callback_data=ExtractData(month=months.index(month)))

    kb.adjust(3, 3, 3, 3)

    return kb.as_markup()
