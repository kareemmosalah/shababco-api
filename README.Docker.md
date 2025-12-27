# 🐳 Docker Setup Guide - Shababco API

Complete guide for running the Shababco API using Docker.

---

## 📋 Prerequisites

- **Docker** 20.10+ & **Docker Compose** 2.0+
- **Git** for cloning the repository
- **8GB RAM** minimum for all services

---

## 🚀 Quick Start (Development)

### 1. Clone & Configure

```bash
# Clone repository
git clone <repository-url>
cd shababco-api

# Create .env file with production values
nano .env  # Add your production credentials (see required variables below)
```

### 2. Start All Services

```bash
# Build and start (first time)
docker-compose up --build -d

# Start (subsequent times)
docker-compose up -d

# View logs
docker-compose logs -f backend
```

### 3. Access Services

| Service         | URL                        | Description                   |
| --------------- | -------------------------- | ----------------------------- |
| **API**         | http://localhost:8000      | FastAPI backend               |
| **API Docs**    | http://localhost:8000/docs | Swagger UI                    |
| **MailCatcher** | http://localhost:1080      | Email testing                 |
| **Redis**       | localhost:6379             | Cache (direct)                |
| **Database**    | External Supabase          | Managed PostgreSQL (see .env) |

### 4. Verify Setup

```bash
# Check all services are healthy
docker-compose ps

# Test API health endpoint
curl http://localhost:8000/api/v1/utils/health-check/

# View backend logs
docker-compose logs backend | tail -50
```

---

## 🛠️ Development Workflow

### Hot Reload

Code changes in `backend/app/` are automatically detected and trigger a reload.

```bash
# Edit files in backend/app/
nano backend/app/api/routes/events.py

# Changes are live immediately (no restart needed!)
```

### Run Commands Inside Container

```bash
# Access backend shell
docker-compose exec backend bash

# Run migrations manually (if needed - Supabase schema already migrated)
docker-compose exec backend alembic upgrade head

# Create a new migration
docker-compose exec backend alembic revision --autogenerate -m "Add new field"

# Run tests
docker-compose exec backend pytest

# Format code
docker-compose exec backend ruff format .

# Lint code
docker-compose exec backend ruff check .
```

### Database Management

```bash
# Access PostgreSQL CLI
docker-compose exec db psql -U postgres -d app

# Backup database
docker-compose exec db pg_dump -U postgres app > backup.sql

# Restore database
docker-compose exec -T db psql -U postgres app < backup.sql

# Reset database (WARNING: destroys all data)
docker-compose down -v
docker-compose up -d
```

### Redis Operations

```bash
# Access Redis CLI
docker-compose exec redis redis-cli

# Clear cache
docker-compose exec redis redis-cli FLUSHDB

# Monitor cache operations
docker-compose exec redis redis-cli MONITOR
```

---

## 🏭 Production Deployment

### Build Production Image

```bash
# Build production image (no dev dependencies, smaller size)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Or build directly
docker build --target application -t shababco-backend:prod ./backend
```

### Run Production Stack

```bash
# Start production services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Production uses:
# - 4 uvicorn workers (or gunicorn)
# - No volume mounts (code baked in)
# - No dev tools (mailcatcher disabled)
# - Resource limits enforced
```

### Production Checklist

- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Generate strong `SECRET_KEY` (min 32 characters)
- [ ] Verify `DATABASE_URL` points to Supabase production
- [ ] Set `REDIS_PASSWORD` if using Redis
- [ ] Configure real SMTP server (not mailcatcher)
- [ ] Set `SENTRY_DSN` for error tracking
- [ ] Update `BACKEND_CORS_ORIGINS` with real frontend URL
- [ ] Rotate all Shopify API tokens
- [ ] Remove `.env` from repository (use secrets manager)
- [ ] Enable HTTPS/TLS (use Traefik or nginx)
- [ ] Enable automated backups in Supabase dashboard
- [ ] Configure log aggregation (ELK, CloudWatch, etc.)

---

## 🔧 Troubleshooting

### Backend Won't Start

```bash
# Check logs
docker-compose logs backend

# Common issues:
# 1. Missing required env vars
docker-compose exec backend env | grep -E "DATABASE_URL|FIRST_SUPERUSER|PROJECT_NAME"

# 2. Database connection (Supabase)
# Check DATABASE_URL in .env is correct

# 3. Port already in use
lsof -i :8000
```

### Database Connection Errors

```bash
# Test database connectivity
docker-compose exec backend python -c "
from app.core.db import engine
from sqlmodel import select, Session
try:
    with Session(engine) as session:
        session.execute(select(1))
    print('✅ Database connection OK')
except Exception as e:
    print(f'❌ Database error: {e}')
"
```

### Migration Failures

```bash
# Note: Migrations are disabled in prestart.sh (Supabase already migrated)
# Only use if you need to apply new migrations:

# Check current migration state
docker-compose exec backend alembic current

# View migration history
docker-compose exec backend alembic history

# Downgrade one version (use with caution on Supabase!)
docker-compose exec backend alembic downgrade -1

# Upgrade to specific version
docker-compose exec backend alembic upgrade <revision_id>

# Force stamp database (careful!)
docker-compose exec backend alembic stamp head
```

### Redis Not Working

```bash
# Check Redis connectivity
docker-compose exec backend python -c "
import redis
try:
    r = redis.from_url('redis://redis:6379')
    r.ping()
    print('✅ Redis connection OK')
except Exception as e:
    print(f'❌ Redis error: {e}')
"

# Redis is optional - app works without it
# Check logs for "Redis not available" warnings
```

### Performance Issues

```bash
# Check resource usage
docker stats

# View backend process info
docker-compose exec backend ps aux

# Check database connections via Supabase dashboard
# Or query DATABASE_URL directly with psql

# Monitor API response times
docker-compose logs backend | grep "GET /api"
```

---

## 🧪 Testing

### Run All Tests

```bash
# Run full test suite
docker-compose exec backend pytest

# Run with coverage
docker-compose exec backend pytest --cov=app --cov-report=html

# Run specific test file
docker-compose exec backend pytest tests/api/routes/test_events.py

# Run tests matching pattern
docker-compose exec backend pytest -k "test_create"
```

### Test Database

Tests use the same PostgreSQL instance but a different database:

```bash
# Check test database
docker-compose exec db psql -U postgres -l | grep test
```

---

## 📦 Image Management

### View Images

```bash
# List images
docker images shababco-backend

# Check image size
docker images shababco-backend --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
```

### Clean Up

```bash
# Stop and remove containers
docker-compose down

# Remove containers and volumes (DESTROYS DATA)
docker-compose down -v

# Remove images
docker rmi shababco-backend:dev
docker rmi shababco-backend:latest

# Clean up unused Docker resources
docker system prune -a
```

### Export/Import Images

```bash
# Save image to tar
docker save shababco-backend:latest | gzip > shababco-backend.tar.gz

# Load image from tar
gunzip -c shababco-backend.tar.gz | docker load

# Push to registry (GitHub Container Registry)
docker tag shababco-backend:latest ghcr.io/your-org/shababco-backend:latest
docker push ghcr.io/your-org/shababco-backend:latest
```

---

## 🔐 Security Best Practices

1. **Never commit `.env`** - Use `.env.example` template only
2. **Rotate secrets regularly** - Especially after any compromise
3. **Use secrets managers** - AWS Secrets Manager, HashiCorp Vault, etc.
4. **Scan images** - Use Trivy, Snyk, or Docker Scout
5. **Run as non-root** - Already configured (user `appuser`)
6. **Update base images** - Regularly rebuild with latest `python:3.12-slim`
7. **Enable TLS** - Use reverse proxy (Traefik, nginx) for HTTPS
8. **Limit resource usage** - Prevent DoS attacks
9. **Monitor logs** - Set up alerts for suspicious activity
10. **Network segmentation** - Use Docker networks properly

---

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Compose Docs](https://docs.docker.com/compose/)
- [PostgreSQL Docker](https://hub.docker.com/_/postgres)
- [Redis Docker](https://hub.docker.com/_/redis)
- [Alembic Migrations](https://alembic.sqlalchemy.org/)

---

## 🆘 Getting Help

1. Check logs: `docker-compose logs backend`
2. Review `.env` configuration
3. Verify all services are healthy: `docker-compose ps`
4. Test database connectivity
5. Check GitHub Issues or create new one

---

**Ready to deploy?** 🚀 Follow the production checklist above and deploy with confidence!
