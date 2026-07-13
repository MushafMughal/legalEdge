# LegalEdge — Client Intake

*Inbound client-intake AI phone agent for a law firm. A caller dials the firm's Twilio number; LegalEdge answers, runs a warm, disclosure-compliant intake conversation over Gemini Live, captures contact + case details, persists each call to SQLite, and hands the prospect to the LegalEdge CRM (stubbed). For the demo, the backend serves simple **HTML report pages** — open a link to view a captured intake. A richer React SPA in `frontend/` is the later, full-frontend phase (not served yet).*

Built by adapting the Traxccel AI-Interviewer MVP2 phone-screening agent to **inbound**. See [`docs/PROVENANCE.md`](docs/PROVENANCE.md) for the full story and [`docs/SPEC.md`](docs/SPEC.md) for the authoritative build spec.

---

## Prerequisites

- **Python 3.11 or 3.12** — **not 3.13**. `backend/audio.py` uses the stdlib `audioop` module, which was removed in 3.13. Do **not** install `audioop-lts`; use a real 3.11/3.12 interpreter.
- A **Gemini API key** (with Live model access) and a **Twilio** account with a dedicated inbound number.
- **Node.js 20+** is needed only for the *later* React frontend (`frontend/`), **not** for the demo.

---

## Run locally

### 1. Backend

```bash
cd backend

# Create a Python 3.12 venv (adjust the launcher for your OS)
python3.12 -m venv .venv
# Windows:  py -3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt

# Configure
cp .env.example .env               # Windows: copy .env.example .env
# then edit .env and fill in at least:
#   GEMINI_API_KEY=...             # your Gemini key
#   TWILIO_INBOUND_NUMBER=...      # the DID this agent answers on
#   TWILIO_AUTH_TOKEN=...          # optional; enables X-Twilio-Signature check on /api/voice
#   PUBLIC_URL=https://ai.traxccel.com/legalEdge   # or your tunnel URL for testing
# (Gemini model/voice, firm identity, DB_PATH, and the CRM stub creds have sane defaults.)

# Run
uvicorn main:app --port 8091
```

The backend listens on `http://127.0.0.1:8091`. It creates `legaledge.db` (SQLite, WAL) on first start via the lifespan hook. Verify:

```bash
curl http://127.0.0.1:8091/api/health
# {"ok":true,"model":"gemini-3.1-flash-live-preview","voice":"Puck",
#  "gemini_configured":true,"firm":"Wexler & Associates","db":"ok"}
```

### 2. Viewing intakes (demo frontend — no build needed)

The backend serves simple, branded HTML pages directly — this is the demo frontend:

- `http://127.0.0.1:8091/` — the **intakes list** (every captured call, newest first).
- `http://127.0.0.1:8091/intake/{id}` — the full **intake report** (contact, matter, transcript, push status).

Open a link to see a captured intake. No `npm` step is required for the demo.

### Later: the full React frontend

`frontend/` holds a React 19 + Vite 6 + Tailwind SPA (landing + sortable dashboard + detail) that reads the JSON `GET /api/intakes` / `GET /api/intakes/{id}` endpoints. It's the next-phase UI and is **not** served yet. To work on it: `cd frontend && npm install && npm run build` (Vite base `/legalEdge/`).

---

## How inbound testing works

LegalEdge answers real phone calls — there is no synthetic call trigger. To test end-to-end:

1. Expose the backend publicly (deployed at `ai.traxccel.com/legalEdge`, or a tunnel like ngrok/cloudflared pointing at `127.0.0.1:8091` during local testing) and set `PUBLIC_URL` to that origin.
2. In the **Twilio Console → Phone Numbers → Active numbers → your inbound number → Voice Configuration → A CALL COMES IN**, set the handler to **Webhook**, method **POST**, URL `https://<your-public-origin>/api/voice`.
3. **Dial the Twilio number** from a phone. Twilio POSTs `From/To/CallSid` to `/api/voice`, which opens an `in_call` intake row, mints a per-call WS secret, and returns `<Connect><Stream>` TwiML. Twilio opens the Media Stream WebSocket; the agent greets you, gives the recording + AI/not-legal-advice disclosures, and runs the intake.
4. Hang up. The row moves `in_call → captured` (contact + case + transcript persisted), then `→ pushed` once the CRM stub returns (or `→ failed` on error). Refresh `/intakes` to see it.

While the Twilio account is in trial mode, the caller's number must be added as a **Verified Caller ID** on the account; then that phone can call the number repeatedly — each call is a fresh `CallSid` row, no code or Twilio change per test.

> Note: the per-call WebSocket secret is a **path segment** (`.../api/media/{session_id}/{secret}`), not a query param, and is minted at runtime — never set it in `.env`.

---

## Deployment

For production deployment at **`https://ai.traxccel.com/legalEdge`** — the loopback uvicorn on `127.0.0.1:8091`, the systemd unit, the nginx `/legalEdge/` subpath reverse proxy (with WebSocket upgrade and prefix stripping), the Vite `base` path, and the Twilio inbound-webhook wiring — see **[`docs/SPEC.md` section 9](docs/SPEC.md)**.

---

## Layout

```
legaledge/
├── backend/         FastAPI app (main.py), Gemini Live bridge, SQLite store, intake tools
│   └── views.py     simple branded HTML report pages — the demo frontend (/ and /intake/{id})
├── frontend/        React 19 + Vite 6 + Tailwind SPA — the later, full-frontend phase (not served yet)
└── docs/            SPEC.md (authoritative build spec) · PROVENANCE.md (adaptation history)
```
