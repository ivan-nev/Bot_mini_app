FROM docker.n8n.io/n8nio/n8n:latest

# Переключаемся на root для установки пакетов
USER root

# Устанавливаем Python и необходимые пакеты
RUN apt-get update && \
    apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем популярные Python библиотеки (опционально)
#RUN pip3 install --no-cache-dir \
#    pandas \
#    requests \
#    beautifulsoup4 \
#    lxml

# Возвращаемся к пользователю node
USER node

# Проверяем установку
RUN python3 --version