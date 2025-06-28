from aiogram import Router, types, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from app.adapters.wireguard.async_manager import AsyncWireGuardClientManager
from app.settings import settings
from vi_core.sqlalchemy import UnitOfWork

from app.adapters.postgresql.repositories import SubscriptionRepository, UserRepository
from app.handlers.telegram.deps import get_database
from app.usecases import user
from app import messages

router = Router()


@router.message(CommandStart())
async def command_start_handler(message: types.Message, state: FSMContext) -> None:
    database = get_database()
    async with database.session() as session:
        user_repository = UserRepository(session=session)
        uow = UnitOfWork(session=session)
        subscription_repository = SubscriptionRepository(session=session)

        start_user_usecase = user.StartUserUsecase(
            user_repository=user_repository,
            uow=uow,
            subscription_repository=subscription_repository,
        )
        await start_user_usecase(message, state)


@router.callback_query(lambda message: message.data == "account")
async def process_account_callback(callback_query: types.CallbackQuery) -> None:
    database = get_database()
    async with database.session() as session:
        user_repository = UserRepository(session=session)
        uow = UnitOfWork(session=session)

        account_usecase = user.AccountUsecase(user_repository=user_repository, uow=uow)
        await account_usecase(callback_query)


@router.callback_query(lambda message: message.data == "notifications")
async def process_notifications_callback(callback_query: types.CallbackQuery) -> None:
    database = get_database()
    async with database.session() as session:
        user_repository = UserRepository(session=session)
        uow = UnitOfWork(session=session)
        subscription_repository = SubscriptionRepository(session=session)

        notifications_usecase = user.NotificationsUsecase(
            user_repository=user_repository,
            uow=uow,
            subscription_repository=subscription_repository,
        )
        await notifications_usecase(callback_query)


@router.callback_query(lambda message: message.data == "instructions")
async def process_instructions_callback(callback_query: types.CallbackQuery) -> None:
    instructions_usecase = user.InstructionsUsecase()
    await instructions_usecase(callback_query)


@router.callback_query(lambda message: message.data == "instruction_connect")
async def process_instruction_connect_callback(callback_query: types.CallbackQuery) -> None:
    await callback_query.message.answer(messages.InstructionTexts.CONNECT, disable_web_page_preview=True)


@router.callback_query(lambda message: message.data == "instruction_speed")
async def process_instruction_speed_callback(callback_query: types.CallbackQuery) -> None:
    instruction_speed_usecase = user.InstructionSpeedUsecase()
    await instruction_speed_usecase(callback_query)


@router.callback_query(lambda message: message.data == "instruction_exclude")
async def process_instruction_exclude_callback(callback_query: types.CallbackQuery) -> None:
    await callback_query.message.answer(messages.InstructionTexts.EXCLUDE, disable_web_page_preview=True)


@router.callback_query(lambda message: message.data == "instruction_referral")
async def process_instruction_referral_callback(callback_query: types.CallbackQuery) -> None:
    await callback_query.message.answer(messages.InstructionTexts.REFERRAL, disable_web_page_preview=True)


@router.callback_query(lambda message: message.data == "instruction_update")
async def process_instruction_update_callback(callback_query: types.CallbackQuery) -> None:
    await callback_query.message.answer(messages.InstructionTexts.UPDATE, disable_web_page_preview=True)


@router.callback_query(lambda message: message.data == "donate")
async def command_donate_handler(callback_query: types.CallbackQuery) -> None:
    database = get_database()
    async with database.session() as session:
        user_repository = UserRepository(session=session)
        subscription_repository = SubscriptionRepository(session=session)

        donate_usecase = user.DonateUsecase(
            user_repository=user_repository,
            subscription_repository=subscription_repository,
        )
        await donate_usecase(callback_query)


@router.callback_query(lambda message: message.data == "support")
async def start_support(callback_query: types.CallbackQuery, state: FSMContext) -> None:
    support_usecase = user.SupportUsecase()
    await support_usecase(callback_query, state)


@router.callback_query(lambda message: message.data == "send_check")
async def send_check(callback_query: types.CallbackQuery, state: FSMContext) -> None:
    send_check_usecase = user.SendCheckUsecase()
    await send_check_usecase(callback_query, state)


@router.message(StateFilter("waiting_for_check_message"))
async def forward_check_to_admin(message: types.Message, state: FSMContext) -> None:
    database = get_database()
    async with database.session() as session:
        user_repository = UserRepository(session=session)
        subscription_repository = SubscriptionRepository(session=session)
        uow = UnitOfWork(session=session)
        wireguard_manager = AsyncWireGuardClientManager(
            host=settings.server_host,
            user=settings.server_user,
            password=settings.server_password,
        )

        send_check_usecase = user.SendMessageCheckUsecase(
            user_repository=user_repository,
            subscription_repository=subscription_repository,
            uow=uow,
            wireguard_manager=wireguard_manager,
        )
        await send_check_usecase(message, state)


@router.message(StateFilter("waiting_for_support_message"))
async def forward_to_admin(message: types.Message, state: FSMContext) -> None:
    support_usecase = user.SupporMessagetUsecase()
    await support_usecase(message, state)
