import json
from datetime import datetime, timezone, timedelta
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from keybords import inline_menu

# UTC+5 (например, для Ташкента, Екатеринбурга и др.)
uts = timezone(timedelta(hours=5))

router = Router()


@router.message(CommandStart())
async def start(message: Message):
    """
    Обработчик команды /start
    Приветствует пользователя и показывает главное меню
    """
    await message.answer(
        text="🔧 <b>Расчёт резьб</b>\n\n"
             "Выберите тип резьбы ниже 👇",
        reply_markup=inline_menu.create_menu_thread(),
        parse_mode="HTML"
    )


@router.message(F.web_app_data)
async def web_app_handler(message: Message):
    """
    Обработчик данных из Mini App
    Принимает данные, парсит и красиво отображает результат
    """
    try:
        data = json.loads(message.web_app_data.data)

        # Извлекаем данные
        input_data = data.get("data_input_row", "Не указано")
        answer = data.get("answer_row", "Не рассчитано")
        timestamp = data.get("time")

        # Форматируем время в UTC+5
        if timestamp:
            date = datetime.fromisoformat(timestamp)
            date_uts = date.astimezone(uts)
            time_str = date_uts.strftime("%H:%M • %d.%m.%Y")
        else:
            time_str = "неизвестно"

        # Красивый ответ с разделителем и эмодзи
        response = (
            f"📨 <b>Данные от Mini App:</b>\n"
            f"——— 🔤 <b>Ввод:</b>\n"
            f"{input_data}\n\n"
            f"——— ✅ <b>Результат:</b>\n"
            f"{answer}\n\n"
            f"🧩 <b>Тип:</b> Расчёт резьбы\n"
            f"⏰ <b>Время:</b> {time_str}"
        )

        await message.answer(
            text=response,
            reply_markup=inline_menu.create_menu_thread(),
            parse_mode="HTML"
        )

    except json.JSONDecodeError:
        await message.answer(
            text="❌ Ошибка: не удалось расшифровать данные из Mini App.",
            reply_markup=inline_menu.create_menu_thread()
        )

    except Exception as e:
        await message.answer(
            text=f"⚠️ Произошла ошибка: <code>{str(e)}</code>",
            reply_markup=inline_menu.create_menu_thread(),
            parse_mode="HTML"
        )