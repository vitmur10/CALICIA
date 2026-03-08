import asyncio
from sqlalchemy import text

from bot.config import load_config
from bot.db import sa_sessionmaker


async def main():
    config = load_config(".env")
    session_factory = sa_sessionmaker(config.db)

    async with session_factory() as session:
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS partner_prices (
                id SERIAL PRIMARY KEY,
                partner_source INTEGER NOT NULL,
                good_id VARCHAR NOT NULL,
                price INTEGER NOT NULL
            );
        """))

        await session.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_partner_prices_source_good
            ON partner_prices (partner_source, good_id);
        """))

        await session.commit()
        print("partner_prices table created successfully")


if __name__ == "__main__":
    asyncio.run(main())