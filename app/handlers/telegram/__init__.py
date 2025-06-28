from aiogram import Router

from app.handlers.telegram.user import router as user_router

root = Router()

root.include_router(user_router)
