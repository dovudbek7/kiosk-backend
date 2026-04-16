# Deployment Guide - Kiosk Backend

This guide covers deploying the Kiosk Backend to a production environment.

---

## Pre-Deployment Checklist

### 1. Environment & Dependencies

- [ ] Python 3.8+ installed on target server
- [ ] PostgreSQL installed and running (production DB)
- [ ] Redis installed (for SSE/caching)
- [ ] Nginx/Apache installed (reverse proxy)
- [ ] Supervisor/systemd for process management
- [ ] All requirements installed: `pip install -r requirements.txt`

### 2. Django Settings Updates

Create `config/.env` or use environment variables:

```bash
# .env file
DEBUG=False
SECRET_KEY=your-very-long-random-secret-key-here-min-50-chars
ALLOWED_HOSTS=example.com,www.example.com,api.example.com
DB_ENGINE=django.db.backends.postgresql
DB_NAME=kiosk_db
DB_USER=kiosk_user
DB_PASSWORD=secure_password_here
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379/0
CORS_ALLOWED_ORIGINS=https://example.com,https://app.example.com
```

Update `config/settings.py`:

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Security
DEBUG = os.getenv('DEBUG', 'False') == 'True'
SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-in-production')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')

# Database
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('DB_NAME', BASE_DIR / 'db.sqlite3'),
        'USER': os.getenv('DB_USER', ''),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', ''),
        'PORT': os.getenv('DB_PORT', ''),
    }
}

# SSL/HTTPS
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_BROWSER_XSS_FILTER = True
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG

# CORS
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True

# Redis (for SSE with Channels)
if not DEBUG:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [os.getenv('REDIS_URL', 'redis://localhost:6379/0')],
            },
        },
    }
```

### 3. Database Migration

```bash
# Backup SQLite (if upgrading)
cp db.sqlite3 db.sqlite3.backup

# Create PostgreSQL database
createdb kiosk_db

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

---

## Deployment Option 1: Using Gunicorn + Supervisor

### 1. Install Dependencies

```bash
pip install gunicorn python-dotenv channels channels-redis
```

### 2. Create Gunicorn Service File

`/etc/supervisor/conf.d/kiosk-backend.conf`:

```ini
[program:kiosk-backend]
command=/home/django/kiosk-backend/venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 4 --worker-class uvicorn.workers.UvicornWorker
directory=/home/django/kiosk-backend
user=django
autostart=true
autorestart=true
stderr_logfile=/home/django/kiosk-backend/logs/gunicorn_err.log
stdout_logfile=/home/django/kiosk-backend/logs/gunicorn_out.log
```

### 3. Create Daphne Service File (for WebSocket/SSE)

`/etc/supervisor/conf.d/kiosk-daphne.conf`:

```ini
[program:kiosk-daphne]
command=/home/django/kiosk-backend/venv/bin/daphne -b 127.0.0.1 -p 8001 config.asgi:application
directory=/home/django/kiosk-backend
user=django
autostart=true
autorestart=true
stderr_logfile=/home/django/kiosk-backend/logs/daphne_err.log
stdout_logfile=/home/django/kiosk-backend/logs/daphne_out.log
```

### 4. Create Nginx Configuration

`/etc/nginx/sites-available/kiosk-backend`:

```nginx
upstream gunicorn {
    server 127.0.0.1:8000;
}

upstream daphne {
    server 127.0.0.1:8001;
}

server {
    listen 80;
    server_name api.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 100M;

    location / {
        proxy_pass http://gunicorn;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket/SSE endpoint
    location /api/notifications/stream {
        proxy_pass http://daphne;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    location /static/ {
        alias /home/django/kiosk-backend/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /home/django/kiosk-backend/media/;
        expires 7d;
    }
}
```

### 5. Enable and Start Services

```bash
# Create logs directory
mkdir -p /home/django/kiosk-backend/logs

# Enable Nginx site
sudo ln -s /etc/nginx/sites-available/kiosk-backend /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Start Supervisor services
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl status all
```

---

## Deployment Option 2: Using Docker

### 1. Create Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn daphne channels-redis

# Copy application
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Create user
RUN useradd -m -u 1000 django && chown -R django:django /app
USER django

# Expose ports
EXPOSE 8000 8001

# Start command
CMD ["bash", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:8000 & daphne -b 0.0.0.0 -p 8001 config.asgi:application"]
```

### 2. Create docker-compose.yml

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: kiosk_db
      POSTGRES_USER: kiosk_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  web:
    build: .
    command: bash -c "
      python manage.py migrate &&
      gunicorn config.wsgi:application --bind 0.0.0.0:8000
    "
    environment:
      DEBUG: "False"
      SECRET_KEY: "your-secret-key"
      ALLOWED_HOSTS: "localhost,127.0.0.1"
      DB_ENGINE: "django.db.backends.postgresql"
      DB_NAME: "kiosk_db"
      DB_USER: "kiosk_user"
      DB_PASSWORD: "secure_password"
      DB_HOST: "db"
      DB_PORT: "5432"
      REDIS_URL: "redis://redis:6379/0"
    depends_on:
      - db
      - redis
    ports:
      - "8000:8000"
    volumes:
      - ./media:/app/media
      - ./staticfiles:/app/staticfiles

  daphne:
    build: .
    command: daphne -b 0.0.0.0 -p 8001 config.asgi:application
    environment:
      DEBUG: "False"
      SECRET_KEY: "your-secret-key"
      DB_ENGINE: "django.db.backends.postgresql"
      DB_NAME: "kiosk_db"
      DB_USER: "kiosk_user"
      DB_PASSWORD: "secure_password"
      DB_HOST: "db"
      DB_PORT: "5432"
      REDIS_URL: "redis://redis:6379/0"
    depends_on:
      - db
      - redis
    ports:
      - "8001:8001"

volumes:
  postgres_data:
```

### 3. Deploy with Docker Compose

```bash
# Build and start services
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Check logs
docker-compose logs -f web
```

---

## Deployment Option 3: Using systemd

Create `/etc/systemd/system/kiosk-backend.service`:

```ini
[Unit]
Description=Kiosk Backend Django Application
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=django
Group=django
WorkingDirectory=/home/django/kiosk-backend
Environment="PATH=/home/django/kiosk-backend/venv/bin"
EnvironmentFile=/home/django/kiosk-backend/.env
ExecStart=/home/django/kiosk-backend/venv/bin/gunicorn \
    config.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 4 \
    --worker-class sync \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable kiosk-backend
sudo systemctl start kiosk-backend
sudo systemctl status kiosk-backend
```

---

## SSL/HTTPS Setup with Let's Encrypt

### 1. Install Certbot

```bash
sudo apt-get install certbot python3-certbot-nginx
```

### 2. Generate Certificate

```bash
sudo certbot certonly --nginx -d api.example.com -d www.api.example.com
```

### 3. Auto-Renewal

```bash
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## Monitoring & Logging

### 1. Setup Logging

Add to `config/settings.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/home/django/kiosk-backend/logs/django.log',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'api_v1': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
        },
    },
}
```

### 2. Error Tracking (Sentry)

```bash
pip install sentry-sdk
```

Add to `config/settings.py`:

```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="https://your-sentry-dsn@sentry.io/your-project-id",
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=False
)
```

### 3. Monitoring Script

Create `scripts/monitor.sh`:

```bash
#!/bin/bash

# Check Django server
curl -f http://localhost:8000/api/docs/ > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Django server is down!"
    systemctl restart kiosk-backend
fi

# Check Daphne
curl -f http://localhost:8001 > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Daphne server is down!"
    systemctl restart kiosk-daphne
fi

# Check database
psql -h localhost -U kiosk_user -d kiosk_db -c "SELECT 1;" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Database is down!"
    systemctl restart postgresql
fi

# Check Redis
redis-cli ping > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Redis is down!"
    systemctl restart redis-server
fi

echo "All services operational at $(date)"
```

Add to crontab:

```bash
*/5 * * * * /home/django/kiosk-backend/scripts/monitor.sh
```

---

## Backup Strategy

### 1. Database Backup

```bash
#!/bin/bash
# backup-db.sh

BACKUP_DIR="/home/django/backups"
DB_NAME="kiosk_db"
DB_USER="kiosk_user"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# PostgreSQL backup
pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_DIR/kiosk_db_$DATE.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "kiosk_db_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/kiosk_db_$DATE.sql.gz"
```

Add to crontab:

```bash
0 2 * * * /home/django/kiosk-backend/scripts/backup-db.sh
```

### 2. Media Files Backup

```bash
#!/bin/bash
# backup-media.sh

BACKUP_DIR="/home/django/backups"
MEDIA_DIR="/home/django/kiosk-backend/media"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

tar -czf $BACKUP_DIR/media_$DATE.tar.gz $MEDIA_DIR

# Keep only last 30 days
find $BACKUP_DIR -name "media_*.tar.gz" -mtime +30 -delete

echo "Media backup completed"
```

---

## Performance Optimization

### 1. Database Indexing

```python
# In models.py, add indexes
class Message(models.Model):
    # ...
    class Meta:
        indexes = [
            models.Index(fields=['target', '-timestamp']),
            models.Index(fields=['is_read']),
        ]
```

### 2. Caching

```python
# In settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# In views.py
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # Cache for 5 minutes
def get_targets(request):
    # ...
```

### 3. Query Optimization

```python
# Use select_related and prefetch_related
queryset = ApplicationTarget.objects.select_related('user').all()
messages = Message.objects.select_related('target').all()
```

---

## Post-Deployment Verification

```bash
# 1. Check Django migrations
python manage.py migrate --check

# 2. Run system checks
python manage.py check --deploy

# 3. Test endpoints
curl -X GET https://api.example.com/api/v1/targets/
curl -X POST https://api.example.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone":"+998901234567","password":"pass"}'

# 4. Check logs
tail -f /var/log/nginx/error.log
tail -f /home/django/kiosk-backend/logs/*.log

# 5. Monitor resources
htop
iostat -x 1
```

---

## Rollback Procedure

```bash
# 1. Revert code
git revert HEAD

# 2. Revert migrations (if needed)
python manage.py migrate api_v1 0001_initial

# 3. Restart services
sudo systemctl restart kiosk-backend
sudo systemctl restart kiosk-daphne

# 4. Verify
curl https://api.example.com/api/docs/
```

---

## Troubleshooting

### Service won't start

```bash
# Check logs
systemctl status kiosk-backend
journalctl -u kiosk-backend -n 50

# Test manually
cd /home/django/kiosk-backend
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

### Database connection issues

```bash
# Test PostgreSQL
psql -h localhost -U kiosk_user -d kiosk_db -c "SELECT 1;"

# Check credentials
echo $DB_USER $DB_PASSWORD $DB_HOST $DB_PORT
```

### Redis connection issues

```bash
# Test Redis
redis-cli ping

# Check channels config
python manage.py shell
>>> from django.conf import settings
>>> settings.CHANNEL_LAYERS
```

### SSL certificate issues

```bash
# Renew certificate
sudo certbot renew --force-renewal

# Check certificate
openssl x509 -in /etc/letsencrypt/live/api.example.com/fullchain.pem -text -noout
```

---

**For additional support, refer to:**

- Django: https://docs.djangoproject.com/en/6.0/howto/deployment/
- Gunicorn: https://docs.gunicorn.org/
- Nginx: https://nginx.org/en/docs/
- Docker: https://docs.docker.com/
