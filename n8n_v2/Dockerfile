FROM n8nio/runners:latest

# Устанавливаем pip через ensurepip, затем обновляем его и ставим пакеты
RUN /opt/runners/task-runner-python/.venv/bin/python -m ensurepip --upgrade && \
    /opt/runners/task-runner-python/.venv/bin/python -m pip install --upgrade pip && \
    /opt/runners/task-runner-python/.venv/bin/python -m pip install requests pandas numpy