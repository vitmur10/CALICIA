import uuid
from datetime import datetime

from aiogram.utils.link import create_tg_link
from sqlalchemy import BigInteger, DateTime, func, Boolean, Enum
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.dialects.postgresql import UUID, ARRAY, BYTEA

from bot.structrures.enums import VarsEnum, ContentTypes


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    full_name: Mapped[str | None] = mapped_column()
    username: Mapped[str | None] = mapped_column()
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_partner: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[int | None] = mapped_column()
    source_name: Mapped[str | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    @property
    def url(self) -> str:
        return create_tg_link("user", id=self.id)


class Good(Base):
    __tablename__ = 'goods'

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    description: Mapped[str | None] = mapped_column()
    currency_code: Mapped[str] = mapped_column()
    price: Mapped[int] = mapped_column()
    image_url: Mapped[str | None] = mapped_column()
    purchased_price: Mapped[int] = mapped_column()
    updated_at: Mapped[str] = mapped_column()
class PartnerPrice(Base):
    __tablename__ = "partner_prices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    partner_source: Mapped[int] = mapped_column(index=True)
    good_id: Mapped[str] = mapped_column(index=True)
    price: Mapped[int] = mapped_column()

class Order(Base):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    msg_id: Mapped[int] = mapped_column(BigInteger)
    buyer: Mapped[bytes] = mapped_column(BYTEA)
    products: Mapped[bytes] = mapped_column(BYTEA)
    shipping: Mapped[bytes] = mapped_column(BYTEA)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now())


