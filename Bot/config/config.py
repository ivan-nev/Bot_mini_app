from dataclasses import dataclass
from environs import Env
import os
import logging
logging.basicConfig(level=logging.INFO)


@dataclass
class TgBot:
    token: str
    webhook_url: str

@dataclass
class Config:
    tg_bot: TgBot

def load_config(path: str|None = None) -> Config:
    if 'CONTEINER' not in os.environ:
        path = '.env_local'
        logging.info('Запуск вне контейнера')
    env = Env()
    env.read_env(path)
    return Config(tg_bot=TgBot(token=env('BOT_TOKEN'), webhook_url=env('WEBHOOK_URL')))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print(load_config().tg_bot.token)
    print(load_config().tg_bot.webhook_url)