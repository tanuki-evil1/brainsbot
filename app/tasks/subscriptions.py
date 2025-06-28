import asyncio
from dataclasses import replace
from aiogram import Bot
from app.adapters.postgresql.repositories import SubscriptionRepository, UserRepository
from app.handlers.telegram.deps import get_database
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from app.adapters.wireguard.async_manager import AsyncWireGuardClientManager
from vi_core.sqlalchemy import UnitOfWork
from app.settings import settings
from app.messages import SUBSCRIPTION_EXPIRED_MESSAGE, ButtonTexts, URLs, CallbackData


async def monthly_check_loop(bot: Bot) -> None:
    database = get_database()
    async with database.session() as session:
        subscription_repository = SubscriptionRepository(session=session)
        user_repository = UserRepository(session=session)
        uow = UnitOfWork(session=session)
        wireguard_manager = AsyncWireGuardClientManager(
            host=settings.server_host,
            user=settings.server_user,
            password=settings.server_password,
        )
        while True:
            subscriptions = await subscription_repository.find_all_expired()

            for subscription in subscriptions:
                async with wireguard_manager as manager:
                    await manager.remove_user(subscription.public_key)
                new_subscription = replace(subscription, is_active=False)
                await subscription_repository.edit_one(new_subscription)
                user = await user_repository.find_one(id=subscription.user_id)

                if user is None:
                    continue

                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text=ButtonTexts.DONATE, url=URLs.PAYMENT_URL)],
                        [InlineKeyboardButton(text=ButtonTexts.SEND_CHECK, callback_data=CallbackData.SEND_CHECK)],
                        [
                            InlineKeyboardButton(
                                text=ButtonTexts.DISABLE_NOTIFICATIONS, callback_data=CallbackData.NOTIFICATIONS
                            )
                        ],
                    ]
                )
                await bot.send_message(user.id, SUBSCRIPTION_EXPIRED_MESSAGE, reply_markup=keyboard)

            await uow.commit()
            await asyncio.sleep(86400)  # Проверка раз в день
