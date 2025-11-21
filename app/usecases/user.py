
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from vi_core.sqlalchemy import UnitOfWork

from app import entities, messages
from app.adapters.postgresql import repositories
from app.adapters.xui.client import XuiClient
from app.settings import settings

DAYS_IN_MONTH = 30


@dataclass
class StartUserUsecase:
    user_repository: repositories.UserRepository
    uow: UnitOfWork
    subscription_repository: repositories.SubscriptionRepository
    referral_repository: repositories.ReferralRepository
    xui_client: XuiClient

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

            await self.xui_client.add_client(email=str(message.from_user.id), user_uuid=str(new_user.id), days=3)
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

        message = messages.ACCOUNT_TEXT.format(
            username=callback_query.from_user.first_name,
            subscription_status=subscription_status,
            end_date=end_date,
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Показать подписку",
                        url=f"{settings.xui_url_subscriptions}/{user.id}",
                    ),
                ]
            ]
        )
        await callback_query.message.answer(message, reply_markup=keyboard)


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
    xui_client: XuiClient

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

        days = DAYS_IN_MONTH + (subscription.end_date - datetime.now()).days
        await self.xui_client.update_client(user_uuid=str(message.from_user.id), email=str(message.from_user.id), days=days)
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
