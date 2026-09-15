# VPS Deployment Guide

This guide walks through deploying CityPark Chatbot on a clean Ubuntu VPS from scratch.

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Ubuntu 22.04+ VPS | Root SSH access required for initial setup |
| Domain name | `chatbot.dqaifactory.ru` (or your own) pointed at the VPS IP |
| OpenAI API key | For LLM and embeddings |
| Local machine | macOS/Linux with `ssh`, `rsync`, and `git` installed |

---

## Step 1 — One-time server setup (run as root)

SSH into the VPS as root and run the setup script:

```bash
ssh root@<VPS_IP>
```

Then on the server:

```bash
curl -fsSL https://raw.githubusercontent.com/<your-org>/chatbot/main/scripts/vps-setup.sh \
  | bash
```

Or copy and run the script manually:

```bash
# From your local machine
scp scripts/vps-setup.sh root@<VPS_IP>:/tmp/
ssh root@<VPS_IP> bash /tmp/vps-setup.sh
```

**What the script does:**

- Installs Docker CE and the `docker compose` plugin
- Installs Certbot (Let's Encrypt) — nginx runs inside Docker, not on the host
- Creates a `deploy` user (sudo + docker groups)
- Copies root's `authorized_keys` to `deploy` so the same SSH key works
- Creates `/opt/chatbot` owned by `deploy`
- Configures UFW firewall: SSH and nginx (80/443) open; ports 8000 and 8501 blocked

After the script finishes, verify you can log in as the deploy user:

```bash
ssh deploy@<VPS_IP>
```

---

## Step 2 — Create the `.env` file on the VPS

There is no git clone on the VPS — `deploy.sh` uses `rsync` and deliberately
excludes `.env`. The `/opt/chatbot` directory was created by `vps-setup.sh` in
Step 1, so just SSH in and write the file there directly. Do this **before**
running `deploy.sh` — the script will exit with an error if `.env` is missing.

```bash
ssh deploy@<VPS_IP>
cat > /opt/chatbot/.env << 'EOF'
OPENAI_API_KEY=sk-...

# Domains — nginx reads these to build its virtual-host config
CHATBOT_DOMAIN=chatbot.dqaifactory.ru
MAIL_DOMAIN=chatmail.dqaifactory.ru

# Database
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/chatbot

# Milvus
MILVUS_URI=http://milvus:19530

# Admin API
ADMIN_TOKEN=change-me-to-something-secure

# SMTP — Mailpit is included in docker compose for dev; replace for production
SMTP_HOST=mailpit
SMTP_PORT=1025
SMTP_FROM=chatbot@parking.local
ADMIN_EMAIL=admin@parking.local

# Reservation storage
RESERVATIONS_FILE_PATH=data/reservations.txt
APPROVAL_TIMEOUT_SECONDS=300
EOF
```

> **Production SMTP**: replace `SMTP_HOST=mailpit` / `SMTP_PORT=1025` with your real
> SMTP provider credentials and update `SMTP_FROM` / `ADMIN_EMAIL` accordingly.

---

## Step 3 — First deploy

From your **local machine**, run the deploy script from the project root:

```bash
VPS_HOST=<VPS_IP> ./scripts/deploy.sh
```

This will:
1. `rsync` the project to `/opt/chatbot` on the VPS (excludes `.env`, `data/`, `.git/`)
2. SSH in and run `docker compose up -d --build`

Wait for all containers to reach healthy status:

```bash
ssh deploy@<VPS_IP> "docker compose -f /opt/chatbot/docker-compose.yml ps"
```

Expected output — all services `Up (healthy)`:

```
chatbot-api-1       ... Up (healthy)
chatbot-etcd-1      ... Up (healthy)
chatbot-mailhog-1   ... Up (healthy)
chatbot-milvus-1    ... Up (healthy)
chatbot-minio-1     ... Up (healthy)
chatbot-postgres-1  ... Up (healthy)
chatbot-ui-1        ... Up
```

---

## Step 4 — Seed the database and knowledge base

Run these once after the first successful deploy:

```bash
ssh deploy@<VPS_IP> bash << 'EOF'
  cd /opt/chatbot
  # Initialise PostgreSQL schema and seed parking data
  docker compose exec api python scripts/init_db.py --seed
  # Index parking knowledge into Milvus
  docker compose exec api python scripts/ingest.py
EOF
```

---

## Step 5 — Set up HTTPS (run once on the VPS)

Make sure both domain DNS records point at the VPS IP before this step.

```bash
ssh deploy@<VPS_IP>
sudo CERT_EMAIL=you@example.com bash /opt/chatbot/scripts/setup-ssl.sh
```

**What the script does:**

1. Reads `CHATBOT_DOMAIN` and `MAIL_DOMAIN` from `/opt/chatbot/.env`
2. Stops the nginx container to free port 80 for the ACME challenge
3. Runs `certbot certonly --standalone` for each domain (separate cert per domain)
4. Installs pre/post renewal hooks so `certbot renew` automatically stops/starts nginx
5. Restarts nginx — the entrypoint detects the certs and switches to the HTTPS config

After this step:

- Chatbot UI: `https://chatbot.dqaifactory.ru`
- Mailpit web:  `https://chatmail.dqaifactory.ru`

> **Note:** `certbot` must be installed on the host (`vps-setup.sh` does this).
> The host nginx is intentionally not installed — nginx runs inside Docker.

---

## Subsequent deploys

Any push to `main` triggers automatic deployment via GitHub Actions (see
`.github/workflows/ci.yml`). The CD job runs after lint + tests pass.

For a manual deploy:

```bash
VPS_HOST=chatbot.dqaifactory.ru ./scripts/deploy.sh
```

---

## GitHub Actions secrets

The CD pipeline requires these repository secrets (Settings → Secrets → Actions):

| Secret | Value |
|--------|-------|
| `SSH_PRIVATE_KEY` | Private key whose public half is in `deploy`'s `authorized_keys` |
| `VPS_HOST` | VPS IP or hostname (`chatbot.dqaifactory.ru`) |
| `VPS_USER` | `deploy` |

---

## Firewall summary

| Port | Protocol | Access | Purpose |
|------|----------|--------|---------|
| 22 | TCP | Public | SSH |
| 80 | TCP | Public | nginx — HTTP (redirects to HTTPS after Step 5) |
| 443 | TCP | Public | nginx — HTTPS reverse proxy |
| 8000 | TCP | Blocked | FastAPI (no host binding; internal only) |
| 8501 | TCP | Blocked | Streamlit (no host binding; internal only) |
| 1025 | TCP | Blocked | Mailpit SMTP (internal only) |
| 5433 | TCP | Blocked | PostgreSQL (internal only) |

All services are reachable only through nginx. UFW blocks every port except 22, 80, and 443.

---

## Troubleshooting

**Containers not starting**
```bash
ssh deploy@<VPS_IP> "docker compose -f /opt/chatbot/docker-compose.yml logs --tail=50"
```

**`.env` missing on VPS**
```bash
scp .env deploy@<VPS_IP>:/opt/chatbot/.env
```

**Certificate renewal failure**
```bash
sudo certbot renew --dry-run
```

**Out of disk space**
```bash
docker system prune -f          # removes stopped containers and dangling images
docker image prune -af          # removes all unused images
docker builder prune -af        # clears build cache
```
