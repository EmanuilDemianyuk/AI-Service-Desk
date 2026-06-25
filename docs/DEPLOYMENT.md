# Deployment Guide

This document provides instructions for deploying the HelpDesk Bot to production.

## Pre-Deployment Checklist

- [ ] `.env` file configured with production values
- [ ] `DEBUG=false` in `.env`
- [ ] `ENVIRONMENT=production` in `.env`
- [ ] Strong `POSTGRES_PASSWORD` set
- [ ] Valid `BOT_TOKEN` from @BotFather
- [ ] Valid `SUPERADMIN_TELEGRAM_ID` set
- [ ] Valid `OPENROUTER_API_KEY` from OpenRouter
- [ ] Notion integration configured (optional)
- [ ] Database backups configured
- [ ] Monitoring and logging setup
- [ ] Firewall configured (ports 22, 80, 443; 5432 only if remote DB)

## Docker Compose (Recommended)

The `docker-compose.yml` defines three services: `postgres`, `api`, `bot`.

### 1. Prepare environment

```bash
cp .env.example .env
# Edit .env with production values
nano .env
```

### 2. Run migrations

```bash
docker-compose run --rm api alembic upgrade head
```

### 3. Start services

```bash
# Build images
docker-compose build

# Start all services in background
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api
docker-compose logs -f bot
```

### 4. Post-deployment verification

```bash
# Health check
curl http://localhost:8000/health

# Check for errors
docker-compose logs api | grep -i error
docker-compose logs bot | grep -i error
```

### Container names

| Service | Container name | Purpose |
|---|---|---|
| postgres | `helpdesk_postgres` | PostgreSQL database |
| api | `helpdesk_api` | FastAPI REST server |
| bot | `helpdesk_bot_service` | aiogram polling process |

---

## Manual Server Deployment

### 1. Server setup

```bash
# Install system dependencies
sudo apt update
sudo apt install -y python3.12 python3.12-venv postgresql postgresql-contrib nginx
```

### 2. Clone and setup

```bash
git clone <repository-url> helpdesk-bot
cd helpdesk-bot

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure database

```bash
sudo -u postgres psql << EOF
CREATE USER helpdesk_user WITH PASSWORD 'your_secure_password';
CREATE DATABASE helpdesk OWNER helpdesk_user;
GRANT ALL PRIVILEGES ON DATABASE helpdesk TO helpdesk_user;
EOF

# Run migrations
alembic upgrade head
```

### 4. Setup environment

```bash
cp .env.example .env
nano .env  # Edit with production values
```

### 5. Setup systemd services

Create `/etc/systemd/system/helpdesk-api.service`:

```ini
[Unit]
Description=HelpDesk Bot API Service
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
WorkingDirectory=/home/user/helpdesk-bot
Environment="PATH=/home/user/helpdesk-bot/venv/bin"
EnvironmentFile=/home/user/helpdesk-bot/.env
ExecStart=/home/user/helpdesk-bot/venv/bin/uvicorn \
    app.main:app \
    --host 127.0.0.1 \
    --port 8000

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/helpdesk-bot.service`:

```ini
[Unit]
Description=HelpDesk Telegram Bot Service
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/home/user/helpdesk-bot
Environment="PATH=/home/user/helpdesk-bot/venv/bin"
EnvironmentFile=/home/user/helpdesk-bot/.env
ExecStart=/home/user/helpdesk-bot/venv/bin/python app/bot_runner.py
StandardOutput=journal
StandardError=journal

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 6. Start services

```bash
sudo systemctl daemon-reload
sudo systemctl start helpdesk-api helpdesk-bot
sudo systemctl enable helpdesk-api helpdesk-bot

# Check status
sudo systemctl status helpdesk-api
sudo systemctl status helpdesk-bot
```

### 7. Configure Nginx

Create `/etc/nginx/sites-available/helpdesk`:

```nginx
upstream helpdesk_api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    access_log /var/log/nginx/helpdesk-access.log;
    error_log /var/log/nginx/helpdesk-error.log;

    location / {
        proxy_pass http://helpdesk_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/helpdesk /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

SSL certificate:

```bash
sudo certbot certonly --standalone -d your-domain.com
```

---

## Database Migrations

```bash
# Apply pending migrations
alembic upgrade head

# Roll back one step
alembic downgrade -1

# In Docker
docker-compose run --rm api alembic upgrade head
```

---

## Database Backup

Create `/usr/local/bin/backup-helpdesk-db.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backups/helpdesk"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/helpdesk_$TIMESTAMP.sql.gz"
mkdir -p $BACKUP_DIR

PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
    -h $POSTGRES_HOST \
    -U $POSTGRES_USER \
    -d $POSTGRES_DB | gzip > $BACKUP_FILE

# Keep last 7 days
find $BACKUP_DIR -name "helpdesk_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE"
```

Add to crontab (daily at 2 AM):

```bash
0 2 * * * /usr/local/bin/backup-helpdesk-db.sh >> /var/log/helpdesk-backup.log 2>&1
```

---

## Monitoring and Logging

### Logs

```bash
# Docker
docker-compose logs -f api
docker-compose logs -f bot

# Systemd
sudo journalctl -u helpdesk-api -f
sudo journalctl -u helpdesk-bot -f

# Files (when running locally)
tail -f logs/app.log
tail -f logs/error.log
```

### Health check

```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","message":"Service is running"}
```

---

## Scaling Considerations

- **FSM state** is stored in memory (`MemoryStorage`). For multi-instance deployments or restartable bots, switch to Redis storage.
- **Bot polling** cannot run in multiple instances simultaneously; only one `bot_runner.py` process should run.
- **API** is stateless and can be scaled horizontally behind a load balancer.

---

## Rollback

```bash
# Identify version to roll back to
docker-compose images

# Update docker-compose.yml to previous image, then:
docker-compose down
docker-compose up -d

# Roll back database if schema changed
alembic downgrade -1
```

---

## Troubleshooting

### Bot not responding

```bash
# Check bot token
curl https://api.telegram.org/bot$BOT_TOKEN/getMe

# Check logs
docker-compose logs -f bot
```

### Database errors

```bash
# Check active connections
psql -h localhost -U helpdesk_user -d helpdesk \
  -c "SELECT datname, usename, count(*) FROM pg_stat_activity GROUP BY datname, usename;"
```

### API not reachable

```bash
docker-compose ps          # Check container status
docker-compose logs api    # Check for startup errors
curl http://localhost:8000/health
```

---

## Post-Deployment Checklist

- [ ] Health check passes: `curl http://localhost:8000/health`
- [ ] Bot responds to `/start`
- [ ] Task creation works end-to-end
- [ ] Notion sync works (if configured): `curl -X POST http://localhost:8000/api/notion/sync`
- [ ] Logs are clean (no ERROR entries)
- [ ] SSL/TLS working (if using HTTPS)
- [ ] Database backups running
