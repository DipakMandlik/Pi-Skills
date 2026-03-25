# Deployment Guide

## Quick Start (Docker Compose)

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 20GB disk space

### Production Deployment Steps

#### 1. Clone and Setup
```bash
git clone your-repo/ai-governance.git
cd ai-governance
cp .env.production .env
```

#### 2. Configure Environment
Edit `.env` with production values:
```bash
# REQUIRED: Generate secure JWT secret
JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")

# REQUIRED: Set strong passwords
POSTGRES_PASSWORD=your_secure_password
REDIS_PASSWORD=your_secure_password

# REQUIRED: Update API keys for model providers (at least one)
ANTHROPIC_API_KEY=sk-ant-...
# OR
OPENAI_API_KEY=sk-...
```

#### 3. Build and Start
```bash
# Build all services
npm run docker:build

# Start all services
npm run docker:up

# Check status
docker-compose ps
```

#### 4. Verify Deployment
```bash
# Check backend health
curl http://localhost:8000/health

# Check frontend
curl http://localhost:3000

# View logs
npm run docker:logs
```

---

## Production Checklist

### Security
- [ ] Change JWT_SECRET to random 64-char hex value
- [ ] Update POSTGRES_PASSWORD to strong password
- [ ] Update REDIS_PASSWORD to strong password
- [ ] Configure CORS_ORIGINS for your domain
- [ ] Enable HTTPS (configure SSL certificates)
- [ ] Update default admin credentials

### Database
- [ ] PostgreSQL configured with authentication
- [ ] Redis configured with password
- [ ] Database migrations applied
- [ ] Initial data seeded

### Monitoring
- [ ] Health checks configured
- [ ] Log rotation enabled
- [ ] Backup strategy implemented

---

## Manual Deployment (Non-Docker)

### Backend Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r backend/requirements.txt

# Set environment
export APP_ENV=production
export POSTGRES_DSN=postgresql+asyncpg://user:pass@host:5432/db
export REDIS_URL=redis://:pass@host:6379/0

# Run with Gunicorn/Uvicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.main:app
```

### Frontend Build
```bash
npm run build
# Serve dist/ with Nginx/Apache
```

---

## AWS EC2 Deployment

### Instance Setup
```bash
# t3.medium or larger recommended
# Ubuntu 22.04 LTS

# Install Docker
sudo apt update
sudo apt install docker.io docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
```

### Deployment
```bash
# Clone repository
git clone ...
cd ai-governance

# Configure environment
cp .env.production .env
nano .env  # Update values

# Start services
docker-compose up -d
```

---

## Kubernetes Deployment (EKS)

### Helm Chart Structure
```
k8s/
  Chart.yaml
  values.yaml
  templates/
    deployment.yaml
    service.yaml
    ingress.yaml
    secret.yaml
```

### Deploy
```bash
# Create EKS cluster
eksctl create cluster --name ai-governance

# Deploy helm chart
helm upgrade --install ai-governance ./k8s \
  --set image.tag=latest \
  --set ingress.hostname=yourdomain.com
```

---

## Troubleshooting

### Services not starting
```bash
# Check logs
docker-compose logs postgres
docker-compose logs redis
docker-compose logs backend

# Check ports
netstat -tulpn | grep -E '5432|6379|8000|3000'
```

### Database connection issues
```bash
# Test database connection
docker-compose exec backend python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
async def test():
    engine = create_async_engine('postgresql+asyncpg://postgres:pass@postgres:5432/ai_governance')
    async with engine.connect() as conn:
        print('DB OK')
asyncio.run(test())
"
```

### Permission issues
```bash
# Fix permissions
sudo chown -R $USER:$USER .
chmod -R 755 .
```

---

## Backup & Recovery

### Database Backup
```bash
# Backup database
docker-compose exec postgres pg_dump -U postgres ai_governance > backup.sql

# Restore database
docker-compose exec -T postgres psql -U postgres ai_governance < backup.sql
```

### Redis Backup
```bash
# Save Redis persistence
docker-compose exec redis redis-cli -a YOUR_PASSWORD SAVE
```

---

## API Endpoints in Production

| Endpoint | URL | Description |
|----------|-----|-------------|
| Health | GET /health | Service health check |
| Login | POST /auth/login | User authentication |
| Execute | POST /execute | AI model execution |
| Skills | GET/POST /skills | Skill management |
| Models | GET/POST /models | Model management |
| Monitoring | GET /monitoring | Audit logs (admin) |
| Users | GET /users | User list (admin) |