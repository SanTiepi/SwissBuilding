#!/bin/bash
# SwissBuilding OS — VPS Setup Script
# Runs on the VPS after rsync
# Note: Run `chmod +x scripts/setup-vps.sh` to make executable

set -euo pipefail

PROJECT_DIR="/opt/swissbuilding"
cd "$PROJECT_DIR"

echo "=== SwissBuilding VPS Setup ==="

# Step 1: Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo ">>> Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

# Step 2: Install Docker Compose plugin if not present
if ! docker compose version &> /dev/null; then
    echo ">>> Installing Docker Compose plugin..."
    apt-get update && apt-get install -y docker-compose-plugin
fi

# Step 3: Generate .env.production if it doesn't exist
ENV_FILE="$PROJECT_DIR/.env.production"
if [ ! -f "$ENV_FILE" ]; then
    echo ">>> Generating .env.production with random secrets..."

    POSTGRES_PW=$(openssl rand -base64 24 | tr -d '/+=' | head -c 32)
    JWT_SECRET=$(openssl rand -hex 32)
    S3_KEY=$(openssl rand -base64 16 | tr -d '/+=' | head -c 20)
    S3_SECRET=$(openssl rand -base64 32 | tr -d '/+=' | head -c 40)
    MEILI_KEY=$(openssl rand -hex 16)
    GLITCHTIP_SECRET=$(openssl rand -hex 32)

    cat > "$ENV_FILE" << EOF
# SwissBuilding OS — Production Environment
# Auto-generated on $(date -u +%Y-%m-%dT%H:%M:%SZ)

# PostgreSQL
POSTGRES_DB=swissbuildingos
POSTGRES_USER=swissbuildingos
POSTGRES_PASSWORD=$POSTGRES_PW
DATABASE_URL=postgresql+asyncpg://swissbuildingos:$POSTGRES_PW@postgres:5432/swissbuildingos

# JWT
JWT_SECRET_KEY=$JWT_SECRET
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=480

# S3 / MinIO
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=$S3_KEY
S3_SECRET_KEY=$S3_SECRET
S3_BUCKET=swissbuildingos

# Redis
REDIS_URL=redis://redis:6379/0

# Meilisearch
MEILISEARCH_URL=http://meilisearch:7700
MEILISEARCH_API_KEY=$MEILI_KEY

# GlitchTip
GLITCHTIP_DSN=
GLITCHTIP_SECRET_KEY=$GLITCHTIP_SECRET

# CORS — allow the VPS IP
CORS_ORIGINS=["http://194.93.48.163"]

# Domain — using IP for now
DOMAIN=194.93.48.163
ACME_EMAIL=

# Backend
ENVIRONMENT=production
LOG_LEVEL=INFO
EOF

    chmod 600 "$ENV_FILE"
    echo ">>> .env.production created with random secrets"
else
    echo ">>> .env.production already exists, keeping it"
fi

# Step 4: Create Caddyfile for IP-only (no TLS)
cat > "$PROJECT_DIR/infrastructure/Caddyfile" << 'EOF'
:80 {
    # Frontend (default)
    handle {
        reverse_proxy frontend:80
    }

    # API
    handle /api/* {
        reverse_proxy backend:8000
    }

    # Health
    handle /health {
        reverse_proxy backend:8000
    }

    # Docs
    handle /docs {
        reverse_proxy backend:8000
    }
    handle /openapi.json {
        reverse_proxy backend:8000
    }

    # Security headers
    header {
        X-Frame-Options SAMEORIGIN
        X-Content-Type-Options nosniff
        X-XSS-Protection "1; mode=block"
        Referrer-Policy strict-origin-when-cross-origin
    }
}
EOF

# Step 5: Build and start services
echo ">>> Building and starting SwissBuilding..."
cd "$PROJECT_DIR/infrastructure"
docker compose -f docker-compose.production.yml --env-file "$PROJECT_DIR/.env.production" down --remove-orphans 2>/dev/null || true
docker compose -f docker-compose.production.yml --env-file "$PROJECT_DIR/.env.production" up -d --build

# Step 6: Wait for services to start
echo ">>> Waiting for services to start..."
sleep 10

# Step 7: Check health
echo ""
echo "=== Service Status ==="
docker compose -f docker-compose.production.yml ps

echo ""
echo ">>> Checking backend health..."
for i in {1..30}; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "Backend is healthy!"
        break
    fi
    echo "  Waiting for backend... ($i/30)"
    sleep 5
done

echo ""
echo "=== SwissBuilding is running ==="
echo "Frontend: http://194.93.48.163"
echo "API:      http://194.93.48.163/api/"
echo "Health:   http://194.93.48.163/health"
echo "Docs:     http://194.93.48.163/docs"
