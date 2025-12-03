import json
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from Bot.keybords import inline_menu

router = Router()


@router.message(CommandStart())
async def start(message: Message):
    await message.answer(text="расчёт резьб", reply_markup=inline_menu.create_menu_thread())


@router.message(F.content_type == "web_app_data")
async def web_app_handler(message: Message):
    """Основной обработчик Web App данных"""
    # Получаем и парсим данные
    data = json.loads(message.web_app_data.data)
    print(data)


@router.message(F.content_type != "web_app_data")
async def web_app_handler(message: Message):
    """Основной обработчик Web App данных"""
    try:
        # Получаем и парсим данные
        data = json.loads(message.web_app_data.data)

        # Обрабатываем данные
        response = await process_web_app_data(data)

        # Отправляем ответ
        await message.answer(response, parse_mode="HTML")

    except json.JSONDecodeError:
        await message.answer("❌ Ошибка: некорректные данные от Web App")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


async def process_web_app_data(data: dict) -> str:
    """Обрабатывает данные из Web App и возвращает форматированный ответ"""
    # Определяем тип резьбы
    thread_type = determine_thread_type(data)

    # Собираем ответ
    response_parts = []

    # Заголовок
    response_parts.append(get_thread_header(thread_type))

    # Входные параметры
    response_parts.append(format_input_params(data, thread_type))

    # Результаты
    response_parts.append(format_results(data))

    # Таймстамп
    if "timestamp" in data:
        response_parts.append(format_timestamp(data["timestamp"]))

    return "\n".join(response_parts)


def determine_thread_type(data: dict) -> str:
    """Определяет тип резьбы"""
    if data.get("action") == "share_metric_result":
        return "metric"
    elif data.get("action") == "share_stub_acme_result":
        return "stub_acme"
    # Альтернативные проверки
    elif "internalTolerance" in data and "externalTolerance" in data:
        return "metric"
    elif "tolerance" in data and data["tolerance"] in ["2G", "4G"]:
        return "stub_acme"
    return "unknown"


def get_thread_header(thread_type: str) -> str:
    """Возвращает заголовок для типа резьбы"""
    headers = {
        "metric": "🔩 <b>Результаты расчета метрической резьбы</b>",
        "stub_acme": "⚙️ <b>Результаты расчета резьбы Stub ACME</b>",
        "unknown": "🔧 <b>Результаты расчета резьбы</b>"
    }
    return headers.get(thread_type, headers["unknown"])


def format_input_params(data: dict, thread_type: str) -> str:
    """Форматирует входные параметры"""
    parts = ["<b>Входные параметры:</b>"]

    # Диаметр
    if "diameter" in data:
        unit = "мм" if thread_type == "metric" else "дюймов"
        parts.append(f"• Диаметр: <code>{data['diameter']} {unit}</code>")

    # Шаг
    if "pitch" in data:
        unit = "мм" if thread_type == "metric" else "ниток/дюйм"
        parts.append(f"• Шаг: <code>{data['pitch']} {unit}</code>")

    # Допуски для метрической
    if thread_type == "metric":
        if "internalTolerance" in data:
            parts.append(f"• Допуск муфты: <code>{data['internalTolerance']}</code>")
        if "externalTolerance" in data:
            parts.append(f"• Допуск ниппеля: <code>{data['externalTolerance']}</code>")

    # Допуски для Stub ACME
    elif thread_type == "stub_acme" and "tolerance" in data:
        tolerance_names = {"2G": "2G (Стандартный)", "4G": "4G (Точный)"}
        tolerance = tolerance_names.get(data["tolerance"], data["tolerance"])
        parts.append(f"• Класс допуска: <code>{tolerance}</code>")

    return "\n".join(parts)


def format_results(data: dict) -> str:
    """Форматирует результаты расчета"""
    results = data.get("results", "")

    if isinstance(results, str):
        return f"\n<b>Результаты:</b>\n<pre>{results}</pre>"

    elif isinstance(results, list):
        formatted = ["<b>Результаты:</b>"]
        for item in results:
            param = item.get("parameter", "Параметр")
            formatted.append(f"• <b>{param}:</b>")

            # Метрическая резьба
            if "nut" in item and "bolt" in item:
                nut_val = item["nut"].get("value", "")
                bolt_val = item["bolt"].get("value", "")
                nut_dev = format_deviations(item["nut"].get("deviations", []))
                bolt_dev = format_deviations(item["bolt"].get("deviations", []))
                formatted.append(f"  Муфта: {nut_val}{nut_dev}")
                formatted.append(f"  Ниппель: {bolt_val}{bolt_dev}")

            # Stub ACME
            elif "nipple" in item and "coupling" in item:
                nipple_val = item["nipple"].get("value", "")
                coupling_val = item["coupling"].get("value", "")
                nipple_dev = format_deviations(item["nipple"].get("deviations", []))
                coupling_dev = format_deviations(item["coupling"].get("deviations", []))
                formatted.append(f"  Ниппель: {nipple_val}{nipple_dev}")
                formatted.append(f"  Муфта: {coupling_val}{coupling_dev}")

            formatted.append("")

        return "\n".join(formatted).strip()

    else:
        return f"\n<b>Результаты:</b>\n<pre>{str(results)}</pre>"


def format_deviations(deviations: list) -> str:
    """Форматирует отклонения"""
    if not deviations:
        return ""
    return f" ({', '.join(deviations)})"


def format_timestamp(timestamp: str) -> str:
    """Форматирует временную метку"""
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return f"\n\n⏱️ <i>Расчет выполнен: {dt.strftime('%d.%m.%Y %H:%M')}</i>"
    except:
        return ""