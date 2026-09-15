#!/usr/bin/env bash
# Deploy to VPS. Run from the project root.
# Usage: VPS_HOST=1.2.3.4 ./scripts/deploy.sh
set -euo pipefail

VPS_HOST=${VPS_HOST:-chatbot.dqaifactory.ru}
VPS_USER=${VPS_USER:-deploy}
REMOTE_DIR=/opt/chatbot

echo "Deploying to ${VPS_USER}@${VPS_HOST}:${REMOTE_DIR} ..."

rsync -az --delete \
  --exclude '.git/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.env' \
  --exclude 'data/' \
  --exclude '.venv/' \
  --exclude 'node_modules/' \
  ./ "${VPS_USER}@${VPS_HOST}:${REMOTE_DIR}/"

ssh "${VPS_USER}@${VPS_HOST}" bash << EOF
  set -euo pipefail
  cd ${REMOTE_DIR}

  if [ ! -f .env ]; then
    echo "ERROR: .env missing on VPS. Copy it first: scp .env ${VPS_USER}@${VPS_HOST}:${REMOTE_DIR}/.env"
    exit 1
  fi

  docker compose pull --quiet --ignore-pull-failures 2>/dev/null || true
  docker compose up -d --build --remove-orphans
  docker compose ps
EOF

echo "Deploy complete."
