FROM node:18-alpine

USER root

# Установка Python и pip
RUN apk add --no-cache python3 py3-pip

# Установка n8n глобально
RUN npm install -g n8n

# Создание пользователя node (если не существует)
RUN addgroup -g 1000 node || true && \
    adduser -D -u 1000 -G node node || true

USER node

WORKDIR /home/node

# Expose порт n8n
EXPOSE 5678

# Команда запуска n8n
CMD ["n8n"]