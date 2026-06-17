# Deployment Guide

This document provides comprehensive instructions for deploying the HelpDesk Bot to production.

## Pre-Deployment Checklist

- [ ] `.env` file configured with production values
- [ ] `DEBUG=false` in `.env`
- [ ] `ENVIRONMENT=production` in `.env`
- [ ] Strong `POSTGRES_PASSWORD` set
- [ ] Valid `BOT_TOKEN` from BotFather
- [ ] Valid `OPENROUTER_API_KEY` from OpenRouter
- [ ] Notion integration configured (optional but recommended)
- [ ] Database backups configured
- [ ] Monitoring and logging setup
- [ ] Security groups/firewall configured
- [ ] SSL/TLS certificates obtained (if using HTTPS)

## Deployment Options

### Option 1: Docker Compose (Recommended)

#### 1. Prepare Production Environment

```bash
# Clone repository
git clone <repository-url> helpdesk-bot
cd helpdesk-bot

# Setup environment
cp .env.example .env

# Edit .env with production values
nano .env
```

#### 2. Pre-deployment Tasks

```bash
# Run database migrations
docker-compose run app alembic upgrade head

# Verify database connection
docker-compose run app python -c "from app.database.base import engine; print('DB OK')"
```

#### 3. Deploy

```bash
# Build images
docker-compose build

# Start services in background
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f app
```

#### 4. Post-deployment Verification

```bash
# Health check
curl http://localhost:8000/health

# Check logs for errors
docker-compose logs app | grep -i error
```

---

### Option 2: Kubernetes Deployment

#### 1. Create Docker Image

```bash
docker build -t helpdesk-bot:latest .
docker tag helpdesk-bot:latest your-registry/helpdesk-bot:latest
docker push your-registry/helpdesk-bot:latest
```

#### 2. Create Kubernetes Secrets

```bash
kubectl create namespace helpdesk

kubectl create secret generic helpdesk-secrets \
  --from-literal=bot-token=YOUR_BOT_TOKEN \
  --from-literal=openrouter-key=YOUR_API_KEY \
  --from-literal=notion-token=YOUR_NOTION_TOKEN \
  --from-literal=postgres-password=YOUR_DB_PASSWORD \
  -n helpdesk
```

#### 3. Create ConfigMap

```bash
kubectl create configmap helpdesk-config \
  --from-literal=ENVIRONMENT=production \
  --from-literal=DEBUG=false \
  --from-literal=POSTGRES_HOST=postgres \
  --from-literal=POSTGRES_DB=helpdesk \
  -n helpdesk
```

#### 4. Deploy Services

See `k8s/` directory for Kubernetes manifests.

---

### Option 3: Manual Server Deployment

#### 1. Server Setup

```bash
# SSH into server
ssh user@your-server.com

# Install system dependencies
sudo apt update
sudo apt install -y python3.13 python3.13-venv postgresql postgresql-contrib nginx
```

#### 2. Clone and Setup

```bash
# Clone repository
git clone <repository-url> helpdesk-bot
cd helpdesk-bot

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 3. Configure Database

```bash
# Create PostgreSQL user and database
sudo -u postgres psql << EOF
CREATE USER helpdesk_user WITH PASSWORD 'your_secure_password';
CREATE DATABASE helpdesk OWNER helpdesk_user;
GRANT ALL PRIVILEGES ON DATABASE helpdesk TO helpdesk_user;
EOF

# Run migrations
alembic upgrade head
```

#### 4. Setup Environment

```bash
# Copy and configure .env
cp .env.example .env
nano .env  # Edit with production values
```

#### 5. Setup Systemd Services

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
ExecStart=/home/user/helpdesk-bot/venv/bin/gunicorn \
    app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/helpdesk/api-access.log \
    --error-logfile /var/log/helpdesk/api-error.log

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

#### 6. Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Start services
sudo systemctl start helpdesk-api
sudo systemctl start helpdesk-bot

# Enable on startup
sudo systemctl enable helpdesk-api
sudo systemctl enable helpdesk-bot

# Check status
sudo systemctl status helpdesk-api
sudo systemctl status helpdesk-bot
```

#### 7. Configure Nginx

Create `/etc/nginx/sites-available/helpdesk`:

```nginx
upstream helpdesk_api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    # Logging
    access_log /var/log/nginx/helpdesk-access.log;
    error_log /var/log/nginx/helpdesk-error.log;

    # Proxy configuration
    location / {
        proxy_pass http://helpdesk_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/helpdesk /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Database Backup Strategy

### Automated Backups

Create `/usr/local/bin/backup-helpdesk-db.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/backups/helpdesk"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/helpdesk_$TIMESTAMP.sql.gz"

mkdir -p $BACKUP_DIR

