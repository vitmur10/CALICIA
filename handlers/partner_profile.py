from datetime import date, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile

from bot.api.swagger import SwaggerCRM
from bot.db.models import User
from bot.structrures.bot import generate_file
from bot.structrures.callback_data import ExtractData
from bot.filters.partner import PartnerFilter

import bot.keyboards.user as kb

router = Router()

router.message.filter(PartnerFilter())
router.callback_query.filter(PartnerFilter())


@router.message(F.text == '💼 Профіль')
@router.callback_query(F.data == 'to_profile')
async def partner_profile(message: Message | CallbackQuery):
    if message.__class__ == CallbackQuery:
        await message.message.edit_text('💼 Профіль партнера: ', reply_markup=kb.profile())
    else:
        await message.answer('💼 Профіль партнера: ', reply_markup=kb.profile())


@router.callback_query(ExtractData.filter())
async def extract(query: CallbackQuery, callback_data: ExtractData, user: User, swagger: SwaggerCRM):

    if callback_data.year is None:

        await query.message.edit_text(
            "⏱️ Оберіть рік:",
            reply_markup=kb.years_kb()
        )

        return


    if callback_data.month is None:

        await query.message.edit_text(
            "⏱️ Оберіть місяць:",
            reply_markup=kb.months_kb(callback_data.year)
        )

        return


    if callback_data.week is None:

        await query.message.edit_text(
            "⏱️ Оберіть тиждень:",
            reply_markup=kb.weeks(callback_data.month, callback_data.year)
        )

        return


    data = callback_data.week.split(' - ')

    if date(
            year=callback_data.year,
            month=int(data[0].split('.')[0]),
            day=int(data[0].split('.')[1])
    ) > date.today():

        await query.answer(
            '⚠️ Оберіть дату, яка не належить до майбутнього',
            show_alert=True
        )

        return


    await query.message.edit_text('Генеруємо файл...')

    res = await generate_file(
        swagger,
        user.source,
        user.source_name,
        data,
        callback_data.year
    )


    if res[0]:

        await query.message.delete()

        await query.message.answer_document(
            document=FSInputFile(res[0]),
            caption=f'📁 Виписку за <b>{callback_data.year}.{data[0]} - {data[1]}</b> згенеровано'
        )

    else:

        await query.message.edit_text(
            res[1],
            reply_markup=kb.universal(
                '« Назад',
                'to_profile'
            )
        )

@router.callback_query(F.data == "reports_menu")
async def reports_menu(query: CallbackQuery):

    await query.message.edit_text(
        "📊 Оберіть тип звіту:",
        reply_markup=kb.quick_reports()
    )

@router.callback_query(F.data == "report_this_week")
async def report_this_week(query: CallbackQuery, user: User, swagger: SwaggerCRM):

    today = date.today()

    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)

    data = [
        f"{str(start.month).zfill(2)}.{str(start.day).zfill(2)}",
        f"{str(end.month).zfill(2)}.{str(end.day).zfill(2)}"
    ]

    await query.message.edit_text("Генеруємо файл...")

    res = await generate_file(
        swagger,
        user.source,
        user.source_name,
        data,
        today.year
    )

    if res[0]:

        await query.message.delete()

        await query.message.answer_document(
            document=FSInputFile(res[0]),
            caption="📅 Виписка за цей тиждень"
        )


@router.callback_query(F.data == "report_this_month")
async def report_this_month(query: CallbackQuery, user: User, swagger: SwaggerCRM):

    today = date.today()

    start = date(today.year, today.month, 1)

    if today.month == 12:
        end = date(today.year, 12, 31)
    else:
        end = date(today.year, today.month + 1, 1) - timedelta(days=1)

    data = [
        f"{str(start.month).zfill(2)}.{str(start.day).zfill(2)}",
        f"{str(end.month).zfill(2)}.{str(end.day).zfill(2)}"
    ]

    await query.message.edit_text("Генеруємо файл...")

    res = await generate_file(
        swagger,
        user.source,
        user.source_name,
        data,
        today.year
    )

    if res[0]:

        await query.message.delete()

        await query.message.answer_document(
            document=FSInputFile(res[0]),
            caption="📆 Виписка за цей місяць"
        )

@router.callback_query(F.data == "report_this_year")
async def report_this_year(query: CallbackQuery, user: User, swagger: SwaggerCRM):

    today = date.today()

    data = [
        "01.01",
        "12.31"
    ]

    await query.message.edit_text("Генеруємо файл...")

    res = await generate_file(
        swagger,
        user.source,
        user.source_name,
        data,
        today.year
    )

    if res[0]:

        await query.message.delete()

        await query.message.answer_document(
            document=FSInputFile(res[0]),
            caption="📊 Виписка за рік"
        )