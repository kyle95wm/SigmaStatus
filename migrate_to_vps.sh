#!/usr/bin/env bash
set -euo pipefail

###
# Configuration (edit these)
###

VPS_USER="linuxuser"
VPS_HOST="140.82.7.168"
REMOTE_DIR="~/reports-bot"

# What to sync
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"

###
# Safety checks
###

if [[ ! -f "$LOCAL_DIR/docker-compose.yml" ]]; then
  echo "❌ docker-compose.yml not found. Run this from the reports-bot root."
  exit 1
fi

if [[ ! -f "$LOCAL_DIR/.env" ]]; then
  echo "⚠️  .env not found locally."
  echo "   This script expects you to copy your .env to the VPS."
  read -rp "Continue anyway? (y/N): " yn
  [[ "$yn" =~ ^[Yy]$ ]] || exit 1
fi

echo "================================================="
echo " Migrating reports-bot to VPS"
echo "================================================="
echo " Local dir : $LOCAL_DIR"
echo " Remote    : $VPS_USER@$VPS_HOST:$REMOTE_DIR"
echo
read -rp "Proceed with rsync? (y/N): " yn
[[ "$yn" =~ ^[Yy]$ ]] || exit 0

###
# Sync files
###

echo
echo "➡️  Syncing project files..."

rsync -av --progress \
  --exclude "__pycache__/" \
  --exclude "*.pyc" \
  --exclude ".git/" \
  "$LOCAL_DIR/" \
  "$VPS_USER@$VPS_HOST:$REMOTE_DIR/"

echo "✅ Files synced."

###
# Remote steps
###

echo
echo "➡️  Running remote Docker steps..."

ssh "$VPS_USER@$VPS_HOST" <<EOF
set -e

cd $REMOTE_DIR

echo "Stopping existing containers (if any)..."
docker compose down || true

echo "Building and starting containers..."
docker compose up -d --build

echo
echo "Container status:"
docker compose ps
EOF

echo
echo "================================================="
echo " Migration complete"
echo "================================================="
echo
echo "Next steps:"
echo "  - ssh $VPS_USER@$VPS_HOST"
echo "  - docker compose logs -f --tail=200"
echo
