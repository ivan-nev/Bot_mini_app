FROM python:3.12-slim

WORKDIR /Server

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование приложения
COPY . .

# Создание непривилегированного пользователя
RUN useradd -m -u 1000 fastapi_user && chown -R fastapi_user:fastapi_user /Server
USER fastapi_user
ENV TZ=Asia/Yekaterinburg
# Запуск приложения
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
