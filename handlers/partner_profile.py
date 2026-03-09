from datetime import date

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

