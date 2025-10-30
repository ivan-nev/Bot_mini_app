from dataclasses import dataclass
from environs import Env
import os
import logging
logging.basicConfig(level=logging.INFO)


@dataclass
class TgBot:
    token: str

@dataclass
class Config:
    tg_bot: TgBot

def load_config(path: str|None = None) -> Config:
    if 'CONTEINER' not in os.environ:
        path = '.env_local'
        print ('Старт вне контейнера')
        logging.info('Запуск вне контейнера')
    env = Env()
    env.read_env(path)
    return Config(tg_bot=TgBot(token=env('BOT_TOKEN')))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print(load_config().tg_bot.token)