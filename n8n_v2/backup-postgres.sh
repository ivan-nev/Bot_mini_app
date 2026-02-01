#!/bin/bash
# PostgreSQL Backup Script for n8n
# Runs daily, keeps 7 days of backups

BACKUP_DIR="/root/n8n-server/compose/backups"
CONTAINER="n8n-compose-postgres-1"
DB_USER="n8n"
DB_NAME="n8n"
DATE=$(date +%Y-%m-%d_%H%M)
RETENTION_DAYS=7

# Create backup
echo "[$(date)] Starting backup..."
docker exec $CONTAINER pg_dump -U $DB_USER $DB_NAME | gzip > "$BACKUP_DIR/n8n_backup_$DATE.sql.gz"

if [ $? -eq 0 ]; then
    echo "[$(date)] Backup completed: n8n_backup_$DATE.sql.gz"
    echo "[$(date)] Size: $(ls -lh $BACKUP_DIR/n8n_backup_$DATE.sql.gz | awk '{print $5}')"
else
    echo "[$(date)] ERROR: Backup failed!"
    exit 1
fi

# Delete backups older than retention period
echo "[$(date)] Cleaning up backups older than $RETENTION_DAYS days..."
find $BACKUP_DIR -name "n8n_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "[$(date)] Current backups:"
ls -lh $BACKUP_DIR/*.sql.gz 2>/dev/null || echo "No backups found"
