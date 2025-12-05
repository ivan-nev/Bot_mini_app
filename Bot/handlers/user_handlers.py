import json
from datetime import datetime, timezone, timedelta
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from keybords import inline_menu

uts = timezone(timedelta(hours=5))

router = Router()


@router.message(CommandStart())
async def start(message: Message):
    await message.answer(text="расчёт резьб", reply_markup=inline_menu.create_menu_thread())


@router.message(F.web_app_data)
async def web_app_handler(message: Message):
    """Основной обработчик Web App данных"""
    # Получаем и парсим данные
    d = message.web_app_data.data
    print(d)
    await message.answer(d)
    # await message.answer()
    # await message.answer(text=message.web_app_data)
    # data = json.loads(message.web_app_data.data)
    # print(data)
    # d=(data.get('time'))
    # date = datetime.fromisoformat(d)
    # date_uts = date.astimezone(uts)
    # await message.answer(f"{data.get('data_input_row')}\n\n"
    #                      f"{data.get('answer_row')}\n\n"
    #                      f'⏰Расчёт выполнен в {date_uts.strftime("%H:%M %d.%m.%Y")}',
    #                      reply_markup=inline_menu.create_menu_thread())

