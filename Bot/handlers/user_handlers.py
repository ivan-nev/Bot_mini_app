import json

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from Bot.keybords import inline_menu

router = Router()


@router.message(CommandStart())
async def start(message: Message):
    await message.answer(text="расчёт резьб", reply_markup=inline_menu.create_menu_thread())
