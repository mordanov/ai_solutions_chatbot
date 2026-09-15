#!/usr/bin/env bash
# Run once on the VPS after vps-setup.sh and after the app is running.
# Configures nginx reverse proxy for Streamlit and gets a Let's Encrypt cert.
set -euo pipefail

DOMAIN=chatbot.dqaifactory.ru
EMAIL=${CERT_EMAIL:?Set CERT_EMAIL=you@example.com before running this script}

# ── Nginx config ─────────────────────────────────────────────────────
cat > /etc/nginx/sites-available/${DOMAIN} << 'NGINX'
server {
    listen 80;
    server_name chatbot.dqaifactory.ru;

    # Streamlit UI
    location / {
        proxy_pass         http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/${DOMAIN} /etc/nginx/sites-enabled/${DOMAIN}
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

# ── TLS cert via Let's Encrypt ────────────────────────────────────────
certbot --nginx -d ${DOMAIN} --non-interactive --agree-tos -m "${EMAIL}"

echo "HTTPS setup complete. Visit https://${DOMAIN}"
