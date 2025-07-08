from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart
from vi_core.sqlalchemy import UnitOfWork

from app import entities, messages
from app.settings import settings
from app.adapters.postgresql.repositories import ReferralRepository, SubscriptionRepository, UserRepository
from app.adapters.wireguard.async_manager import AsyncWireGuardClientManager


DAYS_IN_MONTH = 30


@dataclass
class StartUserUsecase:
    user_repository: UserRepository
    uow: UnitOfWork
    subscription_repository: SubscriptionRepository
    referral_repository: ReferralRepository

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        user = await self.user_repository.find_one(id=message.from_user.id)
        if not user:
            new_user = entities.User(
                id=message.from_user.id,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name or "",
                username=message.from_user.username or "",
                language_code=message.from_user.language_code or "",
            )
            new_subscription = entities.Subscription(
                user_id=new_user.id,
            )
            await self.user_repository.add_one(new_user)
            await self.subscription_repository.add_one(new_subscription)

            referrer_id = message.text.split(" ", 1)
            if len(referrer_id) > 1 and referrer_id[1].startswith("ref_"):
                referrer_id = int(referrer_id[1][4:])
                referrer = await self.user_repository.find_one(id=referrer_id)
                if referrer:
                    new_referral = entities.Referral(
                        referrer_id=referrer_id,
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
    user_repository: UserRepository
    uow: UnitOfWork

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        user = await self.user_repository.find_one(id=callback_query.from_user.id)

        message = messages.ACCOUNT_TEXT.format(
            username=callback_query.from_user.first_name,
            subscription_status=messages.StatusMessages.SUBSCRIPTION_ACTIVE
            if user.subscription.is_active
            else messages.StatusMessages.SUBSCRIPTION_INACTIVE,
            end_date=messages.MessageTemplates.END_DATE_FORMAT.format(
                date=user.subscription.end_date.strftime("%d.%m.%Y"),
                days=(user.subscription.end_date.date() - datetime.now().date()).days,
                days_text=messages.Constants.DAYS_TEXT,
            )
            if user.subscription.end_date
            else messages.StatusMessages.SUBSCRIPTION_NO_END_DATE,
            key=user.subscription.key if user.subscription.key else messages.StatusMessages.SUBSCRIPTION_NO_KEY,
        )
        await callback_query.message.answer(message)


@dataclass
class ReferralUsecase:
    user_repository: UserRepository
    referral_repository: ReferralRepository

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        referrals = await self.referral_repository.find_all(referrer_id=callback_query.from_user.id)
        referral_text = ""
        for referral in referrals:
            if referral.referral.subscription.is_active:
                referral_text += messages.MessageTemplates.REFERRAL_USER_FORMAT.format(
                    first_name=referral.referral.first_name,
                    username=referral.referral.username,
                    separator=messages.Constants.SUBSCRIPTION_SEPARATOR,
                    status=messages.StatusMessages.SUBSCRIPTION_ACTIVE,
                )
            else:
                referral_text += messages.MessageTemplates.REFERRAL_USER_FORMAT.format(
                    first_name=referral.referral.first_name,
                    username=referral.referral.username,
                    separator=messages.Constants.SUBSCRIPTION_SEPARATOR,
                    status=messages.StatusMessages.SUBSCRIPTION_INACTIVE,
                )
        count_active_refferal = await self.referral_repository.count_all_active_referral(
            referrer_id=callback_query.from_user.id
        )
        await callback_query.message.answer(
            messages.REFERRAL_TEXT.format(
                referrals=referral_text,
                referral_link=callback_query.from_user.id,
                discount=entities.DISCOUNT * count_active_refferal,
            )
        )


@dataclass
class InstructionsUsecase:
    async def __call__(self, callback_query: types.CallbackQuery) -> None:
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
                [
                    InlineKeyboardButton(
                        text=messages.ButtonTexts.INSTRUCTION_SPEED,
                        callback_data=messages.CallbackData.INSTRUCTION_SPEED,
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=messages.ButtonTexts.INSTRUCTION_EXCLUDE,
                        callback_data=messages.CallbackData.INSTRUCTION_EXCLUDE,
                    ),
                ],
            ]
        )
        await callback_query.message.answer(messages.INSTRUCTIONS_TEXT, reply_markup=keyboard)


@dataclass
class NotificationsUsecase:
    user_repository: UserRepository
    uow: UnitOfWork
    subscription_repository: SubscriptionRepository

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        user = await self.user_repository.find_one(id=callback_query.from_user.id)

        if not user.subscription.is_active:
            await callback_query.message.answer(messages.ActionRequiredMessages.NOTIFICATIONS_ACTIVATION_REQUIRED)
            return None

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
    user_repository: UserRepository
    uow: UnitOfWork
    subscription_repository: SubscriptionRepository
    wireguard_manager: AsyncWireGuardClientManager

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        text = message.text or message.caption or messages.Constants.NO_TEXT_PLACEHOLDER

        check_message = messages.MessageTemplates.CHECK_INFO.format(username=message.from_user.username, text=text)

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
        if not subscription.key:
            async with self.wireguard_manager as manager:
                user_config = await manager.create_config(username=message.from_user.id)
        else:
            user_config = entities.WireGuardUserConfig(
                client_public_key=subscription.public_key,
                access_key=subscription.key,
                allowed_ip=subscription.allowed_ip,
                username=message.from_user.id,
            )

        async with self.wireguard_manager as manager:
            await manager.add_user(user_config)

        updated_subscription = replace(
            subscription,
            end_date=datetime.now() + timedelta(days=DAYS_IN_MONTH)
            if not subscription.end_date
            else subscription.end_date + timedelta(days=DAYS_IN_MONTH),
            is_notify=True,
            is_active=True,
            key=user_config.access_key,
            public_key=user_config.client_public_key,
            allowed_ip=user_config.allowed_ip,
        )
        await self.subscription_repository.edit_one(updated_subscription)

        await self.uow.commit()

        await message.answer(messages.StatusMessages.MESSAGE_SENT_ACCESS_GRANTED)


@dataclass
class DonateUsecase:
    user_repository: UserRepository
    subscription_repository: SubscriptionRepository
    referral_repository: ReferralRepository

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
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
        await callback_query.message.answer(messages.ActionRequiredMessages.SUPPORT_REQUEST)

        await state.set_state(messages.FSMStates.WAITING_FOR_SUPPORT_MESSAGE)


@dataclass
class SendCheckUsecase:
    async def __call__(self, callback_query: types.CallbackQuery, state: FSMContext) -> None:
        await callback_query.message.answer(messages.ActionRequiredMessages.SUPPORT_CHECK_REQUEST)
        await state.set_state(messages.FSMStates.WAITING_FOR_CHECK_MESSAGE)


@dataclass
class SupporMessagetUsecase:
    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        await message.answer(messages.StatusMessages.MESSAGE_SENT)

        username = message.from_user.username or str(message.from_user.id)
        text = message.text or message.caption or messages.Constants.NO_TEXT_PLACEHOLDER

        support_message = messages.MessageTemplates.SUPPORT_MESSAGE.format(username=username, text=text)

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
class InstructionSpeedUsecase:
    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        await callback_query.message.answer(messages.InstructionTexts.SPEED)
        await callback_query.message.answer_document(types.FSInputFile("amnezia_sites.json"))
