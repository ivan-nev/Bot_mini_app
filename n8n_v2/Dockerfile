FROM n8nio/runners:latest

# Переходим на пользователя node (владелец .venv)
USER node

# Устанавливаем pip (если отсутствует) и нужные пакеты
RUN /opt/runners/task-runner-python/.venv/bin/python -m ensurepip --upgrade && \
    /opt/runners/task-runner-python/.venv/bin/python -m pip install --upgrade pip && \
    /opt/runners/task-runner-python/.venv/bin/python -m pip install requests pandas numpy

# При необходимости можно вернуться к root, но обычно раннер запускается от node,
# так что оставляем пользователя node.