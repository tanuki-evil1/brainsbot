from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from vi_core.sqlalchemy import UnitOfWork

from app import entities, messages
from app.adapters.postgresql import repositories
from app.adapters.protocols.factory import ProtocolFactory
from app.settings import settings

DAYS_IN_MONTH = 30


@dataclass
class StartUserUsecase:
    user_repository: repositories.UserRepository
    uow: UnitOfWork
    subscription_repository: repositories.SubscriptionRepository
    referral_repository: repositories.ReferralRepository
    server_repository: repositories.ServerRepository
    protocol_factory: ProtocolFactory

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        if not message.from_user:
            return

        user = await self.user_repository.find_one(id=message.from_user.id)
        if not user:
            new_user = entities.User(
                id=message.from_user.id,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name or "",
                username=message.from_user.username or "",
                language_code=message.from_user.language_code or "",
            )

            new_subscription = entities.Subscription(user_id=new_user.id)

            server = await self.server_repository.find_one(id=new_subscription.active_server_id)
            if not server:
                raise ValueError("Server not found")

            ips = await self.subscription_repository.find_all_wg_allowed_ips()
            async with self.protocol_factory.create_manager(new_subscription.active_protocol, server) as manager:
                user_config = await manager.create_config(username=str(message.from_user.id), ips=ips)
                await manager.add_user(user_config)  # type: ignore[arg-type]

            new_subscription = replace(new_subscription,
                wg_key=user_config.access_key if hasattr(user_config, "access_key") else None,
                wg_public_key=user_config.client_public_key if hasattr(user_config, "client_public_key") else None,
                wg_allowed_ip=user_config.allowed_ip if hasattr(user_config, "allowed_ip") else None,
                xray_key=user_config.key if hasattr(user_config, "key") else None,
                xray_uuid=user_config.uuid if hasattr(user_config, "uuid") else None,
            )
            await self.user_repository.add_one(new_user)
            await self.subscription_repository.add_one(new_subscription)

            if message.text:
                referrer_id = message.text.split(" ", 1)
                if len(referrer_id) > 1 and referrer_id[1].startswith("ref_"):
                    referrer_id_int = int(referrer_id[1][4:])
                    referrer = await self.user_repository.find_one(id=referrer_id_int)
                    if referrer:
                        new_referral = entities.Referral(
                            referrer_id=referrer_id_int,
                            referral_id=new_user.id,
                        )
                        await self.referral_repository.add_one(new_referral)

            await self.uow.commit()

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=messages.ButtonTexts.ACCOUNT, callback_data=messages.CallbackData.ACCOUNT
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=messages.ButtonTexts.NOTIFICATIONS,
                        callback_data=messages.CallbackData.NOTIFICATIONS,
                    ),
                    InlineKeyboardButton(
                        text=messages.ButtonTexts.INSTRUCTIONS,
                        callback_data=messages.CallbackData.INSTRUCTIONS,
                    ),
                ],
                [
                    InlineKeyboardButton(text=messages.ButtonTexts.TEAM, callback_data=messages.CallbackData.TEAM),
                    InlineKeyboardButton(
                        text=messages.ButtonTexts.SUPPORT, callback_data=messages.CallbackData.SUPPORT
                    ),
                ],
                [InlineKeyboardButton(text=messages.ButtonTexts.DONATE, callback_data=messages.CallbackData.DONATE)],
            ]
        )
        await message.answer(messages.WELCOME_MESSAGE, reply_markup=keyboard)
        await state.clear()


@dataclass
class AccountUsecase:
    user_repository: repositories.UserRepository
    uow: UnitOfWork
    server_repository: repositories.ServerRepository

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        if not callback_query.message:
            return

        user = await self.user_repository.find_one(id=callback_query.from_user.id)
        if not user or not user.subscription:
            return

        # Определяем статус подписки
        subscription_status = (
            messages.StatusMessages.SUBSCRIPTION_ACTIVE
            if user.subscription.is_active
            else messages.StatusMessages.SUBSCRIPTION_INACTIVE
        )

        # Форматируем дату окончания подписки
        if user.subscription.end_date:
            days_left = (user.subscription.end_date.date() - datetime.now().date()).days
            end_date = messages.MessageTemplates.END_DATE_FORMAT.format(
                date=user.subscription.end_date.strftime("%d.%m.%Y"),
                days=days_left,
                days_text=messages.Constants.DAYS_TEXT,
            )
        else:
            end_date = messages.StatusMessages.SUBSCRIPTION_NO_END_DATE

        server = await self.server_repository.find_one(id=user.subscription.active_server_id)
        if not server:
            return

        message = messages.ACCOUNT_TEXT.format(
            username=callback_query.from_user.first_name,
            subscription_status=subscription_status,
            end_date=end_date,
            protocol=user.subscription.active_protocol,
            country=server.location
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=messages.ButtonTexts.KEY,
                        callback_data=messages.CallbackData.KEY,
                    ),
                    InlineKeyboardButton(
                        text=messages.ButtonTexts.REISSUE_KEY,
                        callback_data=messages.CallbackData.REISSUE_KEY,
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=messages.ButtonTexts.SWAP_COUNTRY,
                        callback_data=messages.CallbackData.SWAP_COUNTRY,
                    ),
                    InlineKeyboardButton(
                        text=messages.ButtonTexts.SWAP_PROTOCOL,
                        callback_data=messages.CallbackData.SWAP_PROTOCOL,
                    ),
                ]
            ]
        )
        await callback_query.message.answer(message, reply_markup=keyboard)


@dataclass
class SwapCountryUsecase:
    server_repository: repositories.ServerRepository
    user_repository: repositories.UserRepository

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        user = await self.user_repository.find_one(id=callback_query.from_user.id)
        if not user or not user.subscription:
            return
        servers = await self.server_repository.find_all()

        # Создаем кнопки для каждой страны
        keyboard_buttons = []
        for server in servers:
            # Добавляем эмодзи флага если текущий сервер
            prefix = "✅ " if server.id == user.subscription.active_server_id else ""
            button = InlineKeyboardButton(
                text=f"{prefix}{server.location}",
                callback_data=f"country_{server.id}"
            )
            keyboard_buttons.append([button])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        if callback_query.message:
            await callback_query.message.answer(
                "🌐 Выберите страну для подключения:",
                reply_markup=keyboard
            )


@dataclass
class SwapProtocolUsecase:
    user_repository: repositories.UserRepository

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        user = await self.user_repository.find_one(id=callback_query.from_user.id)
        if not user or not user.subscription:
            return

        # Создаем кнопки для каждого протокола
        protocols = [
            (entities.Protocol.WIREGUARD, "WireGuard"),
            (entities.Protocol.XRAY, "Xray"),
        ]

        keyboard_buttons = []
        for protocol_value, protocol_name in protocols:
            # Добавляем чекмарк если текущий протокол
            prefix = "✅ " if protocol_value == user.subscription.active_protocol else ""
            button = InlineKeyboardButton(
                text=f"{prefix}{protocol_name}",
                callback_data=f"protocol_{protocol_value}"
            )
            keyboard_buttons.append([button])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        if callback_query.message:
            await callback_query.message.answer(
                "⚙️ Выберите протокол подключения:",
                reply_markup=keyboard
            )


@dataclass
class ConfirmSwapCountryUsecase:
    user_repository: repositories.UserRepository
    subscription_repository: repositories.SubscriptionRepository
    server_repository: repositories.ServerRepository
    protocol_factory: ProtocolFactory
    uow: UnitOfWork

    async def __call__(self, callback_query: types.CallbackQuery, server_id: int) -> None:
        user = await self.user_repository.find_one(id=callback_query.from_user.id)
        if not user or not user.subscription:
            return

        # Проверяем, не выбран ли уже этот сервер
        if user.subscription.active_server_id == server_id:
            await callback_query.answer("Вы уже используете этот сервер", show_alert=True)
            return

        # Получаем новый сервер
        new_server = await self.server_repository.find_one(id=server_id)
        if not new_server:
            await callback_query.answer("Сервер не найден", show_alert=True)
            return

        # Получаем старый сервер для удаления пользователя
        old_server = await self.server_repository.find_one(id=user.subscription.active_server_id)

        # Удаляем пользователя со старого сервера
        if old_server:
            protocol_manager = self.protocol_factory.create_manager(
                user.subscription.active_protocol, old_server
            )
            async with protocol_manager as manager:
                # Удаляем пользователя по его ключу
                if user.subscription.active_protocol == entities.Protocol.WIREGUARD:
                    if user.subscription.wg_public_key:
                        await manager.remove_user(user.subscription.wg_public_key)  # type: ignore[arg-type]
                elif user.subscription.active_protocol == entities.Protocol.XRAY:
                    if user.subscription.xray_uuid:
                        await manager.remove_user(user.subscription.xray_uuid)  # type: ignore[arg-type]

        # Создаем конфигурацию на новом сервере
        ips = await self.subscription_repository.find_all_wg_allowed_ips()
        new_protocol_manager = self.protocol_factory.create_manager(
            user.subscription.active_protocol, new_server
        )
        async with new_protocol_manager as manager:
            user_config = await manager.create_config(
                username=str(callback_query.from_user.id), ips=ips
            )
            await manager.add_user(user_config)  # type: ignore[arg-type]
        # Обновляем подписку
        updated_subscription = replace(
            user.subscription,
            active_server_id=server_id,
            wg_key=user_config.access_key if hasattr(user_config, "access_key") else (
                user.subscription.wg_key
            ),
            wg_public_key=user_config.client_public_key if hasattr(
                user_config, "client_public_key"
            ) else user.subscription.wg_public_key,
            wg_allowed_ip=user_config.allowed_ip if hasattr(
                user_config, "allowed_ip"
            ) else user.subscription.wg_allowed_ip,
            xray_key=user_config.key if hasattr(user_config, "key") else user.subscription.xray_key,
            xray_uuid=user_config.uuid if hasattr(user_config, "uuid") else user.subscription.xray_uuid,
        )

        await self.subscription_repository.edit_one(updated_subscription)
        await self.uow.commit()

        await callback_query.answer(f"✅ Страна изменена на {new_server.location}", show_alert=True)
        if callback_query.message:
            await callback_query.message.answer(
                f"🌐 Страна успешно изменена на *{new_server.location}*\n\n"
                "Получите новый ключ в разделе 'Мой аккаунт'"
            )


@dataclass
class ConfirmSwapProtocolUsecase:
    user_repository: repositories.UserRepository
    subscription_repository: repositories.SubscriptionRepository
    server_repository: repositories.ServerRepository
    protocol_factory: ProtocolFactory
    uow: UnitOfWork

    async def __call__(self, callback_query: types.CallbackQuery, protocol: entities.Protocol) -> None:
        user = await self.user_repository.find_one(id=callback_query.from_user.id)
        if not user or not user.subscription:
            return

        # Проверяем, не выбран ли уже этот протокол
        if user.subscription.active_protocol == protocol:
            await callback_query.answer("Вы уже используете этот протокол", show_alert=True)
            return

        # Получаем текущий сервер
        server = await self.server_repository.find_one(id=user.subscription.active_server_id)
        if not server:
            await callback_query.answer("Сервер не найден", show_alert=True)
            return

        # Удаляем пользователя со старого протокола
        old_protocol_manager = self.protocol_factory.create_manager(
            user.subscription.active_protocol, server
        )
        async with old_protocol_manager as manager:
            if user.subscription.active_protocol == entities.Protocol.WIREGUARD:
                if user.subscription.wg_public_key:
                    await manager.remove_user(user.subscription.wg_public_key)  # type: ignore[arg-type]
            elif user.subscription.active_protocol == entities.Protocol.XRAY:
                if user.subscription.xray_uuid:
                    await manager.remove_user(user.subscription.xray_uuid)  # type: ignore[arg-type]

        # Создаем конфигурацию с новым протоколом
        ips = await self.subscription_repository.find_all_wg_allowed_ips()
        new_protocol_manager = self.protocol_factory.create_manager(protocol, server)
        async with new_protocol_manager as manager:
            user_config = await manager.create_config(username=str(callback_query.from_user.id), ips=ips)
            await manager.add_user(user_config)  # type: ignore[arg-type]

        # Обновляем подписку
        updated_subscription = replace(
            user.subscription,
            active_protocol=protocol,
            wg_key=user_config.access_key if hasattr(user_config, "access_key") else None,
            wg_public_key=user_config.client_public_key if hasattr(user_config, "client_public_key") else None,
            wg_allowed_ip=user_config.allowed_ip if hasattr(user_config, "allowed_ip") else None,
            xray_key=user_config.key if hasattr(user_config, "key") else None,
            xray_uuid=user_config.uuid if hasattr(user_config, "uuid") else None,
        )

        await self.subscription_repository.edit_one(updated_subscription)
        await self.uow.commit()

        protocol_name = "WireGuard" if protocol == entities.Protocol.WIREGUARD else "Xray"
        await callback_query.answer(f"✅ Протокол изменен на {protocol_name}", show_alert=True)
        if callback_query.message:
            await callback_query.message.answer(
                f"⚙️ Протокол успешно изменен на *{protocol_name}*\n\n"
                "Получите новый ключ в разделе 'Мой аккаунт'"
            )


@dataclass
class KeyUsecase:
    user_repository: repositories.UserRepository

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        if not callback_query.message:
            return

        user = await self.user_repository.find_one(id=callback_query.from_user.id)
        if not user or not user.subscription:
            return

        if not user.subscription.is_active:
            await callback_query.message.answer(messages.ActionRequiredMessages.NOTIFICATIONS_ACTIVATION_REQUIRED)
            return

        # Получаем ключ в зависимости от протокола
        key = None
        if user.subscription.active_protocol == entities.Protocol.WIREGUARD:
            key = user.subscription.wg_key
        elif user.subscription.active_protocol == entities.Protocol.XRAY:
            key = user.subscription.xray_key

        if not key:
            await callback_query.message.answer(messages.StatusMessages.SUBSCRIPTION_NO_KEY)
            return

        key_message = f"🔑 *Ваш ключ:*\n\n`{key}`\n\n📋 Нажмите на ключ для копирования"
        await callback_query.message.answer(key_message)


@dataclass
class ReissueKeyUsecase:
    user_repository: repositories.UserRepository
    subscription_repository: repositories.SubscriptionRepository
    uow: UnitOfWork
    protocol_factory: ProtocolFactory
    server_repository: repositories.ServerRepository

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        if not callback_query.message:
            return

        user = await self.user_repository.find_one(id=callback_query.from_user.id)
        if not user or not user.subscription:
            return

        # Проверяем наличие ключа в зависимости от протокола
        has_key = False
        if user.subscription.active_protocol == entities.Protocol.WIREGUARD:
            has_key = bool(user.subscription.wg_key)
        elif user.subscription.active_protocol == entities.Protocol.XRAY:
            has_key = bool(user.subscription.xray_key)

        if not has_key:
            await callback_query.message.answer(messages.StatusMessages.SUBSCRIPTION_NO_KEY)
            return

        server = await self.server_repository.find_one(id=user.subscription.active_server_id)
        if not server:
            await callback_query.answer("Сервер не найден", show_alert=True)
            return

        # Удаляем старого пользователя
        async with self.protocol_factory.create_manager(user.subscription.active_protocol, server) as manager:
            if user.subscription.active_protocol == entities.Protocol.WIREGUARD:
                if user.subscription.wg_public_key:
                    await manager.remove_user(user.subscription.wg_public_key)  # type: ignore[arg-type]
            elif user.subscription.active_protocol == entities.Protocol.XRAY:
                if user.subscription.xray_uuid:
                    await manager.remove_user(user.subscription.xray_uuid)  # type: ignore[arg-type]

        # Создаем новый ключ
        ips = await self.subscription_repository.find_all_wg_allowed_ips()
        async with self.protocol_factory.create_manager(user.subscription.active_protocol, server) as manager:
            new_config = await manager.create_config(username=str(callback_query.from_user.id), ips=ips)
            await manager.add_user(new_config)  # type: ignore[arg-type]

        # Обновляем подписку с новыми данными
        updated_subscription = replace(
            user.subscription,
            wg_key=new_config.access_key if hasattr(new_config, "access_key") else user.subscription.wg_key,
            wg_public_key=new_config.client_public_key if hasattr(
                new_config, "client_public_key"
            ) else user.subscription.wg_public_key,
            wg_allowed_ip=new_config.allowed_ip if hasattr(
                new_config, "allowed_ip"
            ) else user.subscription.wg_allowed_ip,
            xray_key=new_config.key if hasattr(new_config, "key") else user.subscription.xray_key,
            xray_uuid=new_config.uuid if hasattr(new_config, "uuid") else user.subscription.xray_uuid,
        )
        await self.subscription_repository.edit_one(updated_subscription)
        await self.uow.commit()

        await callback_query.message.answer(messages.StatusMessages.KEY_REISSUED_SUCCESS)


@dataclass
class ReferralUsecase:
    user_repository: repositories.UserRepository
    referral_repository: repositories.ReferralRepository

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        if not callback_query.message:
            return
        referrals = await self.referral_repository.find_all(referrer_id=callback_query.from_user.id)
        referral_text = ""
        for referral in referrals:
            if not referral.referral or not referral.referral.subscription:
                continue
            # Безопасно форматируем имя пользователя и username
            first_name = referral.referral.first_name or "Пользователь"

            status = (messages.StatusMessages.SUBSCRIPTION_ACTIVE
                     if referral.referral.subscription.is_active
                     else messages.StatusMessages.SUBSCRIPTION_INACTIVE)

            referral_text += f"{first_name}{messages.Constants.SUBSCRIPTION_SEPARATOR}{status}\n"

        count_active_refferal = await self.referral_repository.count_all_active_referral(
            referrer_id=callback_query.from_user.id
        )
        await callback_query.message.answer(
            messages.REFERRAL_TEXT.format(
                referrals=referral_text,
                referral_link=callback_query.from_user.id,
                discount=entities.DISCOUNT * count_active_refferal,
            ),
        )


@dataclass
class InstructionsUsecase:
    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        if not callback_query.message:
            return
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=messages.ButtonTexts.INSTRUCTION_CONNECT,
                        callback_data=messages.CallbackData.INSTRUCTION_CONNECT,
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=messages.ButtonTexts.INSTRUCTION_UPDATE,
                        callback_data=messages.CallbackData.INSTRUCTION_UPDATE,
                    ),
                    InlineKeyboardButton(
                        text=messages.ButtonTexts.INSTRUCTION_REFERRAL,
                        callback_data=messages.CallbackData.INSTRUCTION_REFERRAL,
                    ),
                ],
            ]
        )
        await callback_query.message.answer(messages.INSTRUCTIONS_TEXT, reply_markup=keyboard)


@dataclass
class NotificationsUsecase:
    user_repository: repositories.UserRepository
    uow: UnitOfWork
    subscription_repository: repositories.SubscriptionRepository

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        if not callback_query.message:
            return

        user = await self.user_repository.find_one(id=callback_query.from_user.id)
        if not user or not user.subscription:
            return

        if not user.subscription.is_active:
            await callback_query.message.answer(messages.ActionRequiredMessages.NOTIFICATIONS_ACTIVATION_REQUIRED)
            return

        if user.subscription.is_notify:
            updated_subscription = replace(user.subscription, is_notify=False)
            await callback_query.message.answer(messages.StatusMessages.NOTIFICATIONS_DISABLED)
        else:
            updated_subscription = replace(user.subscription, is_notify=True)
            await callback_query.message.answer(messages.StatusMessages.NOTIFICATIONS_ENABLED)

        await self.subscription_repository.edit_one(updated_subscription)
        await self.uow.commit()


@dataclass
class SendMessageCheckUsecase:
    user_repository: repositories.UserRepository
    uow: UnitOfWork
    subscription_repository: repositories.SubscriptionRepository
    server_repository: repositories.ServerRepository
    protocol_factory: ProtocolFactory

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        if not message.from_user or not message.bot:
            return

        text = message.text or message.caption or messages.Constants.NO_TEXT_PLACEHOLDER

        check_message = messages.MessageTemplates.CHECK_INFO.format(
            username=message.from_user.username or str(message.from_user.id),
            text=text
        )

        if message.photo:
            photo = message.photo[-1]
            await message.bot.send_photo(
                settings.admin_id,
                photo.file_id,
                caption=check_message,
                parse_mode=None,
            )
        elif message.document:
            await message.bot.send_document(
                settings.admin_id,
                message.document.file_id,
                caption=check_message,
                parse_mode=None,
            )
        else:
            await message.answer(messages.StatusMessages.ONLY_PHOTO_OR_DOCUMENT)
            return

        await state.clear()

        subscription = await self.subscription_repository.find_one(user_id=message.from_user.id)
        if not subscription:
            return

        server = await self.server_repository.find_one(id=subscription.active_server_id)
        if not server:
            return

        # Проверяем наличие ключа в зависимости от протокола
        has_key = False
        if subscription.active_protocol == entities.Protocol.WIREGUARD:
            has_key = bool(subscription.wg_key)
        elif subscription.active_protocol == entities.Protocol.XRAY:
            has_key = bool(subscription.xray_key)

        if not has_key:
            ips = await self.subscription_repository.find_all_wg_allowed_ips()
            async with self.protocol_factory.create_manager(subscription.active_protocol, server) as manager:
                user_config = await manager.create_config(username=str(message.from_user.id), ips=ips)
                await manager.add_user(user_config)  # type: ignore[arg-type]

            updated_subscription = replace(
                subscription,
                end_date=datetime.now() + timedelta(days=DAYS_IN_MONTH)
                if not subscription.end_date
                else subscription.end_date + timedelta(days=DAYS_IN_MONTH),
                is_notify=True,
                is_active=True,
                wg_key=user_config.access_key if hasattr(user_config, "access_key") else subscription.wg_key,
                wg_public_key=user_config.client_public_key if hasattr(
                    user_config, "client_public_key"
                ) else subscription.wg_public_key,
                wg_allowed_ip=user_config.allowed_ip if hasattr(
                    user_config, "allowed_ip"
                ) else subscription.wg_allowed_ip,
                xray_key=user_config.key if hasattr(user_config, "key") else subscription.xray_key,
                xray_uuid=user_config.uuid if hasattr(user_config, "uuid") else subscription.xray_uuid,
            )
        else:
            updated_subscription = replace(
                subscription,
                end_date=datetime.now() + timedelta(days=DAYS_IN_MONTH)
                if not subscription.end_date
                else subscription.end_date + timedelta(days=DAYS_IN_MONTH),
                is_notify=True,
                is_active=True,
            )

        await self.subscription_repository.edit_one(updated_subscription)
        await self.uow.commit()

        await message.answer(messages.StatusMessages.MESSAGE_SENT_ACCESS_GRANTED)


@dataclass
class DonateUsecase:
    user_repository: repositories.UserRepository
    subscription_repository: repositories.SubscriptionRepository
    referral_repository: repositories.ReferralRepository

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        if not callback_query.message:
            return
        subscription = await self.subscription_repository.find_one(user_id=callback_query.from_user.id)

        if subscription.is_active:
            await callback_query.message.answer(messages.StatusMessages.SUBSCRIPTION_ALREADY_ACTIVE)

        builder = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=messages.ButtonTexts.DONATE,
                        url=messages.URLs.PAYMENT_URL,
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=messages.ButtonTexts.SEND_CHECK,
                        callback_data=messages.CallbackData.SEND_CHECK,
                    )
                ],
            ]
        )
        count_active_refferal = await self.referral_repository.count_all_active_referral(
            referrer_id=callback_query.from_user.id
        )
        price = int(subscription.amount * (1 - entities.DISCOUNT * count_active_refferal / 100))
        await callback_query.message.answer(
            messages.MessageTemplates.PAYMENT_INFO.format(
                amount=price,
            ),
            reply_markup=builder,
        )


@dataclass
class SupportUsecase:
    async def __call__(self, callback_query: types.CallbackQuery, state: FSMContext) -> None:
        if not callback_query.message:
            return
        await callback_query.message.answer(messages.ActionRequiredMessages.SUPPORT_REQUEST)

        await state.set_state(messages.FSMStates.WAITING_FOR_SUPPORT_MESSAGE)


@dataclass
class SendCheckUsecase:
    async def __call__(self, callback_query: types.CallbackQuery, state: FSMContext) -> None:
        if not callback_query.message:
            return
        await callback_query.message.answer(messages.ActionRequiredMessages.SUPPORT_CHECK_REQUEST)
        await state.set_state(messages.FSMStates.WAITING_FOR_CHECK_MESSAGE)


@dataclass
class SupporMessagetUsecase:
    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        if not message.from_user or not message.bot:
            return

        await message.answer(messages.StatusMessages.MESSAGE_SENT)

        username = message.from_user.username or str(message.from_user.id)
        text = message.text or message.caption or messages.Constants.NO_TEXT_PLACEHOLDER

        support_message = messages.MessageTemplates.SUPPORT_MESSAGE.format(
            user_id=message.from_user.id,
            username=username,
            text=text
        )

        if message.photo:
            photo = message.photo[-1]
            await message.bot.send_photo(
                settings.admin_id,
                photo.file_id,
                caption=support_message,
                parse_mode=None,
            )
        elif message.document:
            await message.bot.send_document(
                settings.admin_id,
                message.document.file_id,
                caption=support_message,
                parse_mode=None,
            )
        else:
            await message.bot.send_message(settings.admin_id, support_message, parse_mode=None)

        await state.clear()


