from aiogram.filters.callback_data import CallbackData


class UserData(CallbackData, prefix="u"):
    id: int
    action: str | None = None
    int_value: int | None = None


class ExtractData(CallbackData, prefix="e"):
    year: int | None = None
    month: int | None = None
    week: str | None = None


class AdminExtractAllData(CallbackData, prefix="aea"):
    year: int | None = None
    month: int | None = None
    week: str | None = None
