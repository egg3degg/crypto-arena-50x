#!/bin/bash
# ==============================================================================
# CryptoArena 50X - Autonomous Auto-Deployment & Continuous Sync Engine
# Automatically checks GitHub for new updates, pulls them, fixes imports,
# and hot-reloads the Docker container with ZERO downtime.
# ==============================================================================

REPO_DIR="$HOME/crypto-arena-50x"
BRANCH="main"
CHECK_INTERVAL=60 # seconds

echo "🚀 CryptoArena 50X Auto-Deployment Daemon Started"
echo "📡 Monitoring GitHub repository: egg3degg/crypto-arena-50x (every ${CHECK_INTERVAL}s)"

cd "$REPO_DIR" || exit 1

while true; do
    # Fetch latest remote changes without merging
    git fetch origin "$BRANCH" > /dev/null 2>&1

    # Check if local is behind remote
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse "origin/$BRANCH")

    if [ "$LOCAL" != "$REMOTE" ]; then
        echo "============================================================"
        echo "🔔 [$(date)] New update detected on GitHub! Auto-deploying..."
        echo "============================================================"

        # Pull latest code
        git reset --hard "origin/$BRANCH"
        git pull origin "$BRANCH"

        # Universal import sanitizer
        python3 -c "
import glob, re
for f in glob.glob('$REPO_DIR/**/*.py', recursive=True):
    with open(f, 'r') as fp: content = fp.read()
    content = re.sub(r'from \.\.([a-zA-Z_]+)', r'from \1', content)
    content = re.sub(r'from \.(database|simulator|market_feed)', r'from core.\1', content)
    with open(f, 'w') as fp: fp.write(content)
"

        # Rebuild and reload container seamlessly
        sudo docker compose up -d --build

        echo "✔ [$(date)] Successfully auto-deployed new release ($REMOTE)!"
        echo "============================================================"
    fi

    sleep "$CHECK_INTERVAL"
done
