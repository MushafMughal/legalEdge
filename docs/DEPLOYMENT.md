# LegalEdge — Deployment (`ai.traxccel.com/legalEdge`)

Deploy the intake agent on the same Linux server as the AI-Interviewer (which runs
at `/ai-interviewer`, backend on `127.0.0.1:8090`). LegalEdge is its **own** process
on `127.0.0.1:8091` with its **own** SQLite file — nothing is shared but the host and
the Twilio/Gemini credentials.

> The demo frontend is **server-rendered HTML** — **no `npm` build is needed**. (The
> React app in `frontend/` is a later phase; ignore it for this deploy.)

---

## 1. Clone

```bash
cd /opt
git clone https://github.com/MushafMughal/legalEdge.git legaledge
```

## 2. Backend (Python **3.11 or 3.12** — not 3.13)

`backend/audio.py` uses the stdlib `audioop` module, removed in 3.13. Do **not**
install `audioop-lts`; use a real 3.11/3.12 interpreter.

```bash
cd /opt/legaledge/backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
nano .env
```

Fill in `.env`:

| Key | Value |
|-----|-------|
| `GEMINI_API_KEY` | reuse the interviewer's Gemini key (Live-model access) |
| `TWILIO_AUTH_TOKEN` | your Twilio Auth Token — **set this** (enables the `X-Twilio-Signature` check on `/api/voice`) |
| `TWILIO_INBOUND_NUMBER` | `+17276070459` |
| `PUBLIC_URL` | `https://ai.traxccel.com/legalEdge` |
| `DASHBOARD_API_KEY` | optional; a random string to gate the JSON `/api/intakes` endpoints (the HTML dashboard is gated at nginx instead — see step 4) |
| `FIRM_NAME` / `AGENT_NAME` | optional; the firm + agent name the AI uses on the call |

(`GEMINI_LIVE_MODEL`, `GEMINI_VOICE`, `INTAKE_TIMEZONE`, and `DB_PATH` have sane
defaults; `LEGALEDGE_API_*` are placeholders for the CRM push, which is stubbed.)

## 3. systemd — `/etc/systemd/system/legaledge.service`

```ini
[Unit]
Description=LegalEdge Intake Agent
After=network.target

[Service]
WorkingDirectory=/opt/legaledge/backend
ExecStart=/opt/legaledge/backend/.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8091
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now legaledge
sudo journalctl -u legaledge -f          # watch for "[legaledge] database ready"
```

The app creates `legaledge.db` (SQLite, WAL) on first start.

## 4. nginx — subpath `/legalEdge/`

The `map $http_upgrade $connection_upgrade { ... }` block already exists in `http { }`
(from the interviewer). Add these **three** locations inside the same `server { }` that
serves `ai.traxccel.com`. Order matters: the two Twilio endpoints must stay **open**
(Twilio can't send credentials, and the media stream is a WebSocket), so they are
separate from the password-protected dashboard.

```nginx
# Twilio inbound webhook — MUST stay open (protected by the Twilio signature).
location = /legalEdge/api/voice {
    proxy_pass http://127.0.0.1:8091/api/voice;
    proxy_set_header Host $host;
}

# Twilio media stream (WebSocket) — MUST stay open (protected by the per-call secret).
location /legalEdge/api/media/ {
    proxy_pass http://127.0.0.1:8091/api/media/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_set_header Host $host;
    proxy_read_timeout 3600s;
}

# Everything else — the intake dashboard + report pages (client PII).
location /legalEdge/ {
    proxy_pass http://127.0.0.1:8091/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_set_header Host $host;
    proxy_read_timeout 3600s;

    # The report pages show client PII. For anything beyond a quick internal demo,
    # password-protect them:
    #   sudo apt install apache2-utils
    #   sudo htpasswd -c /etc/nginx/.legaledge_htpasswd traxccel
    # then uncomment:
    # auth_basic "LegalEdge";
    # auth_basic_user_file /etc/nginx/.legaledge_htpasswd;
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

The trailing-slash `proxy_pass` on `/legalEdge/` strips the prefix, so the backend
sees clean paths (`/`, `/intake/{id}`, `/api/...`). The per-call WebSocket secret is a
path segment, so it survives this hop unchanged.

## 5. Twilio Console

Phone Numbers → Manage → Active numbers → **+1 727 607 0459** → Voice Configuration →
**A CALL COMES IN** → **Webhook**, method **POST**, URL:

```
https://ai.traxccel.com/legalEdge/api/voice
```

(While the Twilio account is in trial mode, add the tester's number as a **Verified
Caller ID** first.)

## 6. Verify + demo

```bash
curl https://ai.traxccel.com/legalEdge/api/health
# {"ok":true,"model":"gemini-3.1-flash-live-preview","voice":"Puck",
#  "gemini_configured":true,"firm":"...","db":"ok"}
```

Then **Zoha (+1 469 690 2471)** dials **+1 727 607 0459** → the agent answers, gives the
recording + not-legal-advice disclosures, and runs the intake → on hang-up the row goes
`in_call → captured → pushed`. Open **https://ai.traxccel.com/legalEdge/** → the intakes
list → click her intake → the full branded report.

## Updating later

```bash
cd /opt/legaledge && git pull && sudo systemctl restart legaledge
```

---

*Reference: [`SPEC.md` §9](SPEC.md) documents the same deployment shape as part of the
full build spec. When the real LegalEdge CRM API is ready, it drops into
`backend/legaledge_client.py` (one function) — no other change.*
