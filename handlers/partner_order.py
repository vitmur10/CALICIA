import uuid
from datetime import datetime, timedelta

import pytz
from aiogram import Router, F, Bot
from aiogram.filters.command import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ErrorEvent, ChatMemberUpdated, InlineQuery, InlineQueryResultArticle, \
    InputTextMessageContent

from bot.api.novaposhta import NovaPoshta
from bot.api.swagger import SwaggerCRM
from bot.config import Config
from bot.db import Repo
from bot.db.models import User
from bot.filters.partner import PartnerFilter

import bot.keyboards.user as kb
from bot.structrures.states import NewOrder

router = Router()

router.message.filter(PartnerFilter())
router.callback_query.filter(PartnerFilter())


@router.message(F.text == '🛒 Замовлення')
async def add_order(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(NewOrder.goods)
    msg = await message.answer("► Натисніть кнопку нижче та оберіть товар. За потреби Ви можете ввести у пошуку назву товару або його артикул: ", reply_markup=kb.goods())
    await state.update_data(msg_id=msg.message_id)


@router.inline_query(NewOrder.goods)
async def new_order(query: InlineQuery, repo: Repo):
    data = await repo.get_goods(query.query)
    results = [InlineQueryResultArticle(id=good.id, title=f"{good.name} - {good.price} грн.", description=good.description, input_message_content=InputTextMessageContent(message_text=good.id, parse_mode="HTML"), thumb_url=good.image_url, thumb_width=48, thumb_height=48) for good in data] if data != [] else [InlineQueryResultArticle(id='0', title='Нічого не знайдено', input_message_content=InputTextMessageContent(message_text='_', parse_mode="HTML"))]
    await query.answer(results=results, cache_time=1, is_personal=True)


@router.callback_query(F.data == 'to_goods')
async def to_goods(query: CallbackQuery, state: FSMContext):
    await state.set_state(NewOrder.goods)
    state_data = await state.get_data()
    goods = state_data['goods']

    msg = await query.message.edit_text(text='► <b>Товари</b>:\n' + "\n".join(f"» {goods[good]['name']}:  <b>{goods[good]['amount']} шт. - {goods[good]['amount'] * goods[good]['price']} грн.</b>" for good in goods.keys()), reply_markup=kb.goods(True))
    await state.update_data(text=msg.html_text)


@router.callback_query(F.data == 'to_fullname')
async def to_fullname(query: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    await state.set_state(NewOrder.fullname)

    await query.message.edit_text(state_data['text'] + '\n\n► Уведіть ПІБ клієнта: ', reply_markup=kb.back('to_goods'))


@router.message(NewOrder.fullname)
async def new_order_fullname(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    state_data = await state.get_data()
    await state.update_data(fullname=message.text)
    await state.set_state(NewOrder.phone)

    await bot.edit_message_text(chat_id=message.from_user.id, message_id=state_data['msg_id'], text=state_data['text'] + f'\n► <b>П.І.Б</b>:  {message.text}\n\n► Уведіть номер телефону клієнта:', reply_markup=kb.back('to_fullname'))


@router.callback_query(F.data == 'to_phone')
async def to_phone(query: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    await state.set_state(NewOrder.phone)

    await query.message.edit_text(text=state_data['text'] + f'\n► <b>П.І.Б</b>:  {state_data["fullname"]}\n\n► Уведіть номер телефону клієнта:', reply_markup=kb.back('to_fullname'))


@router.message(NewOrder.phone)
async def new_order_phone(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    state_data = await state.get_data()

    try:
        phone = message.text
        if phone.startswith('0'):
            phone = '+38' + phone
        elif phone.startswith('380'):
            phone = phone.replace('380', '+380')
        if len(phone) == 13:
            await state.update_data(phone=phone)
            await state.set_state(NewOrder.city)

            await bot.edit_message_text(chat_id=message.from_user.id, message_id=state_data['msg_id'], text=state_data['text'] + f'\n► <b>П.І.Б</b>:  {state_data["fullname"]}\n► <b>Номер телефону</b>:  {phone}\n\n► Оберіть пункт доставки: ', reply_markup=kb.inline_switcher('Пошук населених пунктів', 'to_phone'))
        else:
            raise ValueError
    except ValueError:
        await bot.edit_message_text(chat_id=message.from_user.id, message_id=state_data['msg_id'], text=f'⚠️Зверніть увагу, номер телефону має складатися з <b>трьох цифр</b> коду країни та <b>дев\'яти цифр</b> самого номеру і бути в одному з наступних форматів:\n\n'
                                                                                                        f'► +380933230302\n'
                                                                                                        f'► 380933230302\n'
                                                                                                        f'► 0933230302', reply_markup=kb.back('to_fullname'))


@router.inline_query(NewOrder.city)
async def search_city(query: InlineQuery, np: NovaPoshta):
    try:
        result = (await np.post_request(
            method="searchSettlements",
            CityName=query.query,
            Limit=50,
            Page=1
        ))['data'][0]['Addresses']
    except Exception:
        result = []
    data = [InlineQueryResultArticle(id=r['Ref'], title=r['Present'], input_message_content=InputTextMessageContent(message_text=r['Present'] + " | " + r['Ref'], parse_mode="HTML")) for r in result if r['Warehouses'] != '0'] if result != [] else [InlineQueryResultArticle(id='0', title='Нічого не знайдено' if query.query != "" else "Уведіть пошуковий запит", input_message_content=InputTextMessageContent(message_text='_', parse_mode="HTML"))]
    try:
        await query.answer(results=data, cache_time=1, is_personal=True)
    except UnboundLocalError:
        pass


@router.callback_query(F.data == 'to_city')
async def to_city(query: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    await state.set_state(NewOrder.city)

    await query.message.edit_text(text=state_data['text'] + f'\n► <b>П.І.Б</b>:  {state_data["fullname"]}\n► <b>Номер телефону</b>:  {state_data["phone"]}\n\n► Оберіть пункт доставки: ', reply_markup=kb.inline_switcher('Пошук населених пунктів', 'to_phone'))


@router.message(NewOrder.city)
async def new_order_city(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    state_data = await state.get_data()
    try:
        city = message.text.split(' | ')
        city[1]
        await state.set_state(NewOrder.warehouse)

        await state.update_data(city={'name': city[0], 'ref': city[1]})
        await bot.edit_message_text(chat_id=message.from_user.id, message_id=state_data['msg_id'], text=state_data['text'] + f'\n► <b>П.І.Б</b>:  {state_data["fullname"]}\n► <b>Номер телефону</b>:  {state_data["phone"]}\n► <b>Населений пункт</b>:  {city[0]}\n\n► Оберіть відділення доставки:', reply_markup=kb.inline_switcher('Пошук відділення', 'to_city'))
    except:
        await bot.edit_message_text(chat_id=message.from_user.id, message_id=state_data['msg_id'], text=state_data['text'] + f'\n► <b>П.І.Б</b>:  {state_data["fullname"]}\n► <b>Номер телефону</b>:  {state_data["phone"]}\n\n► Оберіть пункт доставки: \n\n⚠️Після натискання кнопки, впишіть запит для пошуку населеного пункту', reply_markup=kb.inline_switcher('Пошук населених пунктів', 'to_phone'))


@router.inline_query(NewOrder.warehouse)
async def search_warehouse(query: InlineQuery, np: NovaPoshta, state: FSMContext):
    state_data = await state.get_data()
    result = (await np.post_request(
        method="getWarehouses",
        SettlementRef=state_data['city']['ref'],
        FindByString=query.query,
        Limit=50
    ))['data']
    data = [InlineQueryResultArticle(id=r['Ref'], title=r['Description'], input_message_content=InputTextMessageContent(message_text=r['Description'] + " | " + r['Ref'], parse_mode="HTML")) for r in result] if result != [] else [InlineQueryResultArticle(id='0', title='Нічого не знайдено' if query.query != "" else "Уведіть пошуковий запит", input_message_content=InputTextMessageContent(message_text='_', parse_mode="HTML"))]
    try:
        await query.answer(results=data, cache_time=1, is_personal=True)
    except UnboundLocalError:
        pass


@router.callback_query(F.data == 'to_warehouse')
async def to_warehouse(query: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    await state.set_state(NewOrder.warehouse)

    await query.message.edit_text(text=state_data['text'] + f'\n► <b>П.І.Б</b>:  {state_data["fullname"]}\n► <b>Номер телефону</b>:  {state_data["phone"]}\n► <b>Населений пункт</b>:  {state_data["city"]["name"]}\n\n► Оберіть відділення доставки:', reply_markup=kb.inline_switcher('Пошук відділення', 'to_city'))


@router.message(NewOrder.warehouse)
async def new_order_warehouse(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    state_data = await state.get_data()
    try:
        warehouse = message.text.split(' | ')
        warehouse[1]
        goods = state_data['goods']
        price_sum = sum(goods[good]['price'] * goods[good]['amount'] for good in goods.keys())
        await state.set_state(NewOrder.comment)

        await state.update_data(warehouse={'name': warehouse[0], 'ref': warehouse[1]}, price_sum=price_sum)
        await bot.edit_message_text(chat_id=message.from_user.id, message_id=state_data['msg_id'], text=state_data['text'] + f'\n► <b>П.І.Б</b>:  {state_data["fullname"]}\n► <b>Номер телефону</b>:  {state_data["phone"]}\n► <b>Населений пункт</b>:  {state_data["city"]["name"]}\n► <b>Відділення</b>:  {warehouse[0]}\n► <b>Загальна сума замовлення:  {price_sum} грн.</b>\n\n► Уведіть коментар до замовлення або натисніть "Пропустити":', reply_markup=kb.comment_order())
    except:
        await bot.edit_message_text(chat_id=message.from_user.id, message_id=state_data['msg_id'], text=state_data['text'] + f'\n► <b>П.І.Б</b>:  {state_data["fullname"]}\n► <b>Номер телефону</b>:  {state_data["phone"]}\n► <b>Населений пункт</b>:  {state_data["city"]["name"]}\n\n► Оберіть відділення доставки:\n\n⚠️Після натискання кнопки, впишіть запит для пошуку відділення', reply_markup=kb.inline_switcher('Пошук відділення', 'to_city'))


@router.callback_query(F.data == 'skip_comment')
async def skip_comment(query: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    await state.set_state()

    await query.message.edit_text(state_data['text'] + f'\n► <b>П.І.Б</b>:  {state_data["fullname"]}\n► <b>Номер телефону</b>:  {state_data["phone"]}\n► <b>Населений пункт</b>:  {state_data["city"]["name"]}\n► <b>Відділення</b>:  {state_data["warehouse"]["name"]}\n► <b>Загальна сума замовлення:  {state_data["price_sum"]} грн.</b>\n\n► Ви дійсно бажаєте додати це замовлення?', reply_markup=kb.finish_order())


@router.callback_query(F.data == 'to_comment')
async def to_comment(query: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    await state.set_state(NewOrder.comment)

    await query.message.edit_text(state_data['text'] + f'\n► <b>П.І.Б</b>:  {state_data["fullname"]}\n► <b>Номер телефону</b>:  {state_data["phone"]}\n► <b>Населений пункт</b>:  {state_data["city"]["name"]}\n► <b>Відділення</b>:  {state_data["warehouse"]["name"]}\n► <b>Загальна сума замовлення:  {state_data["price_sum"]} грн.</b>\n\n► Уведіть коментар до замовлення або натисніть "Пропустити":', reply_markup=kb.comment_order())


@router.message(NewOrder.comment)
async def new_order_comment(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    state_data = await state.get_data()
    await state.set_state()

    await state.update_data(comment=message.text)
    await bot.edit_message_text(chat_id=message.from_user.id, message_id=state_data['msg_id'], text=state_data['text'] + f'\n► <b>П.І.Б</b>:  {state_data["fullname"]}\n► <b>Номер телефону</b>:  {state_data["phone"]}\n► <b>Населений пункт</b>:  {state_data["city"]["name"]}\n► <b>Відділення</b>:  {state_data["warehouse"]["name"]}\n► <b>Загальна сума замовлення:  {state_data["price_sum"]} грн.</b>\n► <b>Коментар</b>:  {message.text}\n\n► Ви дійсно бажаєте додати це замовлення?', reply_markup=kb.finish_order())


@router.message(NewOrder.goods)
async def new_order_goods(message: Message, repo: Repo, state: FSMContext, bot: Bot):
    state_data = await state.get_data()
    goods = state_data.get('goods')
    good = await repo.get_good(message.text)

    if goods:
        goods[message.text] = {'amount': 0, 'name': good.name, 'price': good.price}
    else:
        goods = {message.text: {'amount': 0, 'name': good.name, 'price': good.price}}

    await state.update_data(goods=goods, current_good=message.text)
    await message.delete()
    await state.set_state(NewOrder.amount)

    await bot.edit_message_text(chat_id=message.from_user.id, message_id=state_data['msg_id'], text=f'► Уведіть кількість товару <b>«{good.name}»</b>:\n\n'
                                                                                                    f'❕Якщо Ваша ціна відрізняється від <b>{good.price} грн.</b>, зазначне також і її. Наприклад, "<code>3 - {int(good.price * 1.05)}</code>", де 3 це кількість товару, а {int(good.price * 1.05)} це ціна товару. Якщо Ваша ціна така ж, тоді просто надішліть кількість товару. Наприклад, "<code>3</code>"', reply_markup=kb.universal(text='❌ Закрити', callback_data='cancel'))


@router.message(NewOrder.amount)
async def new_order_amount(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    state_data = await state.get_data()
    goods = state_data['goods']

    try:
        if '-' in message.text:
            data = message.text.split(' - ')
            amount = int(data[0])
            price = int(data[1])
            if amount > 0 and price > 0:
                pass
            else:
                raise ValueError
        else:
            amount = int(message.text)
            price = 0
            if amount > 0:
                pass
            else:
                raise ValueError

        if price:
            goods[state_data['current_good']]['price'] = price
        goods[state_data['current_good']]['amount'] = amount
        await state.set_state(NewOrder.goods)

        msg = await bot.edit_message_text(chat_id=message.from_user.id, message_id=state_data['msg_id'],
                                          text='► <b>Товари</b>:\n' + "\n".join(
                                              f"» {goods[good]['name']}:  <b>{goods[good]['amount']} шт. - {goods[good]['amount'] * goods[good]['price']} грн.</b>"
                                              for good in goods.keys()), reply_markup=kb.goods(True))
        await state.update_data(text=msg.html_text)

    except ValueError:
        await bot.edit_message_text(chat_id=message.from_user.id, message_id=state_data['msg_id'], text=f'⚠️Зверніть увагу, кількість товару та ціна мають бути цілими числами, більшими за 0 числом та без зайвих символів.' if '-' in message.text else f'⚠️Зверніть увагу, кількість товару має бути цілим, більшим за 0 числом та без зайвих символів.', reply_markup=kb.universal(text='❌ Закрити', callback_data='cancel'))


@router.callback_query(F.data == 'add_order')
async def add_order(query: CallbackQuery, state: FSMContext, swagger: SwaggerCRM, config: Config, user: User, bot: Bot):
    state_data = await state.get_data()

    res = await swagger.post_request('/order',
                                     source_id=user.source,
                                     source_uuid=str(uuid.uuid4()),
                                     manager_id=6,
                                     manager_comment=state_data.get('comment'),
                                     ordered_at=datetime.now(tz=pytz.timezone('Europe/Kiev')).strftime('%Y-%m-%d %H:%M:%S'),
                                     buyer={
                                         "full_name": state_data['fullname'],
                                         "phone": f'{state_data["phone"]}'
                                     },
                                     products=[
                                         {
                                             "sku": product,
                                             "price": state_data["goods"][product]['price'],
                                             "quantity": state_data["goods"][product]['amount']
                                         } for product in state_data["goods"].keys()
                                     ],
                                     shipping={
                                          "delivery_service_id": 2,
                                          "shipping_service": "Нова Пошта",
                                          "recipient_full_name": f"{state_data['fullname']}",
                                          "recipient_phone": f"{state_data['phone']}",
                                          "warehouse_ref": f"{state_data['warehouse']['ref']}"
                                     })
    if not res.get('errors'):
        await state.clear()
        await query.message.delete()
        await query.message.answer(f'🛒 Замовлення <b>№{res["id"]}</b> успішно додано!', reply_markup=kb.menu())
    else:
        await query.message.delete()
        await query.message.answer(f'⛔️ Помилка при додаванні замовлення', reply_markup=kb.menu())
        await bot.send_message(chat_id=config.channel.errors, text=f"⛔️ Помилка при додаванні замовлення, користувач {query.from_user.full_name} - <code>{query.from_user.id}</code>\n"
                                                                   f"{res['errors']}")
