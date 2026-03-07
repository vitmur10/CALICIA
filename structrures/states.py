from aiogram.fsm.state import StatesGroup, State


class NewOrder(StatesGroup):
    goods = State()
    price = State()
    amount = State()
    fullname = State()
    phone = State()
    city = State()
    warehouse = State()
    comment = State()
