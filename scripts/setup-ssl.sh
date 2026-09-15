#!/usr/bin/env bash
# Run once on the VPS after vps-setup.sh and after the app is running.
# Obtains Let's Encrypt certs for both domains and restarts nginx with HTTPS.
set -euo pipefail

REMOTE_DIR=/opt/chatbot

# Read domains from .env
# shellcheck source=/dev/null
set -a; source "${REMOTE_DIR}/.env"; set +a

: "${CHATBOT_DOMAIN:?Set CHATBOT_DOMAIN in .env}"
: "${MAIL_DOMAIN:?Set MAIL_DOMAIN in .env}"
: "${CERT_EMAIL:?Run as: sudo CERT_EMAIL=you@example.com bash setup-ssl.sh}"

cd "${REMOTE_DIR}"

# Stop nginx to free port 80 for certbot standalone challenge
docker compose stop nginx

# Obtain certs (separate cert per domain so each server block gets its own)
certbot certonly --standalone --non-interactive --agree-tos \
  -m "${CERT_EMAIL}" -d "${CHATBOT_DOMAIN}"

certbot certonly --standalone --non-interactive --agree-tos \
  -m "${CERT_EMAIL}" -d "${MAIL_DOMAIN}"

# Register pre/post hooks so auto-renewal also stops/starts nginx
mkdir -p /etc/letsencrypt/renewal-hooks/pre /etc/letsencrypt/renewal-hooks/post

cat > /etc/letsencrypt/renewal-hooks/pre/stop-nginx.sh << EOF
#!/bin/sh
docker compose -f ${REMOTE_DIR}/docker-compose.yml stop nginx
EOF

cat > /etc/letsencrypt/renewal-hooks/post/start-nginx.sh << EOF
#!/bin/sh
docker compose -f ${REMOTE_DIR}/docker-compose.yml start nginx
EOF

chmod +x /etc/letsencrypt/renewal-hooks/pre/stop-nginx.sh \
         /etc/letsencrypt/renewal-hooks/post/start-nginx.sh

# Start nginx — docker-entrypoint.sh sees the certs and loads the HTTPS config
docker compose start nginx

echo "HTTPS setup complete."
echo "  Chatbot: https://${CHATBOT_DOMAIN}"
echo "  Mail:    https://${MAIL_DOMAIN}"
