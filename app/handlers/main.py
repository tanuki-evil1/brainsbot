import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from app.handlers.telegram import root
from app.settings import settings
from app.tasks.subscriptions import monthly_check_loop

dp = Dispatcher()
dp.include_router(root)


async def main() -> None:
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2),
    )
    await bot.set_my_commands([BotCommand(command="start", description="Главное меню")])
    asyncio.create_task(monthly_check_loop(bot))
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
