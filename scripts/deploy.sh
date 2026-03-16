#!/bin/bash
# SwissBuilding OS — Deploy to VPS
# Usage: bash scripts/deploy.sh
# Note: Run `chmod +x scripts/deploy.sh` to make executable on Linux/WSL

set -euo pipefail

VPS_HOST="root@194.93.48.163"
VPS_DIR="/opt/swissbuilding"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== SwissBuilding Deploy ==="
echo "Source: $LOCAL_DIR"
echo "Target: $VPS_HOST:$VPS_DIR"

# Step 1: Ensure target directory exists
ssh $VPS_HOST "mkdir -p $VPS_DIR"

# Step 2: Rsync project (exclude heavy/dev files)
echo ">>> Syncing files..."
rsync -avz --delete \
  --exclude 'node_modules/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude 'dist/' \
  --exclude '.env' \
  --exclude '.env.production' \
  --exclude '*.pyc' \
  --exclude '.git/' \
  --exclude 'frontend/test-results/' \
  --exclude 'tmp/' \
  "$LOCAL_DIR/" "$VPS_HOST:$VPS_DIR/"

# Step 3: Run setup on VPS
echo ">>> Running setup on VPS..."
ssh $VPS_HOST "bash $VPS_DIR/scripts/setup-vps.sh"

echo "=== Deploy complete ==="
echo "Access: http://194.93.48.163"
