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
DELIVERY_SERVICE_MAP = {
    "nova_poshta": {
        "id": 2,
        "name": "Нова Пошта",
        "supports_ref": True,
    },
    "ukrposhta": {
        "id": 22,
        "name": "Укрпошта",
        "supports_ref": False,
    },
    "meest": {
        "id": 23,
        "name": "Meest Express",
        "supports_ref": False,
    },
    "rozetka": {
        "id": 26,
        "name": "Rozetka Delivery",
        "supports_ref": False,
    },
}
def build_shipping_payload(state_data: dict) -> dict:
    delivery = state_data["delivery_service"]

    shipping = {
        "delivery_service_id": delivery["id"],
        "shipping_service": delivery["name"],
        "recipient_full_name": state_data["fullname"],
        "recipient_phone": state_data["phone"],
        "shipping_address_city": state_data["city"]["name"],
        "shipping_receive_point": state_data["warehouse"]["name"],
    }

    warehouse_ref = state_data.get("warehouse", {}).get("ref")
    if warehouse_ref:
        shipping["warehouse_ref"] = warehouse_ref

    return shipping

def calc_price_sum(goods: dict) -> int:
    return sum(item["price"] * item["amount"] for item in goods.values())
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

    await query.message.edit_text(
        text=state_data['text']
             + f'\n► П.І.Б: {state_data["fullname"]}'
             + '\n\n► Уведіть номер телефону клієнта:',
        reply_markup=kb.back('to_fullname')
    )
@router.message(NewOrder.phone)
async def new_order_phone(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    state_data = await state.get_data()

    try:
        phone = message.text.strip()

        if phone.startswith('0'):
            phone = '+38' + phone
        elif phone.startswith('380'):
            phone = '+' + phone

        if len(phone) != 13:
            raise ValueError

        await state.update_data(phone=phone)
        await state.set_state(NewOrder.delivery_service)

        await bot.edit_message_text(
            chat_id=message.from_user.id,
            message_id=state_data['msg_id'],
            text=state_data['text']
                 + f'\n► П.І.Б: {state_data["fullname"]}'
                 + f'\n► Номер телефону: {phone}'
                 + '\n\n► Оберіть службу доставки:',
            reply_markup=kb.delivery_services()
        )
    except ValueError:
        await bot.edit_message_text(
            chat_id=message.from_user.id,
            message_id=state_data['msg_id'],
            text=(
                f'⚠️Зверніть увагу, номер телефону має складатися з трьох цифр коду країни '
                f'та дев\'яти цифр самого номеру і бути в одному з наступних форматів:\n\n'
                f'► +380933230302\n'
                f'► 380933230302\n'
                f'► 0933230302'
            ),
            reply_markup=kb.back('to_fullname')
        )


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

@router.callback_query(F.data == 'to_delivery_service')
async def to_delivery_service(query: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    await state.set_state(NewOrder.delivery_service)

    await query.message.edit_text(
        text=state_data['text']
             + f'\n► П.І.Б: {state_data["fullname"]}'
             + f'\n► Номер телефону: {state_data["phone"]}'
             + '\n\n► Оберіть службу доставки:',
        reply_markup=kb.delivery_services()
    )
@router.callback_query(F.data == 'to_city')
async def to_city(query: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    delivery = state_data['delivery_service']

    await state.set_state(NewOrder.city)

    if delivery['key'] == 'nova_poshta':
        await query.message.edit_text(
            text=state_data['text']
                 + f'\n► П.І.Б: {state_data["fullname"]}'
                 + f'\n► Номер телефону: {state_data["phone"]}'
                 + f'\n► Служба доставки: {delivery["name"]}'
                 + '\n\n► Оберіть населений пункт:',
            reply_markup=kb.inline_switcher('Пошук населених пунктів', 'to_delivery_service')
        )
    else:
        await query.message.edit_text(
            text=state_data['text']
                 + f'\n► П.І.Б: {state_data["fullname"]}'
                 + f'\n► Номер телефону: {state_data["phone"]}'
                 + f'\n► Служба доставки: {delivery["name"]}'
                 + '\n\n► Уведіть населений пункт:',
            reply_markup=kb.back('to_delivery_service')
        )

@router.message(NewOrder.city)
async def new_order_city(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    state_data = await state.get_data()
    delivery = state_data['delivery_service']

    if delivery['key'] == 'nova_poshta':
        try:
            city = message.text.split(' | ')
            city[1]

            await state.update_data(city={'name': city[0], 'ref': city[1]})
            await state.set_state(NewOrder.warehouse)

            await bot.edit_message_text(
                chat_id=message.from_user.id,
                message_id=state_data['msg_id'],
                text=state_data['text']
                     + f'\n► П.І.Б: {state_data["fullname"]}'
                     + f'\n► Номер телефону: {state_data["phone"]}'
                     + f'\n► Служба доставки: {delivery["name"]}'
                     + f'\n► Населений пункт: {city[0]}'
                     + '\n\n► Оберіть відділення доставки:',
                reply_markup=kb.inline_switcher('Пошук відділення', 'to_city')
            )
        except:
            await bot.edit_message_text(
                chat_id=message.from_user.id,
                message_id=state_data['msg_id'],
                text='⚠️ Знайдено декілька чи жодного населених пунктів, уведіть дані у форматі:\n'
                     '► Назва населеного пункту | Ідентифікатор населеного пункту'
                     '\n\nПриклад:\n'
                     '► Одеса | 6bef146c-1d5a-11e3-8c4a-0050568002cf',
                reply_markup=kb.back('to_city')
            )
    else:
        city_name = message.text.strip()

        if not city_name:
            await bot.edit_message_text(
                chat_id=message.from_user.id,
                message_id=state_data['msg_id'],
                text='⚠️ Уведіть коректний населений пункт.',
                reply_markup=kb.back('to_city')
            )
            return

        await state.update_data(city={'name': city_name, 'ref': None})
        await state.set_state(NewOrder.warehouse)

        await bot.edit_message_text(
            chat_id=message.from_user.id,
            message_id=state_data['msg_id'],
            text=state_data['text']
                 + f'\n► П.І.Б: {state_data["fullname"]}'
                 + f'\n► Номер телефону: {state_data["phone"]}'
                 + f'\n► Служба доставки: {delivery["name"]}'
                 + f'\n► Населений пункт: {city_name}'
                 + '\n\n► Уведіть відділення / точку видачі:',
            reply_markup=kb.back('to_city')
        )

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
    delivery = state_data['delivery_service']

    await state.set_state(NewOrder.warehouse)

    if delivery['key'] == 'nova_poshta':
        await query.message.edit_text(
            text=state_data['text']
                 + f'\n► П.І.Б: {state_data["fullname"]}'
                 + f'\n► Номер телефону: {state_data["phone"]}'
                 + f'\n► Служба доставки: {delivery["name"]}'
                 + f'\n► Населений пункт: {state_data["city"]["name"]}'
                 + '\n\n► Оберіть відділення доставки:',
            reply_markup=kb.inline_switcher('Пошук відділення', 'to_city')
        )
    else:
        await query.message.edit_text(
            text=state_data['text']
                 + f'\n► П.І.Б: {state_data["fullname"]}'
                 + f'\n► Номер телефону: {state_data["phone"]}'
                 + f'\n► Служба доставки: {delivery["name"]}'
                 + f'\n► Населений пункт: {state_data["city"]["name"]}'
                 + '\n\n► Уведіть відділення / точку видачі:',
            reply_markup=kb.back('to_city')
        )
@router.callback_query(F.data.startswith('delivery:'))
async def choose_delivery_service(query: CallbackQuery, state: FSMContext):
    key = query.data.split(':', 1)[1]
    service = DELIVERY_SERVICE_MAP[key]

    await state.update_data(
        delivery_service={
            'key': key,
            'id': service['id'],
            'name': service['name'],
            'supports_ref': service['supports_ref'],
        }
    )
    await state.set_state(NewOrder.city)

    state_data = await state.get_data()

    if key == 'nova_poshta':
        text = (
            state_data['text']
            + f'\n► П.І.Б: {state_data["fullname"]}'
            + f'\n► Номер телефону: {state_data["phone"]}'
            + f'\n► Служба доставки: {service["name"]}'
            + '\n\n► Оберіть населений пункт:'
        )
        markup = kb.inline_switcher('Пошук населених пунктів', 'to_delivery_service')
    else:
        text = (
            state_data['text']
            + f'\n► П.І.Б: {state_data["fullname"]}'
            + f'\n► Номер телефону: {state_data["phone"]}'
            + f'\n► Служба доставки: {service["name"]}'
            + '\n\n► Уведіть населений пункт:'
        )
        markup = kb.back('to_delivery_service')

    await query.message.edit_text(
        text=text,
        reply_markup=markup
    )
@router.message(NewOrder.warehouse)
async def new_order_warehouse(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    state_data = await state.get_data()
    delivery = state_data['delivery_service']
    goods = state_data['goods']
    price_sum = calc_price_sum(goods)

    if delivery['key'] == 'nova_poshta':
        try:
            warehouse = message.text.split(' | ')
            warehouse[1]

            await state.update_data(
                warehouse={'name': warehouse[0], 'ref': warehouse[1]},
                price_sum=price_sum
            )
            await state.set_state(NewOrder.comment)

            await bot.edit_message_text(
                chat_id=message.from_user.id,
                message_id=state_data['msg_id'],
                text=state_data['text']
                     + f'\n► П.І.Б: {state_data["fullname"]}'
                     + f'\n► Номер телефону: {state_data["phone"]}'
                     + f'\n► Служба доставки: {delivery["name"]}'
                     + f'\n► Населений пункт: {state_data["city"]["name"]}'
                     + f'\n► Відділення: {warehouse[0]}'
                     + f'\n► Загальна сума замовлення: {price_sum} грн.'
                     + '\n\n► Уведіть коментар до замовлення або натисніть "Пропустити":',
                reply_markup=kb.comment_order()
            )
        except Exception:
            await bot.edit_message_text(
                chat_id=message.from_user.id,
                message_id=state_data['msg_id'],
                text='⚠️ Знайдено декілька чи жодного відділень, уведіть дані у форматі:\n'
                     '► Назва відділення | Ідентифікатор відділення'
                     '\n\nПриклад:\n'
                     '► Відділення №1: вул. Приклад, 10 | 12345678-1234-1234-1234-123456789012',
                reply_markup=kb.back('to_warehouse')
            )
    else:
        warehouse_name = message.text.strip()

        if not warehouse_name:
            await bot.edit_message_text(
                chat_id=message.from_user.id,
                message_id=state_data['msg_id'],
                text='⚠️ Уведіть коректне відділення або точку видачі.',
                reply_markup=kb.back('to_warehouse')
            )
            return

        await state.update_data(
            warehouse={'name': warehouse_name, 'ref': None},
            price_sum=price_sum
        )
        await state.set_state(NewOrder.comment)

        await bot.edit_message_text(
            chat_id=message.from_user.id,
            message_id=state_data['msg_id'],
            text=state_data['text']
                 + f'\n► П.І.Б: {state_data["fullname"]}'
                 + f'\n► Номер телефону: {state_data["phone"]}'
                 + f'\n► Служба доставки: {delivery["name"]}'
                 + f'\n► Населений пункт: {state_data["city"]["name"]}'
                 + f'\n► Відділення: {warehouse_name}'
                 + f'\n► Загальна сума замовлення: {price_sum} грн.'
                 + '\n\n► Уведіть коментар до замовлення або натисніть "Пропустити":',
            reply_markup=kb.comment_order()
        )

@router.callback_query(F.data == 'skip_comment')
async def skip_comment(query: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    delivery = state_data['delivery_service']

    await state.set_state()

    await query.message.edit_text(
        state_data['text']
        + f'\n► П.І.Б: {state_data["fullname"]}'
        + f'\n► Номер телефону: {state_data["phone"]}'
        + f'\n► Служба доставки: {delivery["name"]}'
        + f'\n► Населений пункт: {state_data["city"]["name"]}'
        + f'\n► Відділення: {state_data["warehouse"]["name"]}'
        + f'\n► Загальна сума замовлення: {state_data["price_sum"]} грн.'
        + '\n\n► Ви дійсно бажаєте додати це замовлення?',
        reply_markup=kb.finish_order()
    )
@router.callback_query(F.data == 'to_comment')
async def to_comment(query: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    delivery = state_data['delivery_service']

    await state.set_state(NewOrder.comment)

    await query.message.edit_text(
        state_data['text']
        + f'\n► П.І.Б: {state_data["fullname"]}'
        + f'\n► Номер телефону: {state_data["phone"]}'
        + f'\n► Служба доставки: {delivery["name"]}'
        + f'\n► Населений пункт: {state_data["city"]["name"]}'
        + f'\n► Відділення: {state_data["warehouse"]["name"]}'
        + f'\n► Загальна сума замовлення: {state_data["price_sum"]} грн.'
        + '\n\n► Уведіть коментар до замовлення або натисніть "Пропустити":',
        reply_markup=kb.comment_order()
    )

@router.message(NewOrder.comment)
async def new_order_comment(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    state_data = await state.get_data()
    delivery = state_data['delivery_service']

    comment = message.text.strip()
    if comment == '-':
        comment = None

    await state.set_state()
    await state.update_data(comment=comment)

    comment_text = comment if comment else '—'

    await bot.edit_message_text(
        chat_id=message.from_user.id,
        message_id=state_data['msg_id'],
        text=state_data['text']
             + f'\n► П.І.Б: {state_data["fullname"]}'
             + f'\n► Номер телефону: {state_data["phone"]}'
             + f'\n► Служба доставки: {delivery["name"]}'
             + f'\n► Населений пункт: {state_data["city"]["name"]}'
             + f'\n► Відділення: {state_data["warehouse"]["name"]}'
             + f'\n► Загальна сума замовлення: {state_data["price_sum"]} грн.'
             + f'\n► Коментар: {comment_text}'
             + '\n\n► Ви дійсно бажаєте додати це замовлення?',
        reply_markup=kb.finish_order()
    )

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
async def add_order(
    query: CallbackQuery,
    state: FSMContext,
    swagger: SwaggerCRM,
    config: Config,
    user: User,
    bot: Bot
):
    state_data = await state.get_data()

    shipping = build_shipping_payload(state_data)

    res = await swagger.post_request(
        '/order',
        source_id=user.source,
        source_uuid=str(uuid.uuid4()),
        manager_id=6,
        manager_comment=state_data.get('comment'),
        ordered_at=datetime.now(
            tz=pytz.timezone('Europe/Kiev')
        ).strftime('%Y-%m-%d %H:%M:%S'),
        buyer={
            "full_name": state_data['fullname'],
            "phone": state_data["phone"],
        },
        products=[
            {
                "sku": product,
                "price": state_data["goods"][product]['price'],
                "quantity": state_data["goods"][product]['amount']
            }
            for product in state_data["goods"].keys()
        ],
        shipping=shipping
    )

    await state.clear()

    if res.get('status_code') in (200, 201) or res.get('id'):
        order_id = res.get('id')

        await state.clear()

        try:
            await query.message.delete()
        except Exception:
            pass

        await query.message.answer(
            f'✅ <b>Ваше замовлення успішно оформлене!</b>\n'
            f'Номер замовлення: <b>№{order_id}</b>',
            reply_markup=kb.menu()
        )

        await query.answer('Замовлення успішно оформлене')

    else:
        await state.clear()

        error_text = res.get('message') or res.get('errors') or res

        try:
            await query.message.delete()
        except Exception:
            pass

        await query.message.answer(
            f'⚠️ <b>Не вдалося створити замовлення.</b>\n'
            f'Спробуйте ще раз або зверніться до менеджера.',
            reply_markup=kb.menu()
        )

        await bot.send_message(
            chat_id=config.channel.errors,
            text=(
                f'⛔️ Помилка при створенні замовлення\n'
                f'Користувач: {query.from_user.full_name} - <code>{query.from_user.id}</code>\n'
                f'Відповідь CRM: <code>{error_text}</code>'
            )
        )

        await query.answer('Сталася помилка', show_alert=True)