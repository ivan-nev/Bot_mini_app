#!/bin/bash

# Директория для бэкапов
BACKUP_DIR="/backups"
# База данных (берется из переменной окружения или используется значение по умолчанию)
DB_NAME="${DB_NAME:-vikunja}"
# Максимальное количество бэкапов
MAX_BACKUPS="${MAX_BACKUPS:-7}"
# Интервал между бэкапами (по умолчанию 24 часа)
BACKUP_INTERVAL="${BACKUP_INTERVAL:-86400}"

# Создаем директорию для бэкапов, если её нет
mkdir -p "$BACKUP_DIR"

# Функция очистки старых бэкапов
cleanup_backups() {
    echo "Очистка старых бэкапов (оставляем не более $MAX_BACKUPS)..."
    cd "$BACKUP_DIR" || exit 1
    ls -tp *.sql.gz 2>/dev/null | grep -v '/$' | tail -n +$((MAX_BACKUPS + 1)) | while read old_file; do
        echo "Удаление старого бэкапа: $old_file"
        rm -f "$old_file"
    done
    echo "Очистка завершена"
}

# Функция создания бэкапа
create_backup() {
    # Формируем имя файла с датой и временем
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_FILE="$BACKUP_DIR/vikunja_backup_${TIMESTAMP}.sql.gz"

    echo "Создание бэкапа базы данных в $BACKUP_FILE..."

    # Проверяем доступность базы данных
    echo "Проверка подключения к БД..."

    # Проверяем, существует ли указанная база данных
    echo "Проверка наличия базы данных '$DB_NAME'..."
    DB_EXISTS=$(mysql -h db -u root -p"${MYSQL_ROOT_PASSWORD}" -e "SHOW DATABASES LIKE '$DB_NAME';" 2>/dev/null | grep -c "$DB_NAME" || echo "0")

    if [ "$DB_EXISTS" -eq 0 ]; then
        echo "✗ База данных '$DB_NAME' не найдена!"
        echo "Доступные базы данных:"
        mysql -h db -u root -p"${MYSQL_ROOT_PASSWORD}" -e "SHOW DATABASES;" 2>/dev/null
        return 1
    fi
    echo "✓ База данных '$DB_NAME' найдена"

    # Проверяем количество таблиц в базе данных
    TABLE_COUNT=$(mysql -h db -u root -p"${MYSQL_ROOT_PASSWORD}" -D "$DB_NAME" -e "SHOW TABLES;" 2>/dev/null | wc -l)
    echo "Количество таблиц в базе '$DB_NAME': $((TABLE_COUNT - 1))"  # Вычитаем заголовок

    if [ "$TABLE_COUNT" -le 1 ]; then
        echo "⚠ ВНИМАНИЕ: В базе данных '$DB_NAME' нет таблиц!"
    fi

    # Выполняем бэкап конкретной базы данных
    echo "Выполнение дампа базы данных '$DB_NAME'..."
    if mysqldump -h db -u root -p"${MYSQL_ROOT_PASSWORD}" --databases "$DB_NAME" --single-transaction --routines --triggers --events 2>/tmp/mysqldump_error.log | gzip > "$BACKUP_FILE"; then
        if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
            SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
            # Проверяем, что файл содержит данные, а не только заголовок
            if gunzip -c "$BACKUP_FILE" 2>/dev/null | grep -q "CREATE TABLE\|INSERT INTO"; then
                echo "✓ Бэкап успешно создан: $BACKUP_FILE"
                echo "Размер бэкапа: $SIZE"
                echo "✓ Бэкап содержит данные"
                return 0
            else
                echo "⚠ Бэкап создан, но не содержит данных (размер: $SIZE)"
                echo "Возможные причины:"
                echo "  - В базе данных нет таблиц"
                echo "  - В таблицах нет данных"
                echo "  - Неправильное имя базы данных"
                return 1
            fi
        else
            echo "✗ ОШИБКА: Файл бэкапа пуст или не создан!"
            cat /tmp/mysqldump_error.log 2>/dev/null
            rm -f "$BACKUP_FILE"
            return 1
        fi
    else
        echo "✗ ОШИБКА: Не удалось создать бэкап!"
        cat /tmp/mysqldump_error.log 2>/dev/null
        rm -f "$BACKUP_FILE"
        return 1
    fi
}

# Функция показа текущих бэкапов
show_backups() {
    echo "Текущие бэкапы:"
    ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' || echo "  (нет бэкапов)"
}

# Функция для вычисления следующего времени
get_next_backup_time() {
    local interval=$1
    local current_time=$(date +%s)
    local next_time=$((current_time + interval))
    date -d "@$next_time" "+%Y-%m-%d %H:%M:%S UTC" 2>/dev/null || date -r "$next_time" "+%Y-%m-%d %H:%M:%S UTC" 2>/dev/null || echo "через ${interval} секунд"
}

# Функция для форматирования интервала
format_interval() {
    local seconds=$1
    local hours=$((seconds / 3600))
    local minutes=$(((seconds % 3600) / 60))
    local secs=$((seconds % 60))

    if [ $hours -gt 0 ]; then
        echo "${hours} ч ${minutes} мин ${secs} сек"
    elif [ $minutes -gt 0 ]; then
        echo "${minutes} мин ${secs} сек"
    else
        echo "${secs} сек"
    fi
}

# Основной цикл
echo "========================================="
echo "Сервис автоматического бэкапа Vikunja DB"
echo "========================================="
echo "База данных: $DB_NAME"
echo "Интервал бэкапов: $(format_interval $BACKUP_INTERVAL)"
echo "Максимум бэкапов: $MAX_BACKUPS"
echo "Директория бэкапов: $BACKUP_DIR"
echo "========================================="
echo "Ожидание 10 секунд перед первым бэкапом..."
sleep 10

while true; do
    echo "========================================="
    echo "НАЧАЛО БЭКАПА: $(date '+%Y-%m-%d %H:%M:%S %Z')"
    echo "========================================="

    # Создаем бэкап
    if create_backup; then
        # Очищаем старые бэкапы
        cleanup_backups
    else
        echo "✗ Бэкап не создан, очистка пропущена"
    fi

    echo "-----------------------------------------"
    show_backups
    echo "========================================="
    echo "БЭКАП ЗАВЕРШЕН: $(date '+%Y-%m-%d %H:%M:%S %Z')"

    # Вычисляем и показываем время следующего бэкапа
    NEXT_TIME=$(get_next_backup_time $BACKUP_INTERVAL)
    echo "Следующий бэкап через: $(format_interval $BACKUP_INTERVAL)"
    echo "Следующий бэкап будет в: $NEXT_TIME"
    echo "========================================="

    # Ждем указанный интервал
    sleep "$BACKUP_INTERVAL"
done