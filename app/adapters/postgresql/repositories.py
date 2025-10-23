from datetime import datetime
from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from vi_core.sqlalchemy import SessionHelper

from app import entities
from app.adapters.postgresql import models
from app.adapters.postgresql.registry import mapper


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.helper = SessionHelper[models.User](session)

    async def add_one(self, new_user: entities.User) -> None:
        await self.helper.save(mapper.map(new_user, models.User))

    async def find_one(self, **kwargs: Any) -> entities.User | None:
        stmt = (
            select(models.User)
            .filter_by(**kwargs)
            .options(selectinload(models.User.subscription), selectinload(models.User.referrals))
        )
        instance = await self.helper.one(stmt)
        return mapper.map(instance, entities.User) if instance else None

    async def find_all(self) -> list[entities.User]:
        stmt = select(models.User).options(selectinload(models.User.subscription))
        instances = await self.helper.all(stmt)
        return [mapper.map(instance, entities.User) for instance in instances]


class SubscriptionRepository:
    def __init__(self, session: AsyncSession):
        self.helper = SessionHelper[models.Subscription](session)

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

    async def find_all_ips(self) -> list[str]:
        stmt = select(models.Subscription.allowed_ip).filter(
            models.Subscription.allowed_ip.is_not(None),
        )
        instances = await self.helper.all(stmt)
        return [ip for ip in instances if ip is not None]


class ReferralRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.helper = SessionHelper[models.Referral](session)

    async def add_one(self, new_referral: entities.Referral) -> None:
        await self.helper.save(mapper.map(new_referral, models.Referral))

    async def find_all(self, **kwargs: Any) -> list[entities.Referral]:
        stmt = (
            select(models.Referral)
            .filter_by(**kwargs)
            .options(
                selectinload(models.Referral.referral).selectinload(models.User.subscription),
            )
        )
        instances = await self.helper.all(stmt)
        return [mapper.map(instance, entities.Referral) for instance in instances]

    async def count_all_active_referral(self, referrer_id: int) -> int:
        stmt = (
            select(func.count(models.Referral.id))
            .select_from(models.Referral)
            .join(models.User, models.Referral.referral_id == models.User.id)
            .join(models.Subscription, models.User.id == models.Subscription.user_id)
            .filter(models.Referral.referrer_id == referrer_id)
            .where(models.Subscription.is_active == True)
        )
        result = await self.session.scalar(stmt)
        return result or 0
