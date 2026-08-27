#!/bin/bash
# ==============================================================================
# CryptoArena 50X - 1-Click 24/7 Cloud Deployment Script
# Supports: Ubuntu 20.04/22.04/24.04, Debian 11/12 on Oracle/AWS/GCP/DigitalOcean
# ==============================================================================

set -e

echo "=========================================================="
echo "🚀 Setting up CryptoArena 50X 24/7 Cloud Engine..."
echo "=========================================================="

# 1. Update system packages
echo "📦 Updating system packages..."
sudo apt-get update -y
sudo apt-get install -y curl git ufw

# 2. Install Docker if not installed
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker Engine..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
else
    echo "✔ Docker already installed."
fi

# 3. Install Docker Compose if not installed
if ! docker compose version &> /dev/null; then
    echo "🐳 Installing Docker Compose plugin..."
    sudo apt-get install -y docker-compose-plugin
fi

# 4. Open firewall port 8088 for the Web Dashboard
echo "🛡️ Configuring firewall rules for port 8088..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 8088/tcp || true
fi

# 5. Build and launch 24/7 container
echo "⚙️ Building and launching CryptoArena 50X in background..."
docker compose down || true
docker compose up -d --build

# 6. Retrieve public IP
PUBLIC_IP=$(curl -s ifconfig.me || curl -s icanhazip.com || echo "YOUR_SERVER_IP")

echo "=========================================================="
echo "✅ CryptoArena 50X is now running 24/7 in the background!"
echo "• The bots will continue trading even when your PC is off."
echo "• Web Dashboard URL: http://${PUBLIC_IP}:8088"
echo "• Logs Command: docker compose logs -f"
echo "• Stop Command: docker compose down"
echo "=========================================================="
