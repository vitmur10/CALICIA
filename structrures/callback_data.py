from aiogram.filters.callback_data import CallbackData


class UserData(CallbackData, prefix="u"):
    id: int
    action: str | None = None
    int_value: int | None = None


class ExtractData(CallbackData, prefix="e"):
    month: int | None = None
    week: str | None = None

class AdminExtractAllData(CallbackData, prefix="aea"):
    month: int | None = None
    week: str | None = None
