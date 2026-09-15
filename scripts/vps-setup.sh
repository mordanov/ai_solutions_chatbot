#!/usr/bin/env bash
# Run once on a fresh Ubuntu VPS as root.
set -euo pipefail

# ── Docker ──────────────────────────────────────────────────────────
apt-get update -qq
apt-get install -y ca-certificates curl gnupg

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update -qq
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable --now docker

# ── Nginx + Certbot ─────────────────────────────────────────────────
apt-get install -y nginx certbot python3-certbot-nginx

# ── Deploy user ──────────────────────────────────────────────────────
useradd -m -s /bin/bash deploy || echo "User 'deploy' already exists."
usermod -aG docker deploy  # run docker without sudo

# Passwordless sudo — needed by setup-ssl.sh (nginx config writes + certbot)
echo "deploy ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/deploy
chmod 440 /etc/sudoers.d/deploy

# Copy root's authorized_keys so the same SSH key works for deploy.
if [ -f /root/.ssh/authorized_keys ]; then
  install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
  install -m 600 -o deploy -g deploy /root/.ssh/authorized_keys /home/deploy/.ssh/authorized_keys
  echo "Copied root authorized_keys → deploy user."
else
  install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
  echo "No root authorized_keys found. Add deploy's public key manually:"
  echo "  echo '<pubkey>' >> /home/deploy/.ssh/authorized_keys"
fi

# App directory owned by deploy so rsync works without sudo.
install -d -m 755 -o deploy -g deploy /opt/chatbot

# ── Firewall ─────────────────────────────────────────────────────────
# Only nginx (80/443) and SSH are public; everything else is internal.
ufw --force enable
ufw allow ssh
ufw allow 'Nginx Full'
ufw deny 8000/tcp   # API (no longer has a host port, kept for safety)
ufw deny 8501/tcp   # Streamlit (no longer has a host port, kept for safety)
ufw deny 5433/tcp   # PostgreSQL
ufw deny 1025/tcp   # Mailpit SMTP

echo "VPS setup complete. Deploy with user 'deploy'."
