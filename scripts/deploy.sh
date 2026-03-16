#!/bin/bash
# SwissBuilding OS — Deploy to VPS via GitHub
# Usage: bash scripts/deploy.sh
# Note: Run `chmod +x scripts/deploy.sh` to make executable on Linux/WSL

set -euo pipefail

SSH_KEY="$HOME/.ssh/id_ed25519_batiscan_vps"
VPS_HOST="root@194.93.48.163"
VPS_DIR="/opt/swissbuilding"
REPO_URL="https://github.com/SanTiepi/SwissBuilding.git"

echo "=== SwissBuilding Deploy ==="
echo "Repo: $REPO_URL"
echo "Target: $VPS_HOST:$VPS_DIR"

# Deploy via SSH
ssh -i "$SSH_KEY" $VPS_HOST << 'REMOTE_SCRIPT'
set -euo pipefail

VPS_DIR="/opt/swissbuilding"
REPO_URL="https://github.com/SanTiepi/SwissBuilding.git"

# Step 1: Clone or pull
if [ -d "$VPS_DIR/.git" ]; then
    echo ">>> Pulling latest changes..."
    cd "$VPS_DIR"
    git pull --ff-only
else
    echo ">>> Cloning repository..."
    rm -rf "$VPS_DIR"
    git clone "$REPO_URL" "$VPS_DIR"
fi

# Step 2: Run setup
echo ">>> Running setup..."
chmod +x "$VPS_DIR/scripts/setup-vps.sh"
bash "$VPS_DIR/scripts/setup-vps.sh"

echo "=== Deploy complete ==="
echo "Access: http://194.93.48.163"
REMOTE_SCRIPT
