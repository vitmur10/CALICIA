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
    if callback_data.week:
        data = callback_data.week.split(' - ')
        start = data[0].split('.')
        start_date = date(year=2025, month=int(start[0]), day=int(start[1]))
        if start_date > date.today():
            await query.answer('⚠️ Оберіть дату, яка не належить до майбутнього', show_alert=True)
            return
        else:
            await query.message.edit_text('Генеруємо файл...')
            res = await generate_file(swagger, user.source, user.source_name, data)
            if res[0]:
                await query.message.delete()
                await query.message.answer_document(document=FSInputFile(res[0]), caption=f'📁 Виписку за <b>2025.{data[0]} - {data[1]}</b> згенеровано')
            else:
                await query.message.edit_text(res[1], reply_markup=kb.universal('« Назад', 'to_profile'))

    elif callback_data.month or callback_data.month == 0:
        await query.message.edit_text('⏱️ Оберіть тиждень для виписки: ', reply_markup=kb.weeks(callback_data.month))
    else:
        await query.message.edit_text('⏱️ Оберіть місяць: ', reply_markup=kb.months_kb())

