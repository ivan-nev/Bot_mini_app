#!/bin/bash
# Python Module Manager for n8n Task Runners
# Usage:
#   ./manage-python-modules.sh add stdlib <module>
#   ./manage-python-modules.sh add external <module>
#   ./manage-python-modules.sh remove stdlib <module>
#   ./manage-python-modules.sh remove external <module>
#   ./manage-python-modules.sh list
#   ./manage-python-modules.sh reload
#   ./manage-python-modules.sh backup

set -e

CONFIG_FILE="/root/n8n-server/compose/n8n-task-runners.json"
COMPOSE_DIR="/root/n8n-server/compose"
BACKUP_DIR="/root/n8n-server/compose/backups"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

backup_config() {
    mkdir -p "$BACKUP_DIR"
    local backup_file="$BACKUP_DIR/n8n-task-runners.$(date +%Y%m%d_%H%M%S).json"
    cp "$CONFIG_FILE" "$backup_file"
    # Keep only last 10 backups
    ls -t "$BACKUP_DIR"/*.json 2>/dev/null | tail -n +11 | xargs -r rm
    echo -e "${GREEN}Backup saved: $backup_file${NC}"
}

reload_runners() {
    echo -e "${YELLOW}Reloading runner containers...${NC}"
    cd "$COMPOSE_DIR"
    docker compose restart n8n-runners n8n-worker-runners 2>/dev/null || \
    docker-compose restart n8n-runners n8n-worker-runners
    echo -e "${GREEN}Runners reloaded successfully${NC}"
}

list_modules() {
    echo -e "${GREEN}Current Python Module Allowlist:${NC}"
    echo ""
    echo "Standard Library:"
    jq -r '.["task-runners"][] | select(.["runner-type"]=="python") | .["env-overrides"]["N8N_RUNNERS_STDLIB_ALLOW"]' "$CONFIG_FILE" | tr ',' '\n' | sed 's/^/  - /'
    echo ""
    echo "External Packages:"
    jq -r '.["task-runners"][] | select(.["runner-type"]=="python") | .["env-overrides"]["N8N_RUNNERS_EXTERNAL_ALLOW"]' "$CONFIG_FILE" | tr ',' '\n' | sed 's/^/  - /'
}

add_module() {
    local type=$1
    local module=$2
    local key=""

    if [ "$type" == "stdlib" ]; then
        key="N8N_RUNNERS_STDLIB_ALLOW"
    elif [ "$type" == "external" ]; then
        key="N8N_RUNNERS_EXTERNAL_ALLOW"
    else
        echo "Invalid type: $type (use 'stdlib' or 'external')"
        exit 1
    fi

    # Get current modules
    current=$(jq -r ".\"task-runners\"[] | select(.\"runner-type\"==\"python\") | .\"env-overrides\".\"$key\"" "$CONFIG_FILE")

    # Check if already exists
    if echo "$current" | tr ',' '\n' | grep -q "^${module}$"; then
        echo "Module '$module' already exists in $type allowlist"
        return
    fi

    # Backup before change
    backup_config

    # Add module
    if [ -z "$current" ]; then
        new_value="$module"
    else
        new_value="${current},${module}"
    fi

    # Update config
    jq "(.\"task-runners\"[] | select(.\"runner-type\"==\"python\") | .\"env-overrides\".\"$key\") = \"$new_value\"" "$CONFIG_FILE" > "${CONFIG_FILE}.tmp"
    mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"

    echo -e "${GREEN}Added '$module' to $type allowlist${NC}"
    reload_runners
}

remove_module() {
    local type=$1
    local module=$2
    local key=""

    if [ "$type" == "stdlib" ]; then
        key="N8N_RUNNERS_STDLIB_ALLOW"
    elif [ "$type" == "external" ]; then
        key="N8N_RUNNERS_EXTERNAL_ALLOW"
    else
        echo "Invalid type: $type (use 'stdlib' or 'external')"
        exit 1
    fi

    # Backup before change
    backup_config

    # Get current modules and remove the specified one
    current=$(jq -r ".\"task-runners\"[] | select(.\"runner-type\"==\"python\") | .\"env-overrides\".\"$key\"" "$CONFIG_FILE")
    new_value=$(echo "$current" | tr ',' '\n' | grep -v "^${module}$" | tr '\n' ',' | sed 's/,$//')

    # Update config
    jq "(.\"task-runners\"[] | select(.\"runner-type\"==\"python\") | .\"env-overrides\".\"$key\") = \"$new_value\"" "$CONFIG_FILE" > "${CONFIG_FILE}.tmp"
    mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"

    echo -e "${GREEN}Removed '$module' from $type allowlist${NC}"
    reload_runners
}

case "$1" in
    add)
        add_module "$2" "$3"
        ;;
    remove)
        remove_module "$2" "$3"
        ;;
    list)
        list_modules
        ;;
    reload)
        reload_runners
        ;;
    backup)
        backup_config
        ;;
    *)
        echo "Usage: $0 {add|remove|list|reload|backup}"
        echo ""
        echo "Commands:"
        echo "  add stdlib <module>      Add a stdlib module"
        echo "  add external <module>    Add an external package"
        echo "  remove stdlib <module>   Remove a stdlib module"
        echo "  remove external <module> Remove an external package"
        echo "  list                     List all allowed modules"
        echo "  reload                   Reload runner containers"
        echo "  backup                   Create a backup of current config"
        exit 1
        ;;
esac
