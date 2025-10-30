FROM python:3.12-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование приложения
COPY . ./Server

# Создание непривилегированного пользователя
RUN useradd -m -u 1000 fastapi_user && chown -R fastapi_user:fastapi_user /app
USER fastapi_user

# Запуск приложения
CMD ["uvicorn", "Server.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]