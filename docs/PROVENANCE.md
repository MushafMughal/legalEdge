# LegalEdge — Provenance

*How this folder came to be, for a future Claude session opening `legaledge/` standalone (without the parent `AI-Technical-Interview` repo). Read this first, then `docs/SPEC.md`.*

---

## 1. Where LegalEdge came from

LegalEdge is an **inbound client-intake AI phone agent** for a law firm. It was adapted from the Traxccel **AI-Interviewer** repo's **MVP2 phone-screening** agent — an **outbound** Twilio Media Streams ⇄ Gemini Live voice bot that cold-called candidates and ran a scored screening interview.

The core insight of the port: the *voice plumbing* (Twilio Media Streams ⇄ Gemini Live audio bridge, barge-in, resampling) is identical for inbound and outbound. Only the *call direction*, the *conversation*, and the *persistence/hand-off* differ. So the plumbing was copied verbatim and everything above it was rewritten.

This folder is **self-contained** — its own venv, its own `.env`, its own single-file SQLite DB with a **relative** `DB_PATH=./legaledge.db`. It shares **no code, port, process, or database** with the interviewer; it shares only the **Twilio and Gemini credentials**. It is designed to be lifted out to its own repository root with **no code edits**.

---

## 2. Reused verbatim (do not modify these)

These two files are **byte-for-byte copies** from the screening agent and must stay that way — they are independently testable and have no LegalEdge-specific imports:

| File | Source | Role |
|------|--------|------|
| `backend/audio.py` | screening `audio.py` | mu-law 8k ⇄ PCM16 resamplers for the Twilio ⇄ Gemini bridge |
| `backend/gemini_live.py` | screening `gemini_live_phone.py` (`GeminiLivePhone`) | Gemini Live session wrapper (audio in/out, tool calls, barge-in) |

Also carried over verbatim (as patterns, not whole files):
- The `PUBLIC_URL`-derived, subpath-preserving `wss://` base logic in `config.py` (`public_ws_base`).
- The `twilio_handler.py` architecture: bounded audio queue, `_cur`/`_flush` transcript accumulation, `_run_gemini_session`, `_timeout_guard`, interrupt/barge-in via the Twilio `clear` event.

---

## 3. What was inverted or replaced (screening → LegalEdge)

| Concern | Screening agent (source) | LegalEdge (this folder) |
|---------|--------------------------|-------------------------|
| **Call direction** | **Outbound** — `twilio.rest` client `calls.create(...)` dials the candidate | **Inbound** — `POST /api/voice` Voice webhook returns `<Connect><Stream>` TwiML when a caller dials in. **No Twilio REST client, no `TWILIO_ACCOUNT_SID` needed.** |
| **Conversation** | Question-bank driven, scored screening interview | Warm, disclosure-compliant client-intake conversation (`build_intake_prompt`), **not a lawyer**, mandatory AI + not-legal-advice disclaimer |
| **Tools** | Interview scoring tools | Two silent function-calling intake tools: `submit_contact_details`, `submit_case_details` (see SPEC §4) |
| **Persistence** | Postgres + interview scheduler + signed webhook outbox | **Single-file SQLite** `intakes` table via stdlib `sqlite3` (`store.py`) — no Postgres, no scheduler, no webhook outbox |
| **External systems** | Recall.ai (MVP1), MS Graph (MVP2) | None — dropped entirely |
| **Downstream hand-off** | Scoring + webhook delivery | **LegalEdge CRM push, stubbed** (`legaledge_client.create_prospect`) — logs and returns a fake `prospect_id`; a real impl drops in behind the stable signature |

The inbound bridge otherwise runs the same lifecycle: `POST /api/voice` mints a per-call session + secret and opens an `in_call` DB row; Twilio connects the WS; the handler bridges audio; on hang-up the row moves `captured → pushed | failed`.

---

## 4. Gotchas to carry forward (these bit us; keep them fixed)

1. **Python 3.12 is required — not 3.13.** `audio.py` uses the stdlib `audioop` module, which was **removed in Python 3.13**. Build the venv with Python 3.12. **Do NOT** try to paper over this by installing `audioop-lts` — the reused code expects the real stdlib module; pin the interpreter instead.

2. **Do NOT pass `live_connect_constraints` when minting the Gemini Live session.** If you include it, the Live WebSocket closes immediately with code **1011**. Mint the session cleanly. (This rule lives inside the verbatim `gemini_live.py` — respect it if you ever touch that file.)

3. **The per-call WS secret is a PATH segment, not a query param.** The Media Stream URL is `wss://<host>/legalEdge/api/media/{session_id}/{stream_secret}` — the secret is `/{stream_secret}`, embedded in the path. It is **not** `?k=<secret>`. Rationale: a path-segment secret is not logged as a query string and survives the nginx prefix-strip hop cleanly. It is minted at runtime with `secrets.token_urlsafe` per call, lives only in the TwiML, and is verified against the in-memory session when Twilio connects — it is **never** an env var.

---

## 5. Orientation for a standalone session

If you are reading this with only the `legaledge/` folder in front of you:

- **`docs/SPEC.md` is the authoritative build spec** — every file, route, schema, env var, and the full status lifecycle are defined there. It records binding "Conflict resolved" notes where four source fragments disagreed.
- The backend serves both the `/api/*` routes **and** the built React SPA (from `frontend/dist/`). Locally it runs on `127.0.0.1:8091`; in production nginx strips the `/legalEdge/` prefix so the app sees clean paths (`/api/voice`, `/`, `/intakes`).
- To run it, see `../README.md`. For deployment at `ai.traxccel.com/legalEdge`, see SPEC §9.
- The `intakes` SQLite table (SPEC §5) is the durable record; the SPA reads it via `GET /api/intakes` and `GET /api/intakes/{id}`.
- You do **not** need the parent AI-Interviewer repo for anything — the two files that came from it (`audio.py`, `gemini_live.py`) are already copied in.
