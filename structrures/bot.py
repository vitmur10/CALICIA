import json
import logging
import uuid
from datetime import datetime, timezone, timedelta

import pytz
import xlsxwriter
from aiogram import Bot

from bot.api.swagger import SwaggerCRM
from bot.config import Config
from bot.db import Repo
from bot.db.models import Order

months = ['Січень', 'Лютий', 'Березень', 'Квітень', 'Травень', 'Червень', 'Липень', 'Серпень', 'Вересень', 'Жовтень', 'Листопад', 'Грудень']
months_length = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
status = {
    'pidtverdzeno': {'name': 'Підтверджено', 'color': 'ffd7a2'},
    'ttn_stvoreno': {'name': '✅ ТТН СТВОРЕНО', 'color': 'ffd7a2'},
    'new': {'name': 'Новий', 'color': 'baf5b5'},
    'in_transit': {'name': 'У дорозі', 'color': 'e3e0ff'},
    'v_dorozi_zovnisnya_sluzba': {'name': 'У дорозі (Зовнішня служба)', 'color': 'e3e0ff'},
    'u_viddilenni': {'name': 'У відділенні', 'color': 'e3e0ff'},
    'gotove_do_vidpravlennya': {'name': '📦 ГОТОВЕ ДО ВІДПРАВЛЕННЯ', 'color': 'e3e0ff'},
    'completed': {'name': 'Завершено', 'color': 'baf5b5'},
    'povernennya': {'name': 'Повернення', 'color': 'ffd3cc'},
    'canceled': {'name': 'Відхилено', 'color': 'ffd3cc'},
    'dubl_zamovlennya': {'name': 'Дубль', 'color': 'ffd3cc'}
}


async def generate_file(swagger: SwaggerCRM, source_id: int, source_name: str, data: list):
    result = await swagger.get_request('/order', limit=50, include='shipping, buyer, products.offer, shipping.deliveryService, status', **{"filter[source_id]": source_id, "filter[created_between]": f"2025-{data[0].replace('.', '-')} 00:00:00, 2025-{data[1].replace('.', '-')} 23:59:59"})
    if result['data'] != []:
        workbook = xlsxwriter.Workbook(f'{uuid.uuid4()}.xlsx')
        worksheet = workbook.add_worksheet('Замовлення')

        merge_format = workbook.add_format(
            {
                "align": "center",
                "valign": "vcenter",
                "fg_color": "#BDD7EE",
            }
        )

        bold = workbook.add_format({'bold': True})
        bold_red = workbook.add_format({'bold': True, 'color': 'red'})
        bold_italic_color_center = workbook.add_format(
            {'bold': True, 'italic': True, 'fg_color': '#E2EFDA', 'align': 'center', 'border_color': '#2F75B5',
             'bottom': 2})
        bold_italic_color = workbook.add_format(
            {'bold': True, 'italic': True, 'fg_color': '#E2EFDA', 'border_color': '#2F75B5', 'bottom': 2})
        color = workbook.add_format({'fg_color': '#E2EFDA', 'border_color': '#2F75B5', 'border': 1})
        color_num = workbook.add_format(
            {'fg_color': '#E2EFDA', 'border_color': '#2F75B5', 'border': 1, 'num_format': '#,##0.00'})
        green_color = workbook.add_format({'bold': True, 'fg_color': '#2AF634', 'num_format': '#,##0.00'})
        green_color_14 = workbook.add_format(
            {'bold': True, 'fg_color': '#00B015', 'font_size': 14, 'num_format': '#,##0.00'})
        products_sum_14 = workbook.add_format(
            {'bold': True, 'fg_color': '009fff', 'font_size': 14, 'num_format': '#,##0.00'})
        global baf5b5, e3e0ff, ffd3cc, ffd7a2
        baf5b5 = workbook.add_format({'fg_color': '#baf5b5', 'border_color': '#2F75B5', 'border': 1})
        e3e0ff = workbook.add_format({'fg_color': '#e3e0ff', 'border_color': '#2F75B5', 'border': 1})
        ffd3cc = workbook.add_format({'fg_color': '#ffd3cc', 'border_color': '#2F75B5', 'border': 1})
        ffd7a2 = workbook.add_format({'fg_color': '#ffd7a2', 'border_color': '#2F75B5', 'border': 1})

        worksheet.set_column("A0:A0", 6)
        worksheet.set_column("B0:B0", 10)
        worksheet.set_column("C0:C0", 16)
        worksheet.set_column("D0:D0", 11)
        worksheet.set_column("E0:F0", 16)
        worksheet.set_column("G0:G0", 14)
        worksheet.set_column("H0:H0", 16)
        worksheet.set_column("I0:I0", 25)
        worksheet.set_column("J0:J0", 8)
        worksheet.set_column("K0:M0", 23)
        worksheet.set_column("N0:N0", 16)

        worksheet.merge_range("A1:N1", "", merge_format)
        worksheet.write_rich_string("A1", bold, f"Замовлення: {source_name} ", bold_red, f"(за період 2025.{data[0]} - {data[1]})", merge_format)
        worksheet.write_row("A2",
                            ["№", "Дата", "ПІБ", "Телефон", "Адреса", "ТТН", "Статус", "Код товару", "Назва товару"],
                            bold_italic_color_center)
        worksheet.write_row("J2",
                            ["К-сть (шт.)", "Партнерська ціна (грн./шт.)", "Ціна виробника (грн./шт.)", "Ціна продажу (грн./шт.)"],
                            bold_italic_color)
        worksheet.write("N2", "Заробіток", green_color)
        row = 3
        products = {}

        while result and (result['next_page_url'] or result['total'] <= 50):
            for order in result['data']:

                try:
                    address = order['shipping']['address_payload']
                    if address != []:
                        location = f"""{f"{address.get('region_desc')}, " if address.get('region_desc') else ''}{address.get('city_desc')}, {address.get('warehouse_desc')}"""
                    else:
                        location = ""
                except Exception as e:
                    logging.info(e)
                    continue

                worksheet.write_row(f"A{row}", [order['id'], order['created_at'][:10].replace('-', '.'),
                                                order['buyer']['full_name'],
                                                order['buyer']['phone'].replace('+38', ''), location,
                                                order['shipping'].get('tracking_code')], color)
                worksheet.write(f"G{row}", status[order['status']['alias']]['name'],
                                globals()[status[order['status']['alias']]['color']])
                worksheet.write(f"N{row}", f"=M{row}*J{row}-K{row}*J{row}", green_color)
                last_row = row
                for product in order['products']:
                    if not products.get(product['sku']):
                        products[product['sku']] = {'name': product['name'], 'quantity': product['quantity']}
                    else:
                        products[product['sku']]['quantity'] += product['quantity']

                    if row != last_row:
                        worksheet.write_row(f"A{row}", ['', '', '', '', '', '', ''], color)
                    worksheet.write_row(f"H{row}", [product['sku'], product['name'], product['quantity']], color)
                    if order['status']['alias'] in ('povernennya', 'canceled', 'dubl_zamovlennya'):
                        worksheet.write_row(f"K{row}", [product['purchased_price'], product['price'], product['price_sold']], color_num)
                        worksheet.write(f"N{row}", 0, green_color)
                    else:
                        worksheet.write_row(f"K{row}",
                                            [product['purchased_price'], product['price'], product['price_sold']],
                                            color_num)
                        worksheet.write(f"N{row}", f"=M{row}*J{row}-K{row}*J{row}", green_color)
                    row += 1

            if result['next_page_url']:
                result = await swagger.get_request_url(result['next_page_url'])
            else:
                result = None

        worksheet.write_row(f"A{row}", ["", "", "", "", "", "", "", "", "", "", f"=SUMPRODUCT(J3:J{row - 1},K3:K{row - 1})", "", f"=SUMPRODUCT(J3:J{row - 1},M3:M{row - 1})"], products_sum_14)
        worksheet.write(f"N{row}", f"=(SUM(N3:N{row - 1}))", green_color_14)

        worksheet.autofilter('A2:M2')

        worksheet_result = workbook.add_worksheet('Підсумок')

        worksheet_result.set_column("A0:A0", 10)
        worksheet_result.set_column("B0:B0", 60)
        worksheet_result.set_column("C0:C0", 24)

        worksheet_result.merge_range("A1:C1", "", merge_format)
        worksheet_result.write_rich_string("A1", bold, f"Підсумок проданих товарів: {source_name} ", bold_red, f"(за період 2025.{data[0]} - {data[1]})", merge_format)

        worksheet_result.write_row("A2", ["Код товару", "Назва товару", "К-сть (шт.)"], bold_italic_color_center)
        row = 3
        for product in products.keys():
            worksheet_result.write_row(f"A{row}", [product, products[product]['name'], products[product]['quantity']], color)
            row += 1

        worksheet.autofilter('A2:D2')

        workbook.close()

        return workbook.filename, None

    return None, '⚠️Неможливо отримати виписку за цей період, немає замовлень'


async def orders_to_channel(session_factory, swagger: SwaggerCRM, bot: Bot, config: Config):
    async with session_factory() as session:
        repo = Repo(session)
        sources = await swagger.get_request('/order/source', limit=50)
        sources = {source['id']: source['name'] for source in sources['data'] if source['name'].startswith('посередник') or source['name'] == 'ГЕКТАР'}
        result = await swagger.get_request(
            '/order',
            limit=50,
            include='shipping, buyer, products.offer, shipping.deliveryService, status', **{
                "filter[created_between]": f"{(datetime.now().astimezone(timezone.utc) - timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')}, {(datetime.now().astimezone(timezone.utc)).strftime('%Y-%m-%d %H:%M:%S')}"
            })
        if result:
            for order in result['data']:
                if order['source_id'] in sources.keys():
                    goods = '► <b>Товари</b>:'
                    total = 0
                    for good in order['products']:
                        goods += f"\n» {good['name']}:  <b>{good['quantity']} шт. - {good['quantity'] * good['price']} грн.</b>"
                        total += good['quantity'] * good['price']
                    msg = await bot.send_message(
                        chat_id=config.channel.offers,
                        text=f"🛒 <b>Замовлення #{order['id']} від «{sources[order['source_id']]}»</b>:\n" +
                             goods +
                            (f'\n► <b>П.І.Б</b>:  {order["buyer"]["full_name"]}\n'
                             f'► <b>Номер телефону</b>:  {order["buyer"]["phone"]}\n'
                             f'► <b>Населений пункт</b>:  {order["shipping"]["address_payload"].get("city_desc") if order["shipping"]["address_payload"] != [] else "!Помилка"}\n'
                             f'► <b>Відділення</b>:  {order["shipping"]["address_payload"].get("warehouse_desc") if order["shipping"]["address_payload"] != [] else "!Помилка"}\n'
                             f'► <b>Загальна сума замовлення:  {total} грн.</b>\n') +
                            (f'► <b>Коментар</b>:  {order["manager_comment"]}\n\n' if order.get("manager_comment") else "")
                    )
                    repo.session.add(Order(id=order['id'], msg_id=msg.message_id, buyer=json.dumps(order['buyer']).encode('utf8'), products=json.dumps(order['products']).encode('utf8'), shipping=json.dumps(order["shipping"]).encode('utf8')))

        result = await swagger.get_request(
            '/order',
            limit=50,
            include='shipping, buyer, products.offer, shipping.deliveryService, status', **{
                "filter[created_between]": f"{(datetime.now().astimezone(timezone.utc) - timedelta(hours=47)).strftime('%Y-%m-%d %H:%M:%S')}, {(datetime.now().astimezone(timezone.utc)).strftime('%Y-%m-%d %H:%M:%S')}"
            })
        logging.info(result)
        orders = []
        if result:
            for order in result['data']:
                orders.append(order['id'])
                order_db = await repo.get_order(order['id'])
                if order['source_id'] in sources.keys() and order_db:
                    if order['status']['alias'] in ('povernennya', 'canceled'):
                        goods = '► <b>Товари</b>:'
                        total = 0
                        for good in order['products']:
                            goods += f"\n» {good['name']}:  <b>{good['quantity']} шт. - {good['quantity'] * good['price']} грн.</b>"
                            total += good['quantity'] * good['price']
                        msg = await bot.edit_message_text(
                            chat_id=config.channel.offers,
                            message_id=order_db.msg_id,
                            text=f"🛒 <b>Замовлення #{order['id']} від «{sources[order['source_id']]}»</b>:\n"
                                 f"<b>❌ СКАСОВАНО ❌</b>\n" +
                                 goods +
                                 (f'\n► <b>П.І.Б</b>:  {order["buyer"]["full_name"]}\n'
                                  f'► <b>Номер телефону</b>:  {order["buyer"]["phone"]}\n'
                                  f'► <b>Населений пункт</b>:  {order["shipping"]["address_payload"].get("city_desc") if order["shipping"]["address_payload"] != [] else "!Помилка"}\n'
                                  f'► <b>Відділення</b>:  {order["shipping"]["address_payload"].get("warehouse_desc") if order["shipping"]["address_payload"] != [] else "!Помилка"}\n'
                                  f'► <b>Загальна сума замовлення:  {total} грн.</b>\n') +
                                 (f'► <b>Коментар</b>:  {order["manager_comment"]}\n\n' if order.get(
                                     "manager_comment") else "")
                        )
                        await msg.reply('<b>❌ Замовлення було скасовано! ❌</b>')
                    elif order['products'] != json.loads(order_db.products.decode()) or order["shipping"]["address_payload"] != json.loads(order_db.shipping.decode()) or order['buyer'] != json.loads(order_db.buyer.decode()):
                        goods = '► <b>Товари</b>:'
                        total = 0
                        for good in order['products']:
                            goods += f"\n» {good['name']}:  <b>{good['quantity']} шт. - {good['quantity'] * good['price']} грн.</b>"
                            total += good['quantity'] * good['price']
                        msg = await bot.edit_message_text(
                            chat_id=config.channel.offers,
                            message_id=order_db.msg_id,
                            text=f"🛒 <b>Замовлення #{order['id']} від «{sources[order['source_id']]}»</b>:\n"
                                 f"<b>♻️ ВІДБУЛИСЯ ЗМІНИ ♻️</b>\n" +
                                 goods +
                                 (f'\n► <b>П.І.Б</b>:  {order["buyer"]["full_name"]}\n'
                                  f'► <b>Номер телефону</b>:  {order["buyer"]["phone"]}\n'
                                  f'► <b>Населений пункт</b>:  {order["shipping"]["address_payload"].get("city_desc") if order["shipping"]["address_payload"] != [] else "!Помилка"}\n'
                                  f'► <b>Відділення</b>:  {order["shipping"]["address_payload"].get("warehouse_desc") if order["shipping"]["address_payload"] != [] else "!Помилка"}\n'
                                  f'► <b>Загальна сума замовлення:  {total} грн.</b>\n') +
                                 (f'► <b>Коментар</b>:  {order["manager_comment"]}\n\n' if order.get(
                                     "manager_comment") else "")
                        )
                        await msg.reply('<b>♻️ Замовлення було відредаговано! ♻️</b>')
                    order_db.buyer = json.dumps(order['buyer']).encode('utf8')
                    order_db.products = json.dumps(order['products']).encode('utf8')
                    order_db.shipping = json.dumps(order["shipping"]["address_payload"]).encode('utf8')
        await repo.session.commit()

        for order in await repo.delete_orders(orders):
            goods = '► <b>Товари</b>:'
            total = 0
            buyer = json.loads(order.buyer.decode())
            shipping = json.loads(order.shipping.decode())

            for good in json.loads(order.products.decode()):
                logging.info(good)
                goods += f"\n» {good['name']}:  <b>{good['quantity']} шт. - {good['quantity'] * good['price']} грн.</b>"
                total += good['quantity'] * good['price']
            msg = await bot.edit_message_text(
                chat_id=config.channel.offers,
                message_id=order.msg_id,
                text=f"🛒 <b>Замовлення #{order.id}</b>:\n"
                     f"<b>🗑 ВИДАЛЕНО 🗑</b>\n" +
                     goods +
                     (f'\n► <b>П.І.Б</b>:  {buyer["full_name"]}\n'
                      f'► <b>Номер телефону</b>:  {buyer["phone"]}\n'
                      f'► <b>Населений пункт</b>:  {shipping["address_payload"].get("city_desc") if shipping["address_payload"] != [] else "!Помилка"}\n'
                      f'► <b>Відділення</b>:  {shipping["address_payload"].get("warehouse_desc") if shipping["address_payload"] != [] else "!Помилка"}\n'
                      f'► <b>Загальна сума замовлення:  {total} грн.</b>\n')
            )
            await msg.reply('<b>🗑 Замовлення було видалено! 🗑</b>')

