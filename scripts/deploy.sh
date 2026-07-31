#!/bin/bash
# ============================================================
# DeepLV — Production Deployment Script
# ============================================================
# Run this on your laptop / Raspberry Pi after:
#   1. Filling in .env with your values
#   2. Setting up Cloudflare Tunnel
#   3. (Optional) Downloading translation models
#
# Usage:
#   chmod +x scripts/deploy.sh
#   ./scripts/deploy.sh
# ============================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   DeepLV Production Deployment       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}[1/6] Checking prerequisites...${NC}"
command -v docker >/dev/null 2>&1 || { echo -e "${RED}Error: docker not found. Install Docker first.${NC}"; exit 1; }
command -v docker compose version >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1 || { echo -e "${RED}Error: docker compose not found.${NC}"; exit 1; }
echo -e "${GREEN}  ✓ Docker found${NC}"

# Check .env file
echo -e "${YELLOW}[2/6] Checking configuration...${NC}"
if [ ! -f .env ]; then
    echo -e "${YELLOW}  .env not found. Copying from .env.production...${NC}"
    cp .env.production .env
    echo -e "${RED}  ⚠ Please edit .env with your actual values, then re-run this script.${NC}"
    echo ""
    echo "  Required values to change:"
    echo "    - DOMAIN"
    echo "    - DATABASE_URL (from Supabase)"
    echo "    - JWT_SECRET (run: openssl rand -hex 32)"
    echo "    - ENCRYPTION_KEY (run: openssl rand -hex 32)"
    echo "    - CLOUDFLARE_TUNNEL_TOKEN"
    echo "    - GRAFANA_ADMIN_PASSWORD"
    echo ""
    exit 1
fi

# Validate critical env vars
source .env 2>/dev/null || true
if [[ "${JWT_SECRET:-}" == *"CHANGE_ME"* ]] || [[ "${JWT_SECRET:-}" == *"dev-"* ]]; then
    echo -e "${RED}  ⚠ JWT_SECRET is still set to a default value. Please generate a secure one:${NC}"
    echo "    openssl rand -hex 32"
    exit 1
fi
if [[ "${CLOUDFLARE_TUNNEL_TOKEN:-}" == *"YOUR_TUNNEL"* ]] || [[ -z "${CLOUDFLARE_TUNNEL_TOKEN:-}" ]]; then
    echo -e "${RED}  ⚠ CLOUDFLARE_TUNNEL_TOKEN is not set. Create a tunnel at:${NC}"
    echo "    https://one.dash.cloudflare.com > Networks > Tunnels"
    exit 1
fi
if [[ "${DATABASE_URL:-}" == *"YOUR_PROJECT_REF"* ]] || [[ "${DATABASE_URL:-}" == *"localhost"* ]]; then
    echo -e "${RED}  ⚠ DATABASE_URL still points to placeholder/localhost. Set your Supabase URL.${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Configuration looks good${NC}"

# Copy production nginx config
echo -e "${YELLOW}[3/6] Preparing nginx configuration...${NC}"
cp frontend/nginx.prod.conf frontend/nginx.conf
echo -e "${GREEN}  ✓ Production nginx config applied${NC}"

# Build and start
echo -e "${YELLOW}[4/6] Building Docker images (this may take a while on first run)...${NC}"
docker compose -f docker-compose.prod.yml build --parallel

echo -e "${YELLOW}[5/6] Starting services...${NC}"
docker compose -f docker-compose.prod.yml up -d

echo -e "${YELLOW}[6/6] Waiting for health checks...${NC}"
sleep 10

# Check service health
echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  Deployment Status${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"

services=(redis worker api frontend cloudflared prometheus grafana)
all_healthy=true
for svc in "${services[@]}"; do
    status=$(docker compose -f docker-compose.prod.yml ps --format '{{.Status}}' "$svc" 2>/dev/null || echo "not running")
    if echo "$status" | grep -qi "up\|healthy"; then
        echo -e "  ${GREEN}✓${NC} $svc: $status"
    else
        echo -e "  ${RED}✗${NC} $svc: $status"
        all_healthy=false
    fi
done

echo ""
if [ "$all_healthy" = true ]; then
    echo -e "${GREEN}  All services running!${NC}"
    echo ""
    echo "  Your DeepLV instance is now live at:"
    echo -e "    ${GREEN}https://${DOMAIN:-translate.yourdomain.com}${NC}"
    echo ""
    echo "  Grafana (monitoring):"
    echo -e "    ${GREEN}https://${DOMAIN:-translate.yourdomain.com}/grafana/${NC}"
    echo ""
    echo "  API docs:"
    echo -e "    ${GREEN}https://${DOMAIN:-translate.yourdomain.com}/docs${NC}"
else
    echo -e "${YELLOW}  Some services may still be starting. Check with:${NC}"
    echo "    docker compose -f docker-compose.prod.yml ps"
    echo "    docker compose -f docker-compose.prod.yml logs -f"
fi

echo ""
echo "  Useful commands:"
echo "    Logs:      docker compose -f docker-compose.prod.yml logs -f"
echo "    Stop:      docker compose -f docker-compose.prod.yml down"
echo "    Restart:   docker compose -f docker-compose.prod.yml restart"
echo "    Update:    git pull && ./scripts/deploy.sh"
echo ""
