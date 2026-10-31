docker ps -aFROM python:3.12-slim

# Не создавать .pyc и не буферизовать stdout — логи видны сразу
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SERVICE_PORT=8001

WORKDIR /appdocker ps

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Порт берётся из SERVICE_PORT (можно переопределить в docker-compose/.env)
EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import os,base64,urllib.request; port=os.environ.get('SERVICE_PORT','8001'); user=os.environ.get('AUTH_USER',''); pw=os.environ.get('AUTH_PASS',''); req=urllib.request.Request(f'http://127.0.0.1:{port}/health'); req.add_header('Authorization','Basic '+base64.b64encode(f'{user}:{pw}'.encode()).decode()); urllib.request.urlopen(req,timeout=5)" || exit 1

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${SERVICE_PORT:-8001}"]
