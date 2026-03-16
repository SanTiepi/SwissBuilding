#!/bin/bash
# Check SwissBuilding status on VPS
# Usage: bash scripts/vps-status.sh
# Note: Run `chmod +x scripts/vps-status.sh` to make executable

ssh root@194.93.48.163 "cd /opt/swissbuilding/infrastructure && docker compose -f docker-compose.production.yml ps && echo '' && curl -sf http://localhost:8000/health && echo ''"
