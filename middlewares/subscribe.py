from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from config import config
from keyboards import subscribe_kb


class SubscribeMiddleware(BaseMiddleware):
    """Har bir xabar/callback'dan oldin foydalanuvchi kanalga obuna ekanini tekshiradi.
    Adminlar tekshiruvdan ozod qilinadi."""

    async def __call__(self, handler, event, data):
        if not config.required_channel:
            return await handler(event, data)

        user = event.from_user
        if user is None or user.id in config.admin_ids:
            return await handler(event, data)

        bot = data["bot"]
        is_subscribed = True
        try:
            member = await bot.get_chat_member(config.required_channel, user.id)
            if member.status in ("left", "kicked"):
                is_subscribed = False
        except Exception:
            is_subscribed = False

        if not is_subscribed:
            text = "Botdan foydalanish uchun avval kanalga obuna bo'ling 👇"
            kb = subscribe_kb(config.required_channel)
            if isinstance(event, Message):
                await event.answer(text, reply_markup=kb)
            elif isinstance(event, CallbackQuery):
                await event.answer()
                await event.message.answer(text, reply_markup=kb)
            return

        return await handler(event, data)
