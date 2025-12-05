import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
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

# Путь для вебхука
WEBHOOK_PATH = f"/bot/{CONFIG.tg_bot.token}"
WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = 8080


async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(f"{CONFIG.tg_bot.webhook_url}{WEBHOOK_PATH}")


async def on_shutdown(bot: Bot) -> None:
    await bot.delete_webhook(drop_pending_updates=True)


def main() -> None:
    # Создаём приложение
    app = web.Application()

    # Регистрируем обработчик вебхука
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)

    # Настройка graceful shutdown
    setup_application(app, dp, bot=bot)

    # Добавляем обработчики startup/shutdown
    app.on_startup.append(lambda app: on_startup(bot))
    app.on_shutdown.append(lambda app: on_shutdown(bot))

    # Запускаем сервер
    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)


if __name__ == "__main__":
    main()