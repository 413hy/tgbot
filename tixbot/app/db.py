from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app import models


def create_engine_and_session(database_url: str) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    # MySQL in long-running bot/web processes can hit stale pooled connections,
    # which may cause intermittent slow/failing requests. Enable pre-ping/recycle.
    engine_kwargs: dict = {"future": True}
    if "sqlite" not in (database_url or "").lower():
        engine_kwargs.update(
            {
                "pool_pre_ping": True,
                "pool_recycle": 1800,
                "pool_size": 10,
                "max_overflow": 20,
            }
        )
    engine = create_async_engine(database_url, **engine_kwargs)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    return engine, Session


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
