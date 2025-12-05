import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, AiohttpWebServer
from aiohttp import web

from handlers import user_handlers
from config.config import load_config

# Загружаем конфиг
CONFIG = load_config()

# Настройка бота и диспетчера
bot = Bot(token=CONFIG.tg_bot.token)
dp = Dispatcher()

# Логирование
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Подключаем роутеры
dp.include_router(user_handlers.router)

# Путь, по которому Telegram будет присылать обновления
WEBHOOK_PATH = f"/bot/{CONFIG.tg_bot.token}"
WEB_SERVER_HOST = "0.0.0.0"  # слушаем все интерфейсы
WEB_SERVER_PORT = 8080       # порт бота (не 8000 — это для FastAPI)

async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(f"{CONFIG.tg_bot.webhook_url}{WEBHOOK_PATH}")

async def on_shutdown(bot: Bot) -> None:
    await bot.delete_webhook(drop_pending_updates=True)

def main() -> None:
    # Регистрируем обработчики startup/shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Создаём AIOHTTP приложение
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    AiohttpWebServer(
        app=app,
        host=WEB_SERVER_HOST,
        port=WEB_SERVER_PORT,
    ).run_app()

if __name__ == "__main__":
    main()