import json
import logging
import re
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


def _safe_sheet_name(name: str) -> str:
    name = re.sub(r'[\[\]\:\*\?\/\\]', '_', name).strip()
    return name[:31] if len(name) > 31 else name


def _build_period(year: int, data: list[str]) -> str:
    return f"{year}-{data[0].replace('.', '-')} 00:00:00, {year}-{data[1].replace('.', '-')} 23:59:59"


def _set_columns(worksheet):
    worksheet.set_column("A:A", 8)
    worksheet.set_column("B:B", 12)
    worksheet.set_column("C:C", 20)
    worksheet.set_column("D:D", 16)
    worksheet.set_column("E:E", 30)
    worksheet.set_column("F:F", 16)
    worksheet.set_column("G:G", 22)
    worksheet.set_column("H:H", 16)
    worksheet.set_column("I:I", 30)
    worksheet.set_column("J:J", 10)
    worksheet.set_column("K:M", 20)
    worksheet.set_column("N:N", 16)


def _build_formats(workbook):
    formats = {}

    formats["merge"] = workbook.add_format({
        "align": "center",
        "valign": "vcenter",
        "fg_color": "#BDD7EE",
        "bold": True,
    })

    formats["bold"] = workbook.add_format({"bold": True})
    formats["bold_red"] = workbook.add_format({"bold": True, "color": "red"})

    formats["header_center"] = workbook.add_format({
        'bold': True,
        'italic': True,
        'fg_color': '#E2EFDA',
        'align': 'center',
        'border_color': '#2F75B5',
        'bottom': 2
    })

    formats["header"] = workbook.add_format({
        'bold': True,
        'italic': True,
        'fg_color': '#E2EFDA',
        'border_color': '#2F75B5',
        'bottom': 2
    })

    formats["cell"] = workbook.add_format({
        'fg_color': '#E2EFDA',
        'border_color': '#2F75B5',
        'border': 1
    })

    formats["cell_num"] = workbook.add_format({
        'fg_color': '#E2EFDA',
        'border_color': '#2F75B5',
        'border': 1,
        'num_format': '#,##0.00'
    })

    formats["green"] = workbook.add_format({
        'bold': True,
        'fg_color': '#2AF634',
        'num_format': '#,##0.00'
    })

    formats["green_big"] = workbook.add_format({
        'bold': True,
        'fg_color': '#00B015',
        'font_size': 14,
        'num_format': '#,##0.00'
    })

    formats["blue_big"] = workbook.add_format({
        'bold': True,
        'fg_color': '#009fff',
        'font_size': 14,
        'num_format': '#,##0.00'
    })

    formats["status_baf5b5"] = workbook.add_format({
        'fg_color': '#baf5b5',
        'border_color': '#2F75B5',
        'border': 1
    })

    formats["status_e3e0ff"] = workbook.add_format({
        'fg_color': '#e3e0ff',
        'border_color': '#2F75B5',
        'border': 1
    })

    formats["status_ffd3cc"] = workbook.add_format({
        'fg_color': '#ffd3cc',
        'border_color': '#2F75B5',
        'border': 1
    })

    formats["status_ffd7a2"] = workbook.add_format({
        'fg_color': '#ffd7a2',
        'border_color': '#2F75B5',
        'border': 1
    })

    return formats


