from datetime import datetime, timedelta

from sqlalchemy import select, delete, Sequence, cast, VARCHAR, distinct
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import User, Good, Order, PartnerPrice

class BaseRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def scalar_one(self, stmt):
        return (await self.session.execute(stmt)).scalar_one()

    async def scalars_all(self, stmt):
        return (await self.session.scalars(stmt)).all()


class Repo(BaseRepo):

    async def add_user(self, user_id: int, full_name: str, username: str | None) -> User:
        stmt = insert(User).values(
            id=user_id,
            full_name=full_name,
            username=username
        ).on_conflict_do_nothing().returning(User)
        user = await self.session.execute(stmt)
        await self.session.commit()
        return user.scalar()

    async def get_user(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_good(self, id: str) -> Good | None:
        return await self.session.get(Good, id)

    async def delete_good(self, id: str):
        await self.session.execute(delete(Good).where(Good.id == id))

    async def get_goods(self, query: str) -> Sequence[Good]:
        return await self.scalars_all(
            select(Good).where(
                (Good.id.ilike(f"%{query}%") | (Good.name.ilike(f"%{query}%")))
            )
        )

    async def get_user_by_request(self, request: str) -> Sequence[User]:
        return await self.scalars_all(
            select(User).where(
                User.full_name.ilike(f"%{request}%")
                | User.username.ilike(f"%{request}%")
                | (cast(User.id, VARCHAR)).ilike(f"%{request}%")
            ).limit(50)
        )

    async def get_all_sources(self) -> Sequence[int]:
        return await self.scalars_all(select(distinct(User.source)))

    async def get_partner_sources(self) -> list[tuple[int, str]]:
        stmt = (
            select(User.source, User.source_name)
            .where(
                User.is_partner.is_(True),
                User.source.is_not(None),
                User.source_name.is_not(None)
            )
            .distinct()
        )
        rows = await self.session.execute(stmt)
        return [(source_id, source_name) for source_id, source_name in rows.all()]

    async def get_order(self, order_id: int) -> Order | None:
        return await self.session.get(Order, order_id)

    async def delete_orders(self, orders: list[int]) -> Sequence[Order]:
        res = await self.session.scalars(delete(Order).where(~Order.id.in_(orders)).returning(Order))
        await self.session.commit()
        return res

    async def get_partner_prices(self, partner_source: int) -> dict[str, int]:
        rows = await self.scalars_all(
            select(PartnerPrice).where(PartnerPrice.partner_source == partner_source)
        )
        return {row.good_id: row.price for row in rows}

    async def get_partner_price(self, partner_source: int, good_id: str) -> int | None:
        stmt = select(PartnerPrice).where(
            PartnerPrice.partner_source == partner_source,
            PartnerPrice.good_id == good_id
        )
        result = await self.session.scalar(stmt)
        return result.price if result else None

    async def upsert_partner_price(self, partner_source: int, good_id: str, price: int):
        stmt = select(PartnerPrice).where(
            PartnerPrice.partner_source == partner_source,
            PartnerPrice.good_id == good_id
        )
        row = await self.session.scalar(stmt)

        if row:
            row.price = price
        else:
            self.session.add(
                PartnerPrice(
                    partner_source=partner_source,
                    good_id=good_id,
                    price=price
                )
            )

        await self.session.commit()