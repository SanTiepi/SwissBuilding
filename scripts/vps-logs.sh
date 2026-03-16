#!/bin/bash
# View SwissBuilding logs on VPS
# Usage: bash scripts/vps-logs.sh [service] [lines]
# Example: bash scripts/vps-logs.sh backend 100
# Note: Run `chmod +x scripts/vps-logs.sh` to make executable

SERVICE="${1:-}"
LINES="${2:-50}"

ssh root@194.93.48.163 "cd /opt/swissbuilding/infrastructure && docker compose -f docker-compose.production.yml logs --tail=$LINES $SERVICE"