# Backup database
PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
    -h $POSTGRES_HOST \
    -U $POSTGRES_USER \
    -d $POSTGRES_DB | gzip > $BACKUP_FILE

# Keep only last 7 days of backups
find $BACKUP_DIR -name "helpdesk_*.sql.gz" -mtime +7 -delete

# Upload to S3 (optional)
# aws s3 cp $BACKUP_FILE s3://your-bucket/backups/

echo "Backup completed: $BACKUP_FILE"
```

Add to crontab:

```bash
# Daily backup at 2 AM
0 2 * * * /usr/local/bin/backup-helpdesk-db.sh >> /var/log/helpdesk-backup.log 2>&1
```

---

## Monitoring and Logging

### Application Logs

```bash
# API logs
tail -f /var/log/helpdesk/api-access.log
tail -f /var/log/helpdesk/api-error.log

# Bot logs
sudo journalctl -u helpdesk-bot -f
```

### Health Monitoring

```bash
# Check API health
curl https://your-domain.com/health

# Check database connection
curl https://your-domain.com/api/tasks
```

### Setup Monitoring with Prometheus

Install Prometheus and add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: "helpdesk-bot"
    static_configs:
      - targets: ["localhost:8000"]
```

### Setup Alerting with Alertmanager

Create alerts in `prometheus-rules.yml`:

```yaml
groups:
  - name: helpdesk
    rules:
      - alert: APIDowEvent
        expr: up{job="helpdesk-bot"} == 0
        for: 5m
        annotations:
          summary: "HelpDesk API is down"

      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 0.05
        annotations:
          summary: "High error rate in HelpDesk"
```

---

## Scaling Considerations

### Horizontal Scaling

For multiple app instances:

1. **Load Balancer**: Use HAProxy or AWS Load Balancer
2. **Bot Webhook**: Switch from polling to webhook (requires webhook URL)
3. **Session Storage**: Use Redis instead of memory for FSM state
4. **Database Pool**: Increase connection pool size

### Vertical Scaling

Increase resources:

- Worker threads
- Memory allocation
- CPU cores

---

## Rollback Procedure

### Rollback to Previous Version

```bash
# Identify previous version
docker-compose images

# Rollback docker-compose.yml to previous version
git checkout HEAD~1 docker-compose.yml

# Stop current services
docker-compose down

# Start previous version
docker-compose up -d

# Rollback database (if schema changed)
alembic downgrade -1
```

---

## Security Considerations

### SSL/TLS

```bash
# Obtain certificate with Let's Encrypt
sudo certbot certonly --standalone -d your-domain.com
sudo certbot renew --dry-run  # Test renewal
```

### Firewall Configuration

```bash
# UFW firewall rules
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 5432/tcp    # PostgreSQL (if remote)
sudo ufw enable
```

### Database Security

```bash
# PostgreSQL connection encryption
# In pg_hba.conf, use md5 or scram-sha-256
# hostssl  helpdesk  helpdesk_user  0.0.0.0/0  scram-sha-256
```

---

## Performance Tuning

### PostgreSQL Optimization

```sql
-- Shared buffers (25% of RAM)
shared_buffers = 4GB

-- Effective cache size (50-75% of RAM)
effective_cache_size = 12GB

-- Work memory
work_mem = 10MB

-- Create indexes on frequently queried columns
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_executor ON tasks(executor_id);
CREATE INDEX idx_users_telegram ON users(telegram_id);
```

### Application Optimization

- Use connection pooling (SQLAlchemy default)
- Enable gzip compression in Nginx
- Cache static files
- Use CDN for static assets

---

## Troubleshooting

### Bot Not Responding

1. Check bot token: `curl https://api.telegram.org/bot$TOKEN/getMe`
2. Check logs: `docker-compose logs -f app`
3. Verify database: `psql -h localhost -U helpdesk_user -d helpdesk`

### Database Errors

```bash
# Check connections
SELECT datname, usename, count(*) FROM pg_stat_activity GROUP BY datname, usename;

# Kill idle connections
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE datname='helpdesk' AND state='idle';
```

### High CPU Usage

```bash
# Check slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY total_time DESC LIMIT 10;

# Enable query logging
log_min_duration_statement = 1000  # Log queries > 1s
```

---

## Post-Deployment

### Verify Deployment

- [ ] Health check passes
- [ ] Bot responds to commands
- [ ] API endpoints working
- [ ] Database connectivity confirmed
- [ ] Logs clean (no errors)
- [ ] SSL/TLS working
- [ ] Backups running

### Documentation

- Record deployment details
- Document any customizations
- Create runbooks for common tasks
- Setup monitoring alerts

---

## Support

For deployment issues, refer to:

1. Application logs
2. Database logs
3. System logs
4. Service status

Create issue with logs attached for support.
