import hmac
import hashlib
import json
import urllib.parse
import os
from environs import Env
import requests  # Нужен для отправки запроса обратно в Telegram Bot API
from fastapi import FastAPI, Request, HTTPException, Body
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime

env = Env()
env.read_env()

TELEGRAM_BOT_TOKEN = env('BOT_TOKEN')

app = FastAPI()
templates = Jinja2Templates(directory='Server/templates')


# Pydantic модель для входящего POST запроса из Mini App
class WebAppData(BaseModel):
    value: str
    initData: str


# Функция валидации initData (взята из документации Telegram)
def validate_telegram_init_data(init_data: str, bot_token: str) -> bool:
    """Validate the init data received from the Telegram Mini App."""
    parsed_data = urllib.parse.parse_qsl(init_data)
    data_check_string = []
    signature = ""

    for key, value in parsed_data:
        if key == 'hash':
            signature = value
        else:
            data_check_string.append(f"{key}={value}")

    data_check_string.sort()
    data_check_string = '\n'.join(data_check_string)

    # Key derivation
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode(),
        digestmod=hashlib.sha256
    ).digest()

    # Signature validation
    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(calculated_hash, signature)


# --- Существующие маршруты ---

@app.get("/favicon.ico", include_in_schema=False)
async def get_favicon():
    return FileResponse("Server/static/images/favicon.png")


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("test_bt.html", {"request": request})

@app.get("/test")
async def metric_calc(request: Request):
    return templates.TemplateResponse("test.html", {"request": request})


# Обновленный маршрут для отображения калькулятора
@app.get("/metric-calc")
async def metric_calc(request: Request):
    return templates.TemplateResponse("metric-calc.html", {"request": request})


# --- НОВЫЙ ЭНДПОИНТ ДЛЯ ПРИЕМА POST ЗАПРОСОВ ИЗ MINI APP ---
@app.post("/api/submit-data")
async def submit_metric_data(data: WebAppData):
    # Детальная информация о запросе для отладки
    print(f"📥 Получен запрос на /api/submit-data")
    print(f"   Значение (value): {data.value}")
    print(f"   Длина initData: {len(data.initData) if data.initData else 0}")

    # 1. Проверяем наличие initData
    if not data.initData:
        print("❌ Отсутствует initData")
        raise HTTPException(
            status_code=400,
            detail="Missing initData parameter"
        )

    # 2. Валидация данных от Telegram Mini App
    try:
        is_valid = validate_telegram_init_data(data.initData, TELEGRAM_BOT_TOKEN)
        print(f"   Проверка подписи: {'✅ ВАЛИДНО' if is_valid else '❌ НЕВАЛИДНО'}")

        if not is_valid:
            # Детальная информация о том, что не так
            print(f"   initData: {data.initData[:100]}...")
            raise HTTPException(
                status_code=403,
                detail="Invalid Telegram Init Data Signature"
            )
    except Exception as e:
        print(f"❌ Ошибка при валидации: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Validation error: {str(e)}"
        )

    # 3. Извлекаем user_id из initData
    user_data_str = urllib.parse.parse_qsl(data.initData)
    user_id = None
    user_name = "Unknown"

    for key, value in user_data_str:
        if key == 'user':
            try:
                user_info = json.loads(value)
                user_id = user_info.get('id')

                # Формируем имя пользователя
                first_name = user_info.get('first_name', '')
                last_name = user_info.get('last_name', '')
                if first_name and last_name:
                    user_name = f"{first_name} {last_name}"
                elif first_name:
                    user_name = first_name
                elif last_name:
                    user_name = last_name

                print(f"   Извлечен пользователь: {user_name} (ID: {user_id})")
            except json.JSONDecodeError as e:
                print(f"❌ Ошибка парсинга user данных: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid user data in initData: {str(e)}"
                )
            break

    if not user_id:
        print("❌ User ID не найден в initData")
        raise HTTPException(
            status_code=400,
            detail="User ID not found in init data"
        )

    # 4. Обработка данных
    result_value = data.value
    print(f"✅ Получены валидные данные от пользователя {user_name} (ID: {user_id}): {result_value}")

    # 5. Отправка ответного сообщения боту через Bot API
    send_text = f"""
✅ <b>Данные успешно получены!</b>

👤 <b>Пользователь:</b> {user_name}
🆔 <b>ID:</b> <code>{user_id}</code>
📊 <b>Значение:</b> {result_value}
⏰ <b>Время:</b> {datetime.now().strftime('%H:%M:%S')}
📡 <b>Статус:</b> Валидация пройдена успешно
"""

    telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': user_id,
        'text': send_text,
        'parse_mode': 'HTML'
    }

    bot_response_status = "not_attempted"
    bot_response_detail = ""

    try:
        print(f"   Отправка сообщения пользователю {user_id} через бота...")
        response = requests.post(telegram_api_url, json=payload, timeout=10)

        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('ok'):
                print(f"✅ Сообщение отправлено пользователю {user_id}")
                bot_response_status = "success"
            else:
                error_msg = response_data.get('description', 'Unknown error')
                print(f"⚠️ Ошибка Telegram API: {error_msg}")
                bot_response_status = "telegram_api_error"
                bot_response_detail = error_msg
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            bot_response_status = "http_error"
            bot_response_detail = f"HTTP {response.status_code}"

    except requests.exceptions.Timeout:
        print("❌ Таймаут при отправке сообщения")
        bot_response_status = "timeout"
    except requests.exceptions.ConnectionError:
        print("❌ Ошибка соединения с Telegram API")
        bot_response_status = "connection_error"
    except Exception as e:
        print(f"❌ Неизвестная ошибка: {e}")
        bot_response_status = "unknown_error"
        bot_response_detail = str(e)

    # 6. Возвращаем ответ
    response_data = {
        "status": "success",
        "message": "Data received and validated successfully",
        "validation": {
            "init_data_valid": True,
            "user_found": True
        },
        "user": {
            "id": user_id,
            "name": user_name
        },
        "data": {
            "value": result_value,
            "length": len(result_value)
        },
        "bot_notification": {
            "status": bot_response_status,
            "detail": bot_response_detail
        },
        "timestamp": datetime.now().isoformat()
    }

    print(f"📤 Отправка ответа клиенту")
    return response_data