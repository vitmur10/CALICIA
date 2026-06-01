import calendar
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
from bot.db.models import User
from bot.structrures.callback_data import UserData, AdminExtractAllData
from bot.structrures.bot import months

def universal(text: str, callback_data: CallbackData | str):
    kb = InlineKeyboardBuilder()

    kb.button(text=text, callback_data=callback_data)

    return kb.as_markup()


def menu():
    kb = InlineKeyboardBuilder()

    kb.button(text='Користувачі', switch_inline_query_current_chat='user:')
    kb.button(text='↻ Оновити товари', callback_data='update_goods')
    kb.button(text='📊 Звіт по всіх партнерах', callback_data='extract_all_partners')
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

def all_partners_years_kb():
    kb = InlineKeyboardBuilder()

    current_year = datetime.now().year

    for year in [current_year, current_year - 1, current_year - 2]:
        kb.button(
            text=str(year),
            callback_data=AdminExtractAllData(year=year)
        )

    kb.adjust(3)
    return kb.as_markup()

def all_partners_months_kb(year: int):
    kb = InlineKeyboardBuilder()

    for i, month in enumerate(months):
        kb.button(
            text=month,
            callback_data=AdminExtractAllData(year=year, month=i)
        )

    kb.adjust(3, 3, 3, 3)
    return kb.as_markup()


def all_partners_weeks(month: int, year: int):
    kb = InlineKeyboardBuilder()

    if month - 1 >= 0:
        kb.button(
            text='«',
            callback_data=AdminExtractAllData(year=year, month=month - 1)
        )
    else:
        kb.button(text=' ', callback_data='noop')

    kb.button(text=months[month], callback_data='noop')

    if month + 1 < 12:
        kb.button(
            text='»',
            callback_data=AdminExtractAllData(year=year, month=month + 1)
        )
    else:
        kb.button(text=' ', callback_data='noop')

    month_weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month + 1)

    for week in month_weeks:
        start_of_week = week[0]
        end_of_week = week[6]

        kb.button(
            text=f'{start_of_week.day} - {end_of_week.day}',
            callback_data=AdminExtractAllData(
                year=year,
                month=month,
                week=f'{str(start_of_week.month).zfill(2)}.{str(start_of_week.day).zfill(2)} - {str(end_of_week.month).zfill(2)}.{str(end_of_week.day).zfill(2)}'
            )
        )

    kb.button(text='« Назад', callback_data='admin_menu')

    kb.adjust(3, *[2] * len(month_weeks), 1)
    return kb.as_markup()