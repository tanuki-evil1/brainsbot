from datetime import datetime
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from vi_core.sqlalchemy import SessionHelper

from app import entities
from app.adapters.postgresql import models
from app.adapters.postgresql.models import Subscription, User
from app.adapters.postgresql.registry import mapper


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.helper = SessionHelper[User](session)

    async def add_one(self, new_user: entities.User) -> None:
        await self.helper.save(mapper.map(new_user, models.User))

    async def find_one(self, **kwargs: Any) -> entities.User | None:
        stmt = select(models.User).filter_by(**kwargs).options(selectinload(models.User.subscription))
        instance = await self.helper.one(stmt)
        return mapper.map(instance, entities.User) if instance else None


class SubscriptionRepository:
    def __init__(self, session: AsyncSession):
        self.helper = SessionHelper[Subscription](session)

    async def find_all_expired(self) -> list[entities.Subscription]:
        stmt = select(models.Subscription).filter(
            models.Subscription.end_date < datetime.now(),
            models.Subscription.is_notify == True,
        )
        instances = await self.helper.all(stmt)
        return [mapper.map(instance, entities.Subscription) for instance in instances]

    async def add_one(self, new_subscription: entities.Subscription) -> None:
        await self.helper.save(mapper.map(new_subscription, models.Subscription))

    async def find_one(self, **kwargs: Any) -> entities.Subscription:
        stmt = select(models.Subscription).filter_by(**kwargs)
        instance = await self.helper.one(stmt)
        return mapper.map(instance, entities.Subscription)

    async def edit_one(self, subscription: entities.Subscription) -> None:
        await self.helper.update(mapper.map(subscription, models.Subscription))