@dataclass
class BroadcastUsecase:
    user_repository: repositories.UserRepository

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        if not message.from_user:
            return

        # Проверяем права администратора
        if message.from_user.id != settings.admin_id:
            return

        await message.answer(messages.BROADCAST_REQUEST_MESSAGE)
        await state.set_state(messages.FSMStates.WAITING_FOR_BROADCAST_MESSAGE)


@dataclass
class BroadcastMessageUsecase:
    user_repository: repositories.UserRepository

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        # Получаем всех пользователей
        users = await self.user_repository.find_all()
        user_count = len(users)

        # Сохраняем сообщение в состоянии
        await state.update_data(broadcast_message=message)

        # Создаем клавиатуру подтверждения
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=messages.ButtonTexts.BROADCAST_CONFIRM,
                        callback_data=messages.CallbackData.BROADCAST_CONFIRM,
                    ),
                    InlineKeyboardButton(
                        text=messages.ButtonTexts.BROADCAST_CANCEL,
                        callback_data=messages.CallbackData.BROADCAST_CANCEL,
                    ),
                ]
            ]
        )

        # Отправляем подтверждение без markdown парсинга
        await message.answer(
            messages.BROADCAST_CONFIRMATION_MESSAGE.format(count=user_count),
            reply_markup=keyboard,
            parse_mode=None,
        )


@dataclass
class BroadcastConfirmUsecase:
    user_repository: repositories.UserRepository

    async def __call__(self, callback_query: types.CallbackQuery, state: FSMContext) -> None:
        if not callback_query.message or not callback_query.bot:
            return

        # Получаем сохраненное сообщение
        data = await state.get_data()
        broadcast_message = data.get("broadcast_message")

        if not isinstance(broadcast_message, types.Message):
            await callback_query.message.answer("Ошибка: сообщение для рассылки не найдено")
            await state.clear()
            return

        # Получаем всех пользователей
        users = await self.user_repository.find_all()
        sent_count = 0

        # Отправляем сообщение всем пользователям
        for user in users:
            try:
                if broadcast_message.text:
                    await callback_query.bot.send_message(
                        chat_id=user.id,
                        text=broadcast_message.text,
                        entities=broadcast_message.entities,
                        parse_mode=None,
                    )
                elif broadcast_message.photo:
                    await callback_query.bot.send_photo(
                        chat_id=user.id,
                        photo=broadcast_message.photo[-1].file_id,
                        caption=broadcast_message.caption,
                        caption_entities=broadcast_message.caption_entities,
                        parse_mode=None,
                    )
                elif broadcast_message.document:
                    await callback_query.bot.send_document(
                        chat_id=user.id,
                        document=broadcast_message.document.file_id,
                        caption=broadcast_message.caption,
                        caption_entities=broadcast_message.caption_entities,
                        parse_mode=None,
                    )
                elif broadcast_message.video:
                    await callback_query.bot.send_video(
                        chat_id=user.id,
                        video=broadcast_message.video.file_id,
                        caption=broadcast_message.caption,
                        caption_entities=broadcast_message.caption_entities,
                        parse_mode=None,
                    )
                elif broadcast_message.audio:
                    await callback_query.bot.send_audio(
                        chat_id=user.id,
                        audio=broadcast_message.audio.file_id,
                        caption=broadcast_message.caption,
                        caption_entities=broadcast_message.caption_entities,
                        parse_mode=None,
                    )
                elif broadcast_message.voice:
                    await callback_query.bot.send_voice(
                        chat_id=user.id,
                        voice=broadcast_message.voice.file_id,
                        caption=broadcast_message.caption,
                        caption_entities=broadcast_message.caption_entities,
                        parse_mode=None,
                    )
                elif broadcast_message.sticker:
                    await callback_query.bot.send_sticker(
                        chat_id=user.id,
                        sticker=broadcast_message.sticker.file_id,
                    )

                sent_count += 1
            except Exception as e:
                # Логируем ошибку, но продолжаем рассылку
                print(f"Ошибка отправки сообщения пользователю {user.id}: {e}")
        await state.clear()


@dataclass
class BroadcastCancelUsecase:
    async def __call__(self, callback_query: types.CallbackQuery, state: FSMContext) -> None:
        if not callback_query.message:
            return
        await callback_query.message.answer(messages.BROADCAST_CANCELLED_MESSAGE, parse_mode=None)
        await state.clear()
