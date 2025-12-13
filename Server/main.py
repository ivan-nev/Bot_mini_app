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


# Обновленный маршрут для отображения калькулятора
@app.get("/metric-calc")
async def metric_calc(request: Request):
    return templates.TemplateResponse("metric-calc.html", {"request": request})


# --- НОВЫЙ ЭНДПОИНТ ДЛЯ ПРИЕМА POST ЗАПРОСОВ ИЗ MINI APP ---
@app.post("/api/submit-data")
async def submit_metric_data(data: WebAppData):
    # 1. Валидация данных от Telegram Mini App
    if not validate_telegram_init_data(data.initData, TELEGRAM_BOT_TOKEN):
        raise HTTPException(status_code=403, detail="Invalid Telegram Init Data Signature")

    # 2. Данные валидны. Извлекаем user_id из initData (для примера)
    user_data_str = urllib.parse.parse_qsl(data.initData)
    user_id = None
    for key, value in user_data_str:
        if key == 'user':
            user_info = json.loads(value)
            user_id = user_info.get('id')
            break

    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found in init data")

    # 3. Обработка данных (например, сохранение в БД)
    result_value = data.value
    print(f"Получены валидные данные от пользователя {user_id}: {result_value}")

    # 4. Отправка ответного сообщения боту через Bot API
    # Ваш сервер делает HTTPS POST запрос к API Telegram
    send_text = f"Я получил данные от Mini App:\nValue: {result_value}"

    telegram_api_url = f"api.telegram.org{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': user_id,
        'text': send_text
    }

    # Отправляем запрос в Telegram (асинхронно или синхронно, FastAPI позволяет)
    requests.post(telegram_api_url, json=payload)

    return {"status": "success", "message": "Data received and bot notified"}
