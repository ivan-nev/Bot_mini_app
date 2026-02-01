FROM docker.n8n.io/n8nio/n8n

USER root

# Установка Python 3 и pip для Debian-based образа
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Опционально: установка дополнительных Python библиотек
# RUN pip3 install requests beautifulsoup4 pandas