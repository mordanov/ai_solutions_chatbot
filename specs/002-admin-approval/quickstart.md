# Quickstart: Admin Reservation Approval

**Branch**: `002-admin-approval` | **Date**: 2026-08-11

## Prerequisites

- Docker + docker-compose installed
- Stage 1 working (existing `docker-compose.yml` services healthy)
- `.env` file with `OPENAI_API_KEY` and `ADMIN_TOKEN` set

## New Environment Variables

Add to `.env`:

```bash
# SMTP / MailHog
SMTP_HOST=mailhog
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=chatbot@parking.local
ADMIN_EMAIL=admin@parking.local

# Approval timeout (seconds)
APPROVAL_TIMEOUT_SECONDS=300
```

For local development outside Docker, set `SMTP_HOST=localhost`.

## Start the Stack

```bash
docker-compose up -d --build
```

MailHog web UI is available at `http://localhost:8025`.

## End-to-End Demo Flow

### Step 1 — User submits a reservation

Open the Streamlit UI at `http://localhost:8501` and chat:

```
User: I'd like to make a reservation
User: First name: Alice Surname: Smith Licence plate: ABC123
      Start date/time: 15.08.2026 10:00 End date/time: 16.08.2026 10:00
```

The bot replies:
> Your reservation request has been submitted for admin approval. You'll be notified once a decision is made.

### Step 2 — Admin receives email

Open `http://localhost:8025` (MailHog). The inbox shows a new email:

```
Subject: [Parking Reservation] New request from Alice Smith — <request_id>

Reservation details:
  Name:   Alice Smith
  Plate:  ABC123
  From:   15.08.2026 10:00
  To:     16.08.2026 10:00

To APPROVE:
  curl -X POST http://localhost:8000/admin/reservation/<request_id>/approve \
       -H "Authorization: Bearer <your_admin_token>"

To REJECT:
  curl -X POST http://localhost:8000/admin/reservation/<request_id>/reject \
       -H "Authorization: Bearer <your_admin_token>" \
       -H "Content-Type: application/json" \
       -d '{"reason": "No spaces available on that date"}'
```

### Step 3 — Admin approves

Copy the approve command from the email and run it in a terminal:

```bash
curl -X POST http://localhost:8000/admin/reservation/<request_id>/approve \
     -H "Authorization: Bearer changeme"
# HTTP 204 No Content
```

### Step 4 — User receives the decision

In the Streamlit chat, send any follow-up message (e.g., "What are the parking rates?"). The bot first delivers:

> ✅ Your reservation has been approved!  
> Name: Alice Smith | Plate: ABC123  
> From: 15.08.2026 10:00 → To: 16.08.2026 10:00

Then answers the follow-up query normally.

## Testing Rejection

Repeat the flow but use the reject endpoint instead:

```bash
curl -X POST http://localhost:8000/admin/reservation/<request_id>/reject \
     -H "Authorization: Bearer changeme" \
     -H "Content-Type: application/json" \
     -d '{"reason": "No availability on requested dates"}'
```

The user's next message will receive:

> ❌ Your reservation was not approved.  
> Reason: No availability on requested dates

## Testing Timeout

Set `APPROVAL_TIMEOUT_SECONDS=10` in `.env` and restart the API container. After submitting a reservation, wait 10 seconds without acting as admin, then send any message in chat. The bot replies:

> Your reservation request timed out. Please resubmit if you'd still like to book.

## Running Tests

```bash
docker-compose exec api pytest tests/unit/test_approval_*.py -v
# or locally:
pytest tests/unit/test_approval_*.py -v
```
