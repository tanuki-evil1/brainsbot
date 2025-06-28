from functools import lru_cache

from vi_core.sqlalchemy import AsyncDatabase

from app.settings import settings


@lru_cache()
def get_database() -> AsyncDatabase:
    return AsyncDatabase(pg_dsn=str(settings.database_url))
