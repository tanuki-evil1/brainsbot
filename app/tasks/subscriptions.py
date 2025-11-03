import asyncio
from dataclasses import replace
from typing import cast

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from vi_core.sqlalchemy import UnitOfWork

from app.adapters.postgresql.repositories import ServerRepository, SubscriptionRepository, UserRepository
from app.adapters.protocols.factory import ProtocolFactory
from app.adapters.protocols.wireguard.manager import WireGuardManager
from app.adapters.protocols.xray.manager import XrayManager
from app.entities import Protocol
from app.handlers.telegram.deps import get_database
from app.messages import SUBSCRIPTION_EXPIRED_MESSAGE, ButtonTexts, CallbackData, URLs


async def monthly_check_loop(bot: Bot) -> None:
    database = get_database()
    protocol_factory = ProtocolFactory()

    while True:
        async with database.session() as session:
            subscription_repository = SubscriptionRepository(session=session)
            user_repository = UserRepository(session=session)
            server_repository = ServerRepository(session=session)
            uow = UnitOfWork(session=session)

            subscriptions = await subscription_repository.find_all_expired()

            for subscription in subscriptions:
                # Получаем сервер для подписки
                server = await server_repository.find_one(id=subscription.active_server_id)
                if server is None:
                    continue

                # Удаляем пользователя с сервера в зависимости от протокола
                if subscription.active_protocol == Protocol.WIREGUARD and subscription.wg_public_key:
                    wg_manager = cast(WireGuardManager, protocol_factory.create_manager(Protocol.WIREGUARD, server))
                    async with wg_manager:
                        await wg_manager.remove_user(subscription.wg_public_key)
                elif subscription.active_protocol == Protocol.XRAY and subscription.xray_uuid:
                    xray_manager = cast(XrayManager, protocol_factory.create_manager(Protocol.XRAY, server))
                    async with xray_manager:
                        await xray_manager.remove_user(subscription.xray_uuid)

                # Деактивируем подписку
                new_subscription = replace(subscription, is_active=False)
                await subscription_repository.edit_one(new_subscription)

                # Отправляем уведомление пользователю
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
                try:
                    await bot.send_message(user.id, SUBSCRIPTION_EXPIRED_MESSAGE, reply_markup=keyboard)
                except TelegramForbiddenError:
                    # Пользователь заблокировал бота - пропускаем
                    print(f"User {user.id} has blocked the bot")
                    continue

            await uow.commit()

        await asyncio.sleep(86400)  # Проверка раз в день
