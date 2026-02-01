# n8n Production Docker Compose

Production-ready n8n deployment with PostgreSQL, Redis queue, Traefik reverse proxy, and **Python + JavaScript task runners**.

## Features

- **n8n** with worker for queue-based execution
- **Python Code Node** support via external task runners
- **PostgreSQL 16** for persistent storage
- **Redis 7** for queue management
- **Traefik v3** reverse proxy with automatic SSL (Cloudflare DNS)
- Automatic HTTPS redirect
- Health checks on all services
- Execution data pruning

## Architecture

```
                    ┌─────────────┐
                    │   Traefik   │ :80/:443
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
        ┌─────▼─────┐            ┌──────▼──────┐
        │    n8n    │◄──────────►│  n8n-worker │
        │  (main)   │            │   (queue)   │
        └─────┬─────┘            └──────┬──────┘
              │                         │
        ┌─────▼─────┐            ┌──────▼──────┐
        │n8n-runners│            │worker-runners│
        │ (JS + Py) │            │  (JS + Py)  │
        └───────────┘            └─────────────┘
              │                         │
              └────────────┬────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
        ┌─────▼─────┐            ┌──────▼──────┐
        │ PostgreSQL│            │    Redis    │
        └───────────┘            └─────────────┘
```

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/AllDayAutomationsai/n8n-docker-compose.git
cd n8n-docker-compose
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your values:

```bash
# Generate encryption key
openssl rand -base64 32

# Generate runners auth token
openssl rand -hex 32
```

### 3. Start the stack

```bash
docker compose up -d
```

### 4. Check status

```bash
docker compose ps
docker logs n8n-compose-n8n-1
```

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `N8N_HOST` | Your n8n domain (e.g., `n8n.example.com`) |
| `LETS_ENCRYPT_EMAIL` | Email for SSL certificate |
| `CLOUDFLARE_API_TOKEN` | Cloudflare API token for DNS challenge |
| `N8N_ENCRYPTION_KEY` | Encryption key for credentials |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `REDIS_PASSWORD` | Redis password |
| `N8N_RUNNERS_AUTH_TOKEN` | Shared token between n8n and runners |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `TZ` | `America/New_York` | Timezone |
| `POSTGRES_USER` | `n8n` | PostgreSQL username |
| `POSTGRES_DB` | `n8n` | PostgreSQL database name |
| `N8N_RUNNERS_ENABLED` | `true` | Enable task runners |
| `COMPOSE_PROJECT_NAME` | `n8n-compose` | Docker Compose project name |

## Task Runners (Python Support)

This setup uses **external mode** for task runners, which is the recommended production configuration.

### How it works

1. n8n runs a **Task Broker** on port 5679
2. The `n8nio/runners` container connects to the broker
3. When a Code node executes, the runner processes it in isolation
4. Both JavaScript and Python are supported

### Key configuration

```yaml
# On n8n container
N8N_RUNNERS_MODE: external
N8N_RUNNERS_BROKER_LISTEN_ADDRESS: 0.0.0.0

# On runners container
N8N_RUNNERS_TASK_BROKER_URI: http://n8n:5679
```

### Python Module Allowlist

Python imports are restricted by default. The `n8n-task-runners.json` config file defines which modules are allowed:

**Standard library allowed:**
`sys`, `os`, `json`, `re`, `math`, `datetime`, `time`, `random`, `hashlib`, `base64`, `urllib`, `collections`, `itertools`, `functools`, `decimal`, `statistics`, `uuid`, `csv`, `io`, `pathlib`, `typing`, `dataclasses`, `enum`, `copy`, `operator`, `string`

**External packages allowed:**
`requests`, `pandas`, `numpy`, `dateutil`, `pytz`

To modify the allowlist, use the management script:

```bash
# Add a stdlib module
./scripts/manage-python-modules.sh add stdlib ssl

# Add an external package
./scripts/manage-python-modules.sh add external httpx

# Remove a module
./scripts/manage-python-modules.sh remove stdlib ssl

# List all allowed modules
./scripts/manage-python-modules.sh list
```

The script automatically restarts the runner containers after changes.

**Optional: Auto-reload on file changes**

For automatic reload when the config file is edited directly:

```bash
# Install inotify-tools
apt install -y inotify-tools

# Create systemd service
cat > /etc/systemd/system/n8n-runner-watcher.service << 'EOF'
[Unit]
Description=n8n Task Runner Config Watcher
After=docker.service

[Service]
Type=simple
ExecStart=/bin/bash -c 'while true; do inotifywait -e modify,create /path/to/n8n-task-runners.json && sleep 2 && docker compose -f /path/to/docker-compose.yml restart n8n-runners n8n-worker-runners; done'
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl enable --now n8n-runner-watcher
```

### Verify runners are connected

```bash
docker logs n8n-compose-n8n-1 | grep "Registered runner"
```

Expected output:
```
Registered runner "launcher-javascript" (xxxxx)
Registered runner "launcher-python" (xxxxx)
```

## Scaling

### Add more workers

```bash
docker compose up -d --scale n8n-worker=3
```

### Add more runner instances

```bash
docker compose up -d --scale n8n-runners=2
```

## Backup

### Database backup

```bash
docker exec n8n-compose-postgres-1 pg_dump -U n8n n8n > backup.sql
```

### Restore

```bash
cat backup.sql | docker exec -i n8n-compose-postgres-1 psql -U n8n n8n
```

## SSL Configuration

This setup uses Cloudflare DNS challenge for SSL certificates. To use a different provider:

1. Update Traefik command in `docker-compose.yml`
2. Change the environment variables for your DNS provider

See [Traefik ACME documentation](https://doc.traefik.io/traefik/https/acme/) for other providers.

## Troubleshooting

### Task runners not connecting

1. Check broker is listening on all interfaces:
   ```bash
   docker logs n8n-compose-n8n-1 | grep "Task Broker"
   # Should show: n8n Task Broker ready on 0.0.0.0, port 5679
   ```

2. Check runner logs:
   ```bash
   docker logs n8n-compose-n8n-runners-1
   ```

3. Verify auth tokens match in both containers

### Python code node fails

1. Ensure runners are registered (see above)
2. Check runner container has Python available:
   ```bash
   docker exec n8n-compose-n8n-runners-1 python3 --version
   ```

### Database connection issues

```bash
docker exec n8n-compose-postgres-1 pg_isready -U n8n -d n8n
```

## Resources

- [n8n Documentation](https://docs.n8n.io/)
- [n8n Task Runners](https://docs.n8n.io/hosting/configuration/task-runners/)
- [n8nio/runners Docker Hub](https://hub.docker.com/r/n8nio/runners)
- [Traefik Documentation](https://doc.traefik.io/traefik/)

## License

MIT
