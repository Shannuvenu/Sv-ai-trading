#!/bin/bash
# SV AI Trading Platform — AWS Lightsail Deployment Script
# Run this ON THE SERVER: bash setup.sh

set -e

echo "=== SV AI Trading Platform Setup ==="

# 1. Update system
echo "[1/8] Updating system..."
sudo apt update && sudo apt upgrade -y

# 2. Install Docker
echo "[2/8] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "Docker installed. You may need to re-login for group changes."
fi

# 3. Clone repo
echo "[3/8] Cloning repository..."
REPO_DIR="$HOME/sv-ai-trading"
if [ -d "$REPO_DIR" ]; then
    echo "Repository exists, pulling latest..."
    cd "$REPO_DIR" && git pull
else
    git clone https://github.com/Shannuvenu/Sv-ai-trading.git "$REPO_DIR"
    cd "$REPO_DIR"
fi

# 4. Create directories
echo "[4/8] Creating directories..."
mkdir -p "$REPO_DIR/backups"

# 5. Create .env file if it doesn't exist
echo "[5/8] Creating .env file..."
if [ ! -f "$REPO_DIR/.env" ]; then
    cat > "$REPO_DIR/.env" << 'ENVEOF'
# === REQUIRED — Generate strong values ===
POSTGRES_USER=svuser
POSTGRES_PASSWORD=CHANGE_ME_GENERATE_STRONG_PASSWORD
POSTGRES_DB=svtrading
DATABASE_URL=postgresql://svuser:CHANGE_ME_GENERATE_STRONG_PASSWORD@postgres:5432/svtrading
JWT_SECRET_KEY=CHANGE_ME_GENERATE_RANDOM_64_CHAR_STRING
CORS_ORIGINS=["http://localhost","http://SERVER_IP"]

# === Market Data ===
MARKET_DATA_PROVIDER=simulated

# === Upstox (fill when ready) ===
UPSTOX_ACCESS_TOKEN=
UPSTOX_CLIENT_ID=
UPSTOX_CLIENT_SECRET=
UPSTOX_REDIRECT_URI=http://localhost:8000/upstox/callback

# === Redis / Celery ===
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
ENVEOF
    echo ".env created with placeholder values."
    echo ""
    echo ">>> ACTION REQUIRED: Edit .env on the server NOW:"
    echo "    nano $REPO_DIR/.env"
    echo "    Replace POSTGRES_PASSWORD with a strong random password."
    echo "    Replace JWT_SECRET_KEY with a strong random string."
    echo "    Replace SERVER_IP with your Lightsail IP."
    echo "    Then re-run: bash $REPO_DIR/setup.sh"
    echo ""
else
    echo ".env already exists."
fi

# 6. Build and start
echo "[6/8] Building and starting containers..."
cd "$REPO_DIR"
cp docker/nginx/prod.conf docker/nginx/default.conf
docker compose -f docker-compose.prod.yml up --build -d

# 7. Wait and check
echo "[7/8] Waiting for services..."
sleep 30
docker compose -f docker-compose.prod.yml ps

# 8. Verify
echo "[8/8] Verifying deployment..."
curl -s http://localhost/api/health || echo "Backend may still be starting..."
echo ""
echo "=== Setup Complete ==="
echo "Open: http://YOUR_SERVER_IP"
echo ""
echo "Commands:"
echo "  Status:   cd $REPO_DIR && docker compose -f docker-compose.prod.yml ps"
echo "  Logs:     cd $REPO_DIR && docker compose -f docker-compose.prod.yml logs --tail=100"
echo "  Backup:   cd $REPO_DIR && docker compose -f docker-compose.prod.yml exec backup pg_dump -h postgres -U svuser -d svtrading -F c -f /backups/manual.dump"
echo "  Restore:  cd $REPO_DIR && docker compose -f docker-compose.prod.yml exec -T postgres pg_restore -U svuser -d svtrading < backups/manual.dump"
echo "  Stop:     cd $REPO_DIR && docker compose -f docker-compose.prod.yml down"
echo "  Update:   cd $REPO_DIR && git pull && docker compose -f docker-compose.prod.yml up --build -d"
echo "  Env:      cd $REPO_DIR && nano .env"
