import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

import database as db
from config import config
from handlers import admin, user
from middlewares.subscribe import SubscribeMiddleware


async def main():
    logging.basicConfig(level=logging.INFO)

    if not config.bot_token:
        raise RuntimeError("BOT_TOKEN sozlanmagan (.env faylni tekshiring)")

    await db.init_db()

    session = None
    if config.bot_api_base and "api.telegram.org" not in config.bot_api_base:
        local_server = TelegramAPIServer.from_base(config.bot_api_base)
        session = AiohttpSession(api=local_server)
        logging.info("Local Bot API server ishlatilmoqda: %s", config.bot_api_base)

    bot = Bot(token=config.bot_token, session=session)
    dp = Dispatcher()

    dp.message.middleware(SubscribeMiddleware())
    dp.callback_query.middleware(SubscribeMiddleware())

    # admin routerini birinchi ulaymiz, aks holda uning buyruqlari
    # user routerdagi umumiy handlerlar tomonidan "yutib" ketilishi mumkin
    dp.include_router(admin.router)
    dp.include_router(user.router)

    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Bot ishga tushdi.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
