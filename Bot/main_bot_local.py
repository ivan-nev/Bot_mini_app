import logging
import sys
from aiogram import Bot, Dispatcher

from handlers import user_handlers

from config.config import load_config

CONFIG = load_config()
bot = Bot(token=CONFIG.tg_bot.token)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

dp.include_router(user_handlers.router)

if __name__ == '__main__':
    dp.run_polling(bot)
