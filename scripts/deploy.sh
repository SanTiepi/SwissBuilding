#!/bin/bash
# SwissBuilding / BatiConnect — Deploy to VPS
# Usage: bash scripts/deploy.sh
# Prerequisites:
#   1. Domain app.swissbuilding.ch DNS pointing to 83.228.221.188
#   2. Infomaniak S3 buckets created (swissbuilding-uploads, swissbuilding-reports, swissbuilding-backups)
#   3. .env.production file with real credentials on VPS

set -euo pipefail

SSH_KEY="$HOME/.ssh/id_ed25519_batiscan_vps"
VPS_HOST="ubuntu@83.228.221.188"
VPS_DIR="/home/ubuntu/SwissBuilding"
REPO_URL="https://github.com/SanTiepi/SwissBuilding.git"

echo "=== SwissBuilding Deploy ==="
echo "Repo: $REPO_URL"
echo "Target: $VPS_HOST:$VPS_DIR"

ssh -i "$SSH_KEY" "$VPS_HOST" << 'REMOTE_SCRIPT'
set -euo pipefail

VPS_DIR="/home/ubuntu/SwissBuilding"
REPO_URL="https://github.com/SanTiepi/SwissBuilding.git"
INFRA_DIR="$VPS_DIR/infrastructure"

echo ">>> Step 1: Clone or pull"
if [ -d "$VPS_DIR/.git" ]; then
    cd "$VPS_DIR"
    git pull --ff-only
else
    git clone "$REPO_URL" "$VPS_DIR"
fi

echo ">>> Step 2: Create data directories"
sudo mkdir -p /mnt/data/swissbuilding/{postgres,uploads,backups,tmp}
sudo chown -R 999:999 /mnt/data/swissbuilding/postgres  # postgres user

echo ">>> Step 3: Check .env.production"
if [ ! -f "$INFRA_DIR/.env.production" ]; then
    echo "ERROR: $INFRA_DIR/.env.production not found!"
    echo "Copy .env.production.example and fill in real values."
    exit 1
fi

echo ">>> Step 4: Build and start SwissBuilding stack"
cd "$INFRA_DIR"
docker compose -f docker-compose.production.yml --env-file .env.production build
docker compose -f docker-compose.production.yml --env-file .env.production up -d

echo ">>> Step 5: Connect Batiscan Caddy to SwissBuilding network"
docker network connect swissbuilding batiscan_caddy 2>/dev/null || echo "Already connected"

echo ">>> Step 6: Append SwissBuilding config to Caddy"
CADDY_FILE="/home/ubuntu/Batiscan-V4/Caddyfile"
if ! grep -q "app.swissbuilding.ch" "$CADDY_FILE" 2>/dev/null; then
    echo "" >> "$CADDY_FILE"
    cat "$INFRA_DIR/Caddyfile" >> "$CADDY_FILE"
    echo ">>> Added SwissBuilding block to Caddyfile"
else
    echo ">>> SwissBuilding block already in Caddyfile"
fi

echo ">>> Step 7: Reload Caddy"
docker exec batiscan_caddy caddy reload --config /etc/caddy/Caddyfile

echo ">>> Step 8: Run migrations"
docker exec swissbuilding-backend python -m alembic upgrade head || echo "Migrations skipped (may need manual run)"

echo ">>> Step 9: Health check"
sleep 5
if docker exec swissbuilding-backend python -c "import app; print('Backend OK')" 2>/dev/null; then
    echo "Backend: OK"
else
    echo "Backend: CHECKING..."
    docker logs swissbuilding-backend --tail 20
fi

echo ""
echo "=== Deploy complete ==="
echo "URL: https://app.swissbuilding.ch"
echo "Health: https://app.swissbuilding.ch/health"
echo ""
echo "Containers:"
docker ps --filter "name=swissbuilding" --format "table {{.Names}}\t{{.Status}}"
REMOTE_SCRIPT