def _write_partner_sheet(workbook, worksheet, source_name: str, orders: list, data: list[str], year: int):
    formats = _build_formats(workbook)
    _set_columns(worksheet)

    worksheet.merge_range("A1:N1", "", formats["merge"])
    worksheet.write_rich_string(
        "A1",
        formats["bold"], f"Замовлення: {source_name} ",
        formats["bold_red"], f"(за період {year}.{data[0]} - {data[1]})",
        formats["merge"]
    )

    worksheet.write_row(
        "A2",
        ["№", "Дата", "ПІБ", "Телефон", "Адреса", "ТТН", "Статус", "Код товару", "Назва товару"],
        formats["header_center"]
    )
    worksheet.write_row(
        "J2",
        ["К-сть (шт.)", "Партнерська ціна (грн./шт.)", "Ціна виробника (грн./шт.)", "Ціна продажу (грн./шт.)"],
        formats["header"]
    )
    worksheet.write("N2", "Заробіток", formats["green"])

    row = 3
    products_summary = {}

    for order in orders:
        try:
            address = order['shipping']['address_payload']
            if address != []:
                location = (
                    f"{f'{address.get('region_desc')}, ' if address.get('region_desc') else ''}"
                    f"{address.get('city_desc')}, {address.get('warehouse_desc')}"
                )
            else:
                location = ""
        except Exception as e:
            logging.info(e)
            continue

        worksheet.write_row(
            f"A{row}",
            [
                order['id'],
                order['created_at'][:10].replace('-', '.'),
                order['buyer']['full_name'],
                order['buyer']['phone'].replace('+38', ''),
                location,
                order['shipping'].get('tracking_code')
            ],
            formats["cell"]
        )

        status_alias = order['status']['alias']
        color_key = status.get(status_alias, {}).get('color', 'baf5b5')
        status_format = formats.get(f"status_{color_key}", formats["cell"])
        worksheet.write(
            f"G{row}",
            status.get(status_alias, {}).get('name', status_alias),
            status_format
        )

        first_row_for_order = row

        for product in order['products']:
            sku = product['sku']
            if sku not in products_summary:
                products_summary[sku] = {
                    "name": product['name'],
                    "quantity": product['quantity']
                }
            else:
                products_summary[sku]["quantity"] += product['quantity']

            if row != first_row_for_order:
                worksheet.write_row(f"A{row}", ['', '', '', '', '', '', ''], formats["cell"])

            worksheet.write_row(
                f"H{row}",
                [sku, product['name'], product['quantity']],
                formats["cell"]
            )

            worksheet.write_row(
                f"K{row}",
                [product['purchased_price'], product['price'], product['price_sold']],
                formats["cell_num"]
            )

            if status_alias in ('povernennya', 'canceled', 'dubl_zamovlennya'):
                worksheet.write(f"N{row}", 0, formats["green"])
            else:
                worksheet.write(f"N{row}", f"=M{row}*J{row}-K{row}*J{row}", formats["green"])

            row += 1

    if row == 3:
        worksheet.write("A3", "Немає замовлень за цей період", formats["bold"])
        return

    total_row = row
    worksheet.write_row(
        f"A{total_row}",
        ["", "", "", "", "", "", "", "", "", "", f"=SUMPRODUCT(J3:J{total_row - 1},K3:K{total_row - 1})", "", f"=SUMPRODUCT(J3:J{total_row - 1},M3:M{total_row - 1})"],
        formats["blue_big"]
    )
    worksheet.write(f"N{total_row}", f"=SUM(N3:N{total_row - 1})", formats["green_big"])

    worksheet.autofilter("A2:N2")

    summary_start = total_row + 3

    worksheet.merge_range(
        summary_start - 1, 0,
        summary_start - 1, 2,
        "",
        formats["merge"]
    )
    worksheet.write_rich_string(
        summary_start - 1, 0,
        formats["bold"], f"Підсумок проданих товарів: {source_name} ",
        formats["bold_red"], f"(за період {year}.{data[0]} - {data[1]})",
        formats["merge"]
    )

    worksheet.write_row(
        summary_start, 0,
        ["Код товару", "Назва товару", "К-сть (шт.)"],
        formats["header_center"]
    )

    summary_row = summary_start + 1
    for sku, product_data in products_summary.items():
        worksheet.write_row(
            summary_row, 0,
            [sku, product_data["name"], product_data["quantity"]],
            formats["cell"]
        )
        summary_row += 1


async def generate_all_partners_file(swagger: SwaggerCRM, repo: Repo, data: list[str], year: int):
    partners = await repo.get_partner_sources()

    if not partners:
        return None, "⚠️ Не знайдено партнерів із прив'язаними source/source_name"

    workbook = xlsxwriter.Workbook(f"{uuid.uuid4()}.xlsx")

    has_any_orders = False
    period = _build_period(year, data)

    for source_id, source_name in partners:
        result = await swagger.get_request(
            '/order',
            limit=50,
            include='shipping, buyer, products.offer, shipping.deliveryService, status',
            **{
                "filter[source_id]": source_id,
                "filter[created_between]": period
            }
        )

        source_orders = []
        while result:
            source_orders.extend(result.get("data", []))
            next_page_url = result.get("next_page_url")
            if next_page_url:
                result = await swagger.get_request_url(next_page_url)
            else:
                result = None

        if source_orders:
            has_any_orders = True

        sheet_name = _safe_sheet_name(f"{source_name}_{data[0]}-{data[1]}")
        worksheet = workbook.add_worksheet(sheet_name)
        _write_partner_sheet(workbook, worksheet, source_name, source_orders, data, year)

    workbook.close()

    if not has_any_orders:
        try:
            import os
            os.remove(workbook.filename)
        except Exception:
            pass
        return None, "⚠️ Немає замовлень у жодного партнера за цей період"

    return workbook.filename, None