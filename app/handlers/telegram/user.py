from aiogram import Router, types
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from vi_core.sqlalchemy import UnitOfWork

from app import entities, messages
from app.adapters.postgresql import repositories
from app.adapters.protocols.factory import ProtocolFactory
from app.handlers.telegram.deps import get_database
from app.usecases import user

router = Router()


@router.message(CommandStart())
async def command_start_handler(message: types.Message, state: FSMContext) -> None:
    database = get_database()
    async with database.session() as session:
        user_repository = repositories.UserRepository(session=session)
        uow = UnitOfWork(session=session)
        subscription_repository = repositories.SubscriptionRepository(session=session)
        referral_repository = repositories.ReferralRepository(session=session)
        server_repository = repositories.ServerRepository(session=session)
        protocol_factory = ProtocolFactory()

        start_user_usecase = user.StartUserUsecase(
            user_repository=user_repository,
            uow=uow,
            subscription_repository=subscription_repository,
            referral_repository=referral_repository,
            server_repository=server_repository,
            protocol_factory=protocol_factory,
        )
        await start_user_usecase(message, state)


@router.message(Command("broadcast"))
async def command_broadcast_handler(message: types.Message, state: FSMContext) -> None:
    database = get_database()
    async with database.session() as session:
        user_repository = repositories.UserRepository(session=session)

        broadcast_usecase = user.BroadcastUsecase(user_repository=user_repository)
        await broadcast_usecase(message, state)


@router.callback_query(lambda message: message.data == messages.CallbackData.ACCOUNT)
async def process_account_callback(callback_query: types.CallbackQuery) -> None:
    database = get_database()
    async with database.session() as session:
        user_repository = repositories.UserRepository(session=session)
        uow = UnitOfWork(session=session)
        server_repository = repositories.ServerRepository(session=session)

        account_usecase = user.AccountUsecase(user_repository=user_repository,
                                              server_repository=server_repository,
                                              uow=uow)
        await account_usecase(callback_query)

@router.callback_query(lambda message: message.data == messages.CallbackData.SWAP_COUNTRY)
async def process_swap_country_callback(callback_query: types.CallbackQuery) -> None:
    database = get_database()
    async with database.session() as session:
        user_repository = repositories.UserRepository(session=session)
        server_repository = repositories.ServerRepository(session=session)

        swap_country_usecase = user.SwapCountryUsecase(
            user_repository=user_repository,
            server_repository=server_repository,
        )
        await swap_country_usecase(callback_query)


@router.callback_query(lambda message: message.data == messages.CallbackData.SWAP_PROTOCOL)
async def process_swap_protocol_callback(callback_query: types.CallbackQuery) -> None:
    database = get_database()
    async with database.session() as session:
        user_repository = repositories.UserRepository(session=session)

        swap_protocol_usecase = user.SwapProtocolUsecase(
            user_repository=user_repository,
        )
        await swap_protocol_usecase(callback_query)


@router.callback_query(lambda callback: callback.data and callback.data.startswith("country_"))
async def process_confirm_swap_country_callback(callback_query: types.CallbackQuery) -> None:
    # Извлекаем ID сервера из callback_data
    if not callback_query.data:
        return
    server_id = int(callback_query.data.split("_")[1])

    database = get_database()
    async with database.session() as session:
        user_repository = repositories.UserRepository(session=session)
        subscription_repository = repositories.SubscriptionRepository(session=session)
        server_repository = repositories.ServerRepository(session=session)
        protocol_factory = ProtocolFactory()
        uow = UnitOfWork(session=session)

        confirm_swap_country_usecase = user.ConfirmSwapCountryUsecase(
            user_repository=user_repository,
            subscription_repository=subscription_repository,
            server_repository=server_repository,
            protocol_factory=protocol_factory,
            uow=uow,
        )
        await confirm_swap_country_usecase(callback_query, server_id)


@router.callback_query(lambda callback: callback.data and callback.data.startswith("protocol_"))
async def process_confirm_swap_protocol_callback(callback_query: types.CallbackQuery) -> None:
    # Извлекаем протокол из callback_data
    if not callback_query.data:
        return
    protocol_value = entities.Protocol(callback_query.data.split("_")[1])

    database = get_database()
    async with database.session() as session:
        user_repository = repositories.UserRepository(session=session)
        subscription_repository = repositories.SubscriptionRepository(session=session)
        server_repository = repositories.ServerRepository(session=session)
        protocol_factory = ProtocolFactory()
        uow = UnitOfWork(session=session)

        confirm_swap_protocol_usecase = user.ConfirmSwapProtocolUsecase(
            user_repository=user_repository,
            subscription_repository=subscription_repository,
            server_repository=server_repository,
            protocol_factory=protocol_factory,
            uow=uow,
        )
        await confirm_swap_protocol_usecase(callback_query, protocol_value)


@router.callback_query(lambda message: message.data == messages.CallbackData.TEAM)
async def process_referral_callback(callback_query: types.CallbackQuery) -> None:
    database = get_database()
    async with database.session() as session:
        user_repository = repositories.UserRepository(session=session)
        referral_repository = repositories.ReferralRepository(session=session)

        referral_usecase = user.ReferralUsecase(
            user_repository=user_repository,
            referral_repository=referral_repository,
        )
        await referral_usecase(callback_query)


@router.callback_query(lambda message: message.data == messages.CallbackData.NOTIFICATIONS)
async def process_notifications_callback(callback_query: types.CallbackQuery) -> None:
    database = get_database()
    async with database.session() as session:
        user_repository = repositories.UserRepository(session=session)
        uow = UnitOfWork(session=session)
        subscription_repository = repositories.SubscriptionRepository(session=session)

        notifications_usecase = user.NotificationsUsecase(
            user_repository=user_repository,
            uow=uow,
            subscription_repository=subscription_repository,
        )
        await notifications_usecase(callback_query)


@router.callback_query(lambda message: message.data == messages.CallbackData.INSTRUCTIONS)
async def process_instructions_callback(callback_query: types.CallbackQuery) -> None:
    instructions_usecase = user.InstructionsUsecase()
    await instructions_usecase(callback_query)


@router.callback_query(lambda message: message.data == messages.CallbackData.INSTRUCTION_CONNECT)
async def process_instruction_connect_callback(callback_query: types.CallbackQuery) -> None:
    if callback_query.message:
        await callback_query.message.answer(messages.InstructionTexts.CONNECT, disable_web_page_preview=True)


@router.callback_query(lambda message: message.data == messages.CallbackData.INSTRUCTION_REFERRAL)
async def process_instruction_referral_callback(callback_query: types.CallbackQuery) -> None:
    if callback_query.message:
        await callback_query.message.answer(messages.InstructionTexts.REFERRAL, disable_web_page_preview=True)


@router.callback_query(lambda message: message.data == messages.CallbackData.INSTRUCTION_UPDATE)
async def process_instruction_update_callback(callback_query: types.CallbackQuery) -> None:
    if callback_query.message:
        await callback_query.message.answer(messages.InstructionTexts.UPDATE, disable_web_page_preview=True)


@router.callback_query(lambda message: message.data == messages.CallbackData.DONATE)
async def command_donate_handler(callback_query: types.CallbackQuery) -> None:
    database = get_database()
    async with database.session() as session:
        user_repository = repositories.UserRepository(session=session)
        subscription_repository = repositories.SubscriptionRepository(session=session)
        referral_repository = repositories.ReferralRepository(session=session)
        donate_usecase = user.DonateUsecase(
            user_repository=user_repository,
            subscription_repository=subscription_repository,
            referral_repository=referral_repository,
        )
        await donate_usecase(callback_query)


@router.callback_query(lambda message: message.data == messages.CallbackData.SUPPORT)
async def start_support(callback_query: types.CallbackQuery, state: FSMContext) -> None:
    support_usecase = user.SupportUsecase()
    await support_usecase(callback_query, state)


@router.callback_query(lambda message: message.data == messages.CallbackData.KEY)
async def process_key_callback(callback_query: types.CallbackQuery) -> None:
    database = get_database()
    async with database.session() as session:
        user_repository = repositories.UserRepository(session=session)

        key_usecase = user.KeyUsecase(user_repository=user_repository)
        await key_usecase(callback_query)


@router.callback_query(lambda message: message.data == messages.CallbackData.REISSUE_KEY)
async def process_reissue_key_callback(callback_query: types.CallbackQuery) -> None:
    database = get_database()
    async with database.session() as session:
        user_repository = repositories.UserRepository(session=session)
        subscription_repository = repositories.SubscriptionRepository(session=session)
        server_repository = repositories.ServerRepository(session=session)
        uow = UnitOfWork(session=session)
        protocol_factory = ProtocolFactory()

        reissue_key_usecase = user.ReissueKeyUsecase(
            user_repository=user_repository,
            subscription_repository=subscription_repository,
            uow=uow,
            protocol_factory=protocol_factory,
            server_repository=server_repository,
        )
        await reissue_key_usecase(callback_query)


@router.callback_query(lambda message: message.data == messages.CallbackData.SEND_CHECK)
async def send_check(callback_query: types.CallbackQuery, state: FSMContext) -> None:
    send_check_usecase = user.SendCheckUsecase()
    await send_check_usecase(callback_query, state)


@router.message(StateFilter(messages.FSMStates.WAITING_FOR_CHECK_MESSAGE))
async def forward_check_to_admin(message: types.Message, state: FSMContext) -> None:
    database = get_database()
    async with database.session() as session:
        user_repository = repositories.UserRepository(session=session)
        subscription_repository = repositories.SubscriptionRepository(session=session)
        server_repository = repositories.ServerRepository(session=session)
        uow = UnitOfWork(session=session)
        protocol_factory = ProtocolFactory()

        send_check_usecase = user.SendMessageCheckUsecase(
            user_repository=user_repository,
            subscription_repository=subscription_repository,
            uow=uow,
            server_repository=server_repository,
            protocol_factory=protocol_factory,
        )
        await send_check_usecase(message, state)


@router.message(StateFilter(messages.FSMStates.WAITING_FOR_SUPPORT_MESSAGE))
async def forward_to_admin(message: types.Message, state: FSMContext) -> None:
    support_usecase = user.SupporMessagetUsecase()
    await support_usecase(message, state)


@router.message(StateFilter(messages.FSMStates.WAITING_FOR_BROADCAST_MESSAGE))
async def process_broadcast_message(message: types.Message, state: FSMContext) -> None:
    database = get_database()
    async with database.session() as session:
        user_repository = repositories.UserRepository(session=session)

        broadcast_message_usecase = user.BroadcastMessageUsecase(user_repository=user_repository)
        await broadcast_message_usecase(message, state)


@router.callback_query(lambda callback: callback.data == messages.CallbackData.BROADCAST_CONFIRM)
async def process_broadcast_confirm(callback_query: types.CallbackQuery, state: FSMContext) -> None:
    database = get_database()
    async with database.session() as session:
        user_repository = repositories.UserRepository(session=session)

        broadcast_confirm_usecase = user.BroadcastConfirmUsecase(user_repository=user_repository)
        await broadcast_confirm_usecase(callback_query, state)


@router.callback_query(lambda callback: callback.data == messages.CallbackData.BROADCAST_CANCEL)
async def process_broadcast_cancel(callback_query: types.CallbackQuery, state: FSMContext) -> None:
    broadcast_cancel_usecase = user.BroadcastCancelUsecase()
    await broadcast_cancel_usecase(callback_query, state)
