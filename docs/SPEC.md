# LegalEdge — Authoritative Build Spec

*Inbound client-intake AI phone agent. A standalone Traxccel product, adapted from the AI-Interviewer MVP2 phone-screening path.*

> This document is the single source of truth. Where the four source fragments disagreed, the resolutions are recorded inline in **Conflict resolved** notes and are binding.

---

## 1. Overview

LegalEdge is a self-contained inbound voice agent that answers a law firm's prospective-client calls on a dedicated Twilio number, bridges Twilio Media Streams (mu-law 8k) to Gemini Live for a warm, disclosure-compliant intake conversation, captures contact and case details through two silent function-calling tools, persists each call to a single-file SQLite `intakes` table, and hands the captured prospect off to the LegalEdge CRM (stubbed for now). The same FastAPI process also serves a thin React monitoring SPA (landing, intakes dashboard, intake detail). It runs as its own systemd process on `127.0.0.1:8091` behind nginx at the `/legalEdge` subpath, reusing the interviewer's proven audio bridge and Gemini Live wrapper **verbatim**, sharing only Twilio and Gemini credentials with the interviewer — no shared code, port, database, or process.

---

## 2. File tree — `legaledge/`

```
legaledge/
├── backend/
│   ├── main.py                 # FastAPI app, lifespan (init DB), routes, static SPA mount
│   ├── config.py               # Env-backed Settings singleton + public_ws_base
│   ├── audio.py                # VERBATIM copy of screening audio.py (mu-law↔PCM resamplers)
│   ├── gemini_live.py          # VERBATIM copy of gemini_live_phone.py (GeminiLivePhone)
│   ├── twilio_handler.py       # TwilioPhoneHandler: per-call bridge + end-of-call persistence
│   ├── prompts.py              # build_intake_prompt(...)
│   ├── intake_tools.py         # submit_contact_details_tool(), submit_case_details_tool()
│   ├── store.py                # stdlib sqlite3 persistence (schema, save/update/list/get)
│   ├── legaledge_client.py     # create_prospect(...) CRM stub
│   ├── models.py               # Pydantic response models + TypedDicts
│   ├── requirements.txt        # Pinned deps (Python 3.12)
│   ├── .env.example            # Documented env template
│   └── legaledge.db            # SQLite file (runtime, gitignored)
├── frontend/
│   ├── index.html              # <title>, Fraunces+Inter fonts link, favicon = LegalEdge mark
│   ├── package.json
│   ├── vite.config.ts          # base: '/legalEdge/'
│   ├── tsconfig.json
│   ├── src/
│   │   ├── main.tsx            # createRoot → <App/>, StrictMode, import './index.css'
│   │   ├── index.css          # @theme tokens (Statute palette) + serif/sans wiring
│   │   ├── App.tsx            # <BrowserRouter basename> + <Routes>
│   │   ├── lib/
│   │   │   ├── api.ts          # apiBase (reused) + intake client fns + types
│   │   │   ├── brand.ts        # logo/mark exports + name/phone constants
│   │   │   └── format.ts       # phone, date, practiceArea label helpers
│   │   ├── assets/
│   │   │   ├── legaledge-logo.png
│   │   │   └── legaledge-mark.png
│   │   ├── components/
│   │   │   ├── layout/{AppShell,Navbar,Footer}.tsx
│   │   │   ├── ui/{StatusBadge,PracticeAreaTag,DataTable,Toolbar,EmptyState,Spinner,ErrorBanner}.tsx
│   │   │   └── intake/{ContactCard,CaseCard,TranscriptPanel,PushStatusCard}.tsx
│   │   └── pages/{LandingPage,IntakesPage,IntakeDetailPage,NotFoundPage}.tsx
│   └── dist/                   # built SPA, served by the backend
├── docs/
│   ├── SPEC.md                 # this file
│   └── PROVENANCE.md
└── README.md
```

**Self-containment:** the folder has its own venv, `.env`, SQLite file, and relative `DB_PATH=./legaledge.db`, so it can be relocated to its own repo with no code edits.

---

## 3. Backend files — responsibility + interface

### 3.1 `config.py`

Mirrors the screening `Settings` pattern (dotenv load of `backend/.env` then root `.env`), trimmed to inbound needs.

```python
class Settings:
    GEMINI_API_KEY: str
    GEMINI_LIVE_MODEL: str        # default "gemini-3.1-flash-live-preview"
    GEMINI_VOICE: str             # default "Puck"

    TWILIO_INBOUND_NUMBER: str    # the firm's inbound DID this agent answers on
    TWILIO_AUTH_TOKEN: str        # optional; enables X-Twilio-Signature check on /api/voice

    PUBLIC_URL: str               # e.g. https://ai.traxccel.com/legalEdge  (rstrip '/')
    PUBLIC_DOMAIN: str            # optional host[/path] override for the wss base (no scheme)
    SUBPATH: str                  # default "/legalEdge"

    FIRM_NAME: str                # default "Wexler & Associates"
    AGENT_NAME: str               # default "Jordan"
    INTAKE_TIMEZONE: str          # default "America/New_York"

    DB_PATH: str                  # default "./legaledge.db"

    DASHBOARD_API_KEY: str        # optional; if set, gates GET /api/intakes* via X-API-Key

    LEGALEDGE_API_BASE: str       # stub target (echoed, unused by stub)
    LEGALEDGE_API_KEY: str        # stub credential (unused by stub)

    def require_gemini(self) -> None: ...
    @property
    def public_ws_base(self) -> str:
        # wss://host[/subpath]. Use PUBLIC_DOMAIN if set, else swap https→wss on
        # PUBLIC_URL, preserving the /legalEdge subpath. Copied verbatim from the
        # screening config.py public_ws_base logic.
```

> **Conflict resolved (env names):** Fragment A's `SQLITE_PATH` → **`DB_PATH`** (Fragment D). Fragment A's `TWILIO_PHONE_NUMBER` → **`TWILIO_INBOUND_NUMBER`** (Fragment D; semantically the inbound DID). `TWILIO_ACCOUNT_SID` is **not required** for inbound bridging (no `twilio.rest` client) — inbound only generates TwiML and handles the WS.

### 3.2 `main.py`

```python
app = FastAPI(title="LegalEdge — Inbound Intake Backend", lifespan=lifespan)
# lifespan: store.init_db()  (creates SQLite file + schema if absent)

intake_sessions: dict[str, dict] = {}   # session_id -> live in-memory session state
```

Owns `intake_sessions` and passes it into every `TwilioPhoneHandler`, exactly as screening owns `screening_sessions`. Registers all `/api/*` routes, then mounts the static SPA (§3.11) **last** so the API always wins.

The live session dict created by `/api/voice`:

```python
session_id = str(uuid.uuid4())                 # == the intake row id
stream_secret = secrets.token_urlsafe(18)      # per-call; lives ONLY in the TwiML
intake_sessions[session_id] = {
    "session_id": session_id,
    "caller_number": form.get("From", ""),
    "twilio_call_sid": form.get("CallSid"),
    "contact": None,       # filled by submit_contact_details
    "case": None,          # filled by submit_case_details
    "transcripts": [],     # [{speaker, text, ts}]
    "status": "connecting",
    "stream_secret": stream_secret,
    "ws_attached": False,
    "created_at": _now_iso(),
    "prospect_id": None,
    "prospect_status": None,
}
```

> **Conflict resolved (in-memory vs persisted status):** the in-memory `session["status"]` may be `connecting | in_call | completed` for UI/logging, but the **persisted DB status and every API-returned status** use the canonical lifecycle `in_call | captured | pushed | failed` (§5). `store.save_intake` writes `captured`; `store.update_prospect` writes `pushed`/`failed`.

### 3.3 Routes — see §6 for the complete table. Behaviours:

**`POST /api/voice`** — Twilio inbound Voice webhook (replaces the interviewer's `calls.create`).
- Reads `application/x-www-form-urlencoded` via `await request.form()`: `From`, `To`, `CallSid`.
- If `TWILIO_AUTH_TOKEN` is set, validate `X-Twilio-Signature` over the full request URL + sorted params; return **403** on mismatch.
- Creates the session (above), persists an initial row `store.open_intake(session)` with `status='in_call'` and `call_sid=CallSid` (idempotent on the `call_sid` UNIQUE index), then returns TwiML.
- **TwiML** — secret is a **path segment**, never a query param:

```python
wss_url = f"{settings.public_ws_base}/api/media/{session_id}/{stream_secret}"
twiml = f'<Response><Connect><Stream url="{wss_url}"/></Connect></Response>'
# Response(content=twiml, media_type="application/xml")
```

> **Conflict resolved (Stream URL shape):** Fragment D's `/ws/twilio?sid=&k=` (secret as query param) is **rejected** in favour of Fragment A's **`/api/media/{session_id}/{stream_secret}`** (secret as a path segment). Rationale carried from the screening router: a path-segment secret is not logged as a query string and survives the nginx prefix hop cleanly. The public URL Twilio dials is therefore `wss://ai.traxccel.com/legalEdge/api/media/{session_id}/{secret}`.

**`WEBSOCKET /api/media/{session_id}/{secret}`** — the bridge. Guards (same as screening router):

```python
sess = intake_sessions.get(session_id)
if not sess:                     await ws.close(1008); return
if secret != sess["stream_secret"]: await ws.close(1008); return
if sess["ws_attached"]:          await ws.close(1008); return
sess["ws_attached"] = True
await ws.accept()
handler = TwilioPhoneHandler(session_id, intake_sessions)
try:     await handler.handle_media_stream(ws)
finally: sess["ws_attached"] = False
```

**`GET /api/intakes`** and **`GET /api/intakes/{id}`** — read endpoints backing the SPA (§7). These were **absent from Fragment A and are added here** because the frontend (Fragment C) depends on them. They read from `store` and serialize to the exact wire shapes in §7.4. Both are gated by `X-API-Key` only if `DASHBOARD_API_KEY` is set (open within the trusted subpath otherwise, MVP).

**`POST /api/voice/status`** (optional) — Twilio status-callback sink; logs `CallStatus`; returns `204`.

### 3.4 `twilio_handler.py`

Same architecture as the screening `twilio_handler.py`. `MULAW_FRAME_SIZE = 160`, `CALL_TIMEOUT_SECONDS = 600`. Resamplers, bounded `audio_input_queue(maxsize=250)`, `text_input_queue`, output buffer, `_cur`/`_flush` transcript accumulation, `_run_gemini_session`, `handle_media_stream`, `_timeout_guard`, interrupt/barge-in — all **copied verbatim**. Three LegalEdge differences: (a) the two intake tools, (b) the intake prompt, (c) `_end_call_handler` persists to SQLite + calls the CRM stub instead of scoring/webhook.

Construction:

```python
prompt = build_intake_prompt(
    firm_name=settings.FIRM_NAME, agent_name=settings.AGENT_NAME,
    caller_number=session["caller_number"],
    current_date=..., timezone=settings.INTAKE_TIMEZONE,
)
self.gemini = GeminiLivePhone(
    api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_LIVE_MODEL,
    input_sample_rate=16000, system_instruction=prompt,
    tools=[submit_contact_details_tool(), submit_case_details_tool()],
    tool_mapping={
        "submit_contact_details": self._submit_contact_details,
        "submit_case_details":    self._submit_case_details,
    },
    voice=settings.GEMINI_VOICE,
)
```

`start` frame handling (inbound: adopt Twilio's SID, no outbound SID to match):

```python
if event == "start":
    sess = self.intake_sessions[self.session_id]
    self.call_sid   = data["start"].get("callSid")
    self.stream_sid = data["start"]["streamSid"]
    sess["status"] = "in_call"
    await self.text_input_queue.put(
        "A client has just called the firm. Warmly greet them, introduce "
        "yourself, and begin the intake.")
```

Tool handlers (async, return a short confirmation string; accept `**kw` for forward-compat). They accept the **full merged tool parameter sets** from §4 and stash them on the session:

```python
async def _submit_contact_details(self, full_name="", phone="", phone_from_caller_id=False,
        email="", mailing_address=None, preferred_contact_method="",
        best_time_to_contact="", **kw) -> str:
    s = self.intake_sessions[self.session_id]
    s["contact"] = {
        "full_name": full_name or None,
        "phone": phone or s["caller_number"],
        "phone_from_caller_id": bool(phone_from_caller_id),
        "email": email or None,
        "mailing_address": mailing_address or None,
        "preferred_contact_method": preferred_contact_method or None,
        "best_time_to_contact": best_time_to_contact or None,
    }
    return "Contact details recorded"

async def _submit_case_details(self, practice_area="", practice_area_other_text="",
        situation_description="", location="", incident_date="", key_dates=None,
        opposing_or_other_parties=None, has_current_or_prior_attorney=False,
        attorney_status_notes="", urgency="", urgency_flag=False,
        urgency_notes="", referral_source="", **kw) -> str:
    s = self.intake_sessions[self.session_id]
    s["case"] = {
        "practice_area": practice_area or None,
        "practice_area_other_text": practice_area_other_text or None,
        "situation_description": situation_description or None,
        "location": location or None,
        "incident_date": incident_date or None,
        "key_dates": key_dates or [],
        "opposing_or_other_parties": opposing_or_other_parties or [],
        "has_current_or_prior_attorney": bool(has_current_or_prior_attorney),
        "attorney_status_notes": attorney_status_notes or None,
        "urgency": urgency or None,
        "urgency_flag": bool(urgency_flag),
        "urgency_notes": urgency_notes or None,
        "referral_source": referral_source or None,
    }
    return "Case details recorded"
```

`_end_call_handler` (idempotent via `self._ended`):

```python
async def _end_call_handler(self):
    if self._ended: return
    self._ended = True
    self._flush_transcript()
    sess = self.intake_sessions.get(self.session_id)
    if not sess: return
    sess["status"] = "completed"
    store.save_intake(sess)                        # UPSERT, sets DB status = 'captured'
    try:
        result = legaledge_client.create_prospect(sess)   # {"prospect_id","status"}
        sess["prospect_id"], sess["prospect_status"] = result["prospect_id"], result["status"]
        store.update_prospect(self.session_id, result["prospect_id"], "pushed")   # DB → 'pushed'
    except Exception as e:
        store.update_prospect(self.session_id, None, "failed", error=str(e))       # DB → 'failed'
```

> **Conflict resolved (end status):** Fragment A set `status="completed"` in the DB. That value is **replaced** by the canonical `captured → pushed | failed` lifecycle so the persisted/API status matches the frontend `IntakeStatus`. `create_prospect` is synchronous stdlib-only; wrap with `asyncio.to_thread` if a real impl does blocking I/O.

### 3.5 `prompts.py`

```python
def build_intake_prompt(firm_name, agent_name, caller_number,
                        current_date="", timezone="") -> str: ...
```

Returns a system instruction (firm-agnostic default from Fragment B, §5 of the domain design) establishing: role = friendly virtual intake assistant named `{agent_name}` at `{firm_name}`, powered by LegalEdge, **not a lawyer**; the call is **inbound**. Mandatory ordered goals:

1. **Warm greeting** identifying the firm; set expectations ("I'll take a few details so the right attorney can follow up").
2. **Recording/consent disclosure early** (before gathering) — some jurisdictions require all-party consent; if declined, continue without recording per firm policy.
3. **AI + not-legal-advice disclaimer** (mandatory, three points never skipped/watered down): *I am an AI assistant, not an attorney; this is not legal advice; no attorney-client relationship is formed.* Confirm understanding **before** substantive case questions.
4. **Collect contact** → silently call `submit_contact_details`. The caller's number is already `{caller_number}`; confirm rather than re-ask.
5. **Collect the matter** (practice area, plain description, dates, opposing parties, urgency) → silently call `submit_case_details`.
6. **Wrap-up**: recap preferred contact method + best time; attorney follows up (default one business day); on any deadline/SOL sensitivity, encourage the caller not to delay **without ever stating the limitations period**.

Guardrails baked in: **never give legal advice** (don't assess merits, predict outcomes, quote statutes/deadlines, or confirm "you have a case"); **emotional/distressed callers** — acknowledge first, slow down, mark skipped fields unknown; **emergencies** — tell the caller to hang up and dial 911, stop intake; **adverse contact** — if already represented for this matter, note it and avoid substantive discussion. Phone-call formatting rules copied from the screening prompt (no markdown, spell out numbers, ≤3 sentences per turn, one question at a time). `date_line` block reused verbatim.

### 3.6 `intake_tools.py`

Two `types.Tool` builders (`from google.genai import types`), same shape as the screening tool builders. Both are called **silently** — never announced. See §4 for the exact JSON schemas that these builders must produce.

### 3.7 `store.py` — stdlib `sqlite3`

Single file DB at `settings.DB_PATH`. Module-level connection `check_same_thread=False`, guarded by a `threading.Lock` (writes happen at call end — serialize them). `row_factory = sqlite3.Row`. `PRAGMA journal_mode=WAL`. Schema in §5.

Public interface:

```python
def init_db() -> None: ...
    # connect, create table + indexes, set PRAGMA. Also used by the health check.

def open_intake(session: dict) -> str: ...
    # INSERT OR IGNORE a row at call start: id, call_sid, from_number, status='in_call',
    # created_at. Idempotent on the call_sid UNIQUE index. Returns id.

def save_intake(session: dict) -> str: ...
    # UPSERT (INSERT OR REPLACE) from the live session dict at call end.
    # Flattens session["contact"]/["case"] into the sortable columns AND stores the
    # full args as contact_json / case_json, json.dumps(transcripts) into transcript,
    # sets status='captured' and completed_at=now. Derives:
    #   caller_name        = contact.full_name
    #   contact_phone      = contact.phone or from_number
    #   preferred_contact  = contact.preferred_contact_method
    #   practice_area      = case.practice_area
    #   matter_summary     = case.situation_description
    #   urgency            = case.urgency
    #   opposing_party     = ", ".join(p["name"] for p in case.opposing_or_other_parties) or None
    #   incident_date      = case.incident_date
    #   location           = case.location
    #   conflict_check_flag= 1 if case.has_current_or_prior_attorney else 0
    # A caller who hangs up early still yields a row with whatever was captured
    # (contact/case may be None → those columns NULL). Returns id.

def update_prospect(session_id: str, prospect_id: str | None,
                    status: str, error: str | None = None) -> None: ...
    # Sets legaledge_prospect_id, status ('pushed'|'failed'), error,
    # increments push_attempts, refreshes completed_at.

def get_intake(session_id: str) -> dict | None: ...
    # Single row, with contact_json/case_json/transcript parsed back to objects.

def list_intakes(q: str | None = None, status: str | None = None,
                 practice_area: str | None = None,
                 sort: str = "captured_at", dir: str = "desc") -> list[dict]: ...
    # Filter (q matches caller_name/contact_phone), sort, return list-row dicts.
    # 'captured_at' maps to COALESCE(completed_at, created_at).
```

> **Conflict resolved (schema shape):** Fragment A used flat columns; Fragment D used JSON blobs. The resolution is a **hybrid**: flat sortable columns for everything the list/sort/cards/API need (so columns match the API and frontend), **plus** `contact_json`/`case_json` blobs to retain the richer Fragment B fields (mailing_address, key_dates[], parties[], notes, referral). `id` is the primary key and equals the in-memory `session_id`.

### 3.8 `legaledge_client.py` — CRM stub

```python
def create_prospect(session: dict) -> dict:
    """Stub for the LegalEdge/Traxccel CRM. Production POSTs the intake to
    LEGALEDGE_API_BASE with LEGALEDGE_API_KEY. The stub logs and returns a fake id."""
    contact = session.get("contact") or {}
    case = session.get("case") or {}
    prospect_id = f"prospect_{uuid.uuid4().hex[:12]}"
    logger.info("LegalEdge create_prospect (stub): name=%s matter=%s -> %s",
                contact.get("full_name"), case.get("practice_area"), prospect_id)
    return {"prospect_id": prospect_id, "status": "created"}
```

Pure, synchronous, no network. Signature is stable so a real implementation drops in behind it. A returned `prospect_id` means success → the row moves to `pushed` (the client's `"status":"created"` is the CRM's own status, informational).

### 3.9 `models.py`

Lightweight typing only (no ORM). Pydantic response models for the JSON endpoints and TypedDicts documenting the session/row shapes:

```python
class HealthResponse(BaseModel):
    ok: bool; model: str; voice: str
    gemini_configured: bool; firm: str; db: str      # union of Fragment A + D health shapes

class ContactDetails(TypedDict, total=False):
    full_name: str; phone: str; phone_from_caller_id: bool; email: str
    mailing_address: dict; preferred_contact_method: str; best_time_to_contact: str

class CaseDetails(TypedDict, total=False):
    practice_area: str; practice_area_other_text: str; situation_description: str
    location: str; incident_date: str; key_dates: list; opposing_or_other_parties: list
    has_current_or_prior_attorney: bool; attorney_status_notes: str
    urgency: str; urgency_flag: bool; urgency_notes: str; referral_source: str

# IntakeSummary / IntakeDetail Pydantic models mirror the §7.4 wire shapes exactly.
```

`/api/voice` needs no request body model (Twilio posts form-encoded, read via `request.form()`).

### 3.10 `audio.py` & `gemini_live.py`

**Verbatim, byte-for-byte copies** of the screening `audio.py` and `gemini_live_phone.py` (`GeminiLivePhone`). No LegalEdge-specific imports; independently testable; untouched. The Twilio mu-law 8k ⇄ Gemini Live bridge and barge-in handling are identical to the screener.

### 3.11 Static SPA mount

> **Conflict resolved (mount point):** Fragment A mounted the SPA at `/legalEdge`; Fragment D's nginx **strips** the `/legalEdge/` prefix (trailing-slash `proxy_pass`). These are mutually exclusive. The binding resolution: **nginx strips the prefix, so the backend serves the SPA at root `/` and the API at `/api/*`**. The `/legalEdge` public subpath is applied entirely by nginx + Vite `base` (§8, §9). This makes Fragment A's clean route paths (`/api/voice`, `/api/media/...`) correct as-is.

```python
DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"

# SPA client-route deep-link fallback (registered before the mount, after all /api/*):
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    return FileResponse(DIST_DIR / "index.html")

if DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="spa")
```

The fallback lets `/intakes` and `/intakes/{id}` (as seen by the backend after nginx strips `/legalEdge/`) resolve to `index.html` on deep-link/refresh.

`__main__`: `uvicorn.run(app, host="127.0.0.1", port=8091)`.

> **Conflict resolved (port):** Fragment A's `8090` → **`8091`** (Fragment D; `8090` belongs to the interviewer).

---

## 4. Intake tool JSON schemas

Two declarations, both called **silently** (no verbal narration), required fields minimal, may be called repeatedly to enrich. These are the **merged, canonical** schemas — Fragment A's minimal set is superseded by Fragment B's richer set, with `location`, `incident_date`, and an `urgency` enum added so every flattened SQLite column and frontend field has a source.

### 4.1 `submit_contact_details`

```json
{
  "name": "submit_contact_details",
  "description": "Save the prospective client's contact information. Call silently once the caller's name and at least one contact method (phone or email) are confirmed. May be called again to update fields. Do not announce that you are saving data.",
  "parameters": {
    "type": "object",
    "properties": {
      "full_name": { "type": "string", "description": "Caller's full legal name (first and last), spelling-confirmed." },
      "phone": { "type": "string", "description": "Best callback number in E.164 or local format. Pre-filled from caller ID; confirm or correct verbally. Defaults to the caller's own number." },
      "phone_from_caller_id": { "type": "boolean", "description": "True if the phone value was auto-captured from caller ID and not yet verbally confirmed." },
      "email": { "type": "string", "description": "Email address, spelled back and confirmed." },
      "mailing_address": {
        "type": "object",
        "description": "Postal mailing address.",
        "properties": {
          "street": { "type": "string", "description": "Street address, incl. unit/apt." },
          "city": { "type": "string", "description": "City." },
          "state": { "type": "string", "description": "State or province." },
          "postal_code": { "type": "string", "description": "ZIP or postal code." },
          "country": { "type": "string", "description": "Country; default to firm's country if unstated." }
        }
      },
      "preferred_contact_method": { "type": "string", "enum": ["phone", "email", "text"], "description": "How the caller prefers to be reached." },
      "best_time_to_contact": { "type": "string", "description": "Free-text best time/day window, e.g. 'weekday mornings' or 'after 5pm'." }
    },
    "required": ["full_name"]
  }
}
```

### 4.2 `submit_case_details`

```json
{
  "name": "submit_case_details",
  "description": "Save the prospective client's matter/case information for attorney review. Call silently once the practice area and a plain-language description of the situation are known. May be called again to enrich fields (dates, parties, urgency). Do not announce that you are saving data.",
  "parameters": {
    "type": "object",
    "properties": {
      "practice_area": {
        "type": "string",
        "enum": ["personal_injury", "family", "criminal_defense", "estate_planning", "business_contract", "employment", "immigration", "real_estate", "other"],
        "description": "Best-fit matter type. Use 'other' if unclear or outside the listed areas."
      },
      "practice_area_other_text": { "type": "string", "description": "If practice_area is 'other', a short label describing the matter type." },
      "situation_description": { "type": "string", "description": "Plain-language summary of the caller's situation, in their own words where possible. No legal conclusions." },
      "location": { "type": "string", "description": "City/state or jurisdiction where the matter arises, e.g. 'San Mateo, CA'." },
      "incident_date": { "type": "string", "description": "Primary incident/injury/arrest date in YYYY-MM-DD if determinable, else the caller's approximate phrasing." },
      "key_dates": {
        "type": "array",
        "description": "Relevant dates mentioned by the caller.",
        "items": {
          "type": "object",
          "properties": {
            "label": { "type": "string", "description": "What the date refers to, e.g. 'incident', 'arrest', 'service of papers', 'hearing'." },
            "date": { "type": "string", "description": "Date in YYYY-MM-DD if known, else the caller's approximate phrasing." }
          }
        }
      },
      "opposing_or_other_parties": {
        "type": "array",
        "description": "Other people, companies, insurers, or agencies involved.",
        "items": {
          "type": "object",
          "properties": {
            "name": { "type": "string", "description": "Party name." },
            "role": { "type": "string", "description": "Their role, e.g. 'other driver', 'ex-spouse', 'employer', 'insurer', 'landlord'." }
          }
        }
      },
      "has_current_or_prior_attorney": { "type": "boolean", "description": "True if the caller has or previously had an attorney for THIS matter (conflicts / adverse-contact). Drives conflict_check_flag." },
      "attorney_status_notes": { "type": "string", "description": "Optional detail on current/prior representation for this matter." },
      "urgency": { "type": "string", "enum": ["low", "medium", "high"], "description": "Overall time-pressure of the matter." },
      "urgency_flag": { "type": "boolean", "description": "True if any deadline, court date, or possible statute-of-limitations sensitivity was mentioned or implied (e.g., a past incident/injury/arrest date)." },
      "urgency_notes": { "type": "string", "description": "Free-text detail on the deadline or time pressure. Do NOT include any estimate of the legal limitations period." },
      "referral_source": { "type": "string", "description": "How the caller heard of the firm, e.g. 'Google search', 'referred by friend', 'radio ad', 'returning client'." }
    },
    "required": ["practice_area", "situation_description"]
  }
}
```

> **Schema-level `required`** stays minimal (`full_name`; `practice_area` + `situation_description`) so partial submissions never block. The **conversational** rule (§3.5) still secures at least one working contact method before wrap-up. **SOL sensitivity:** whenever an incident/injury/arrest date or any deadline surfaces, set `urgency_flag = true` and capture the date — never state the actual limitations period.

---

## 5. SQLite schema — `intakes`

Single self-contained table at `DB_PATH`. `id` is a UUIDv4 string (== in-memory `session_id`); timestamps are UTC ISO-8601. JSON payloads are `TEXT` (SQLite `json_valid()`/`json_extract()` still work).

```sql
CREATE TABLE IF NOT EXISTS intakes (
    id                     TEXT PRIMARY KEY,              -- uuid4, app-generated (== session_id)
    call_sid               TEXT UNIQUE,                   -- Twilio CallSid, idempotency anchor
    from_number            TEXT,                          -- E.164 caller ID

    status                 TEXT NOT NULL DEFAULT 'in_call'
                             CHECK (status IN ('in_call','captured','pushed','failed')),

    -- flattened contact (list + cards + sort)
    caller_name            TEXT,                          -- contact.full_name
    contact_phone          TEXT,                          -- confirmed callback (defaults to from_number)
    email                  TEXT,
    preferred_contact      TEXT,                          -- phone|email|text

    -- flattened case (list + cards + sort)
    practice_area          TEXT,                          -- enum (see §4.2)
    matter_summary         TEXT,                          -- case.situation_description
    urgency                TEXT,                          -- low|medium|high
    opposing_party         TEXT,                          -- display string derived from parties[]
    incident_date          TEXT,                          -- ISO YYYY-MM-DD
    location               TEXT,                          -- city/state / jurisdiction
    conflict_check_flag    INTEGER NOT NULL DEFAULT 0,    -- 0/1, from has_current_or_prior_attorney

    -- rich JSON payloads (full tool args, retained for detail/future use)
    contact_json           TEXT,                          -- full submit_contact_details args
    case_json              TEXT,                          -- full submit_case_details args
    transcript             TEXT,                          -- JSON [{speaker,text,ts}]

    -- push / CRM
    legaledge_prospect_id  TEXT,                          -- id returned by the LegalEdge push (nullable until pushed)
    push_attempts          INTEGER NOT NULL DEFAULT 0,
    error                  TEXT,                          -- last failure detail (nullable)

    -- timing
    created_at             TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),  -- == call.answered_at
    completed_at           TEXT                           -- set when status leaves 'in_call'; == captured_at/pushed_at
);

-- Look up an in-flight call by its Twilio SID.
CREATE UNIQUE INDEX IF NOT EXISTS idx_intakes_call_sid ON intakes(call_sid);
-- Dashboards / retry sweeper: "captured-but-not-pushed".
CREATE INDEX IF NOT EXISTS idx_intakes_status_created ON intakes(status, created_at);
```

**Status lifecycle:** `in_call` (answered, WS open — row created by `/api/voice`/`open_intake`) → `captured` (caller hung up; contact + case + transcript persisted by `save_intake`) → `pushed` (CRM stub succeeded; `legaledge_prospect_id` filled) → `failed` (push errored; `error` holds the reason; retryable via `idx_intakes_status_created`).

**Column → API mapping** (drives §7.4): `captured_at = COALESCE(completed_at, created_at)`; `phone = contact_phone`; `call.answered_at = created_at`; `call.from_number = from_number`; `call.duration_seconds = completed_at − created_at`; `push.pushed_at = completed_at when status='pushed'`; `push.reference_id = legaledge_prospect_id`.

---

## 6. FastAPI routes

| # | Method | Path (as the app sees it, post-nginx-strip) | Purpose | Auth |
|---|--------|----------------------------------------------|---------|------|
| 1 | `GET` | `/api/health` | Liveness + config echo. Returns `{"ok":true,"model":...,"voice":...,"gemini_configured":true,"firm":...,"db":"ok"}` | None |
| 2 | `POST` | `/api/voice` | Twilio inbound Voice webhook. Reads `From/To/CallSid` (form), opens the `in_call` row, mints per-call secret, returns `<Connect><Stream>` TwiML | Optional `X-Twilio-Signature` (enforced iff `TWILIO_AUTH_TOKEN` set) |
| 3 | `WEBSOCKET` | `/api/media/{session_id}/{secret}` | The Twilio Media Stream ⇄ Gemini Live bridge. Guards: session exists, secret matches, not already attached → else `close(1008)` | Per-call path-segment secret (known only from the TwiML) |
| 4 | `POST` | `/api/voice/status` (optional) | Twilio status-callback sink; logs `CallStatus`; returns `204` | Optional `X-Twilio-Signature` |
| 5 | `GET` | `/api/intakes` | Dashboard list. Query: `q, status, practice_area, sort, dir`. Returns `IntakeSummary[]` (§7.4) | Optional `X-API-Key` (enforced iff `DASHBOARD_API_KEY` set) |
| 6 | `GET` | `/api/intakes/{id}` | Intake detail. Returns `IntakeDetail` (§7.4); `404` if unknown | Optional `X-API-Key` (as #5) |
| 7 | `GET` | `/{full_path:path}` | SPA deep-link fallback → `index.html` (registered after all `/api/*`, before the `StaticFiles` root mount) | None |

Public URLs (what Twilio/browsers use) are these paths prefixed with `https://ai.traxccel.com/legalEdge`; nginx strips `/legalEdge/` before the app sees them (§8).

> **Conflict resolved (health shape):** Fragment A `{ok,model,gemini_configured,firm}` and Fragment D `{ok,model,voice,db}` are **unioned** into one response.
> **Routes 5 & 6 are additive** — required by Fragment C's frontend, absent from Fragment A's backend list.

---

## 7. Frontend

*React 19 + Vite 6 + Tailwind v4, served by the backend under `/legalEdge/`. Single new runtime dependency vs the sibling: `react-router-dom`.*

### 7.1 Page / component tree

```
src/
├── main.tsx                      # createRoot → <App/>, StrictMode, import './index.css'
├── index.css                     # @theme "Statute" tokens + Fraunces/Inter wiring
├── App.tsx                       # <BrowserRouter basename> + <Routes>
├── lib/{api.ts, brand.ts, format.ts}
├── components/
│   ├── layout/
│   │   ├── AppShell.tsx          # top bar (logo · nav · "by Traxccel") + <Outlet/>
│   │   ├── Navbar.tsx            # LegalEdge mark; links Home / Intakes
│   │   └── Footer.tsx            # "LegalEdge — a Traxccel product" + intake phone
│   ├── ui/
│   │   ├── StatusBadge.tsx       # captured | pushed | failed pill (semantic colors)
│   │   ├── PracticeAreaTag.tsx   # low-saturation colored tag per practice area
│   │   ├── DataTable.tsx         # generic sortable table (sort carets, sticky thead)
│   │   ├── Toolbar.tsx           # search input + status filter + practice filter + count
│   │   ├── EmptyState.tsx        # no-intakes illustration + copy
│   │   ├── Spinner.tsx           # reused spinner SVG
│   │   └── ErrorBanner.tsx       # reused banner (semantic danger color)
│   └── intake/
│       ├── ContactCard.tsx       # caller name / phone / email / preferred contact / best time
│       ├── CaseCard.tsx          # practice area, matter summary, urgency, opposing party, incident date, location, conflict flag
│       ├── TranscriptPanel.tsx   # speaker-tagged transcript, scrollable
│       └── PushStatusCard.tsx    # push state, target, timestamp, reference id, error + retry note, attempts
└── pages/
    ├── LandingPage.tsx           # hero + value line + "Call for a free intake"
    ├── IntakesPage.tsx           # dashboard table (GET /api/intakes)
    ├── IntakeDetailPage.tsx      # detail (GET /api/intakes/{id})
    └── NotFoundPage.tsx          # in-app 404
```

**View 1 — LandingPage:** dark evergreen hero band, LegalEdge wordmark + tagline *"Client intake, captured the moment they call."*, value line ("AI-answered intake calls that capture every detail and hand your firm a case-ready file — before you pick up the phone."), primary pill CTA `Call for a free intake` as `<a href="tel:{INTAKE_PHONE_TEL}">` with a `Phone` lucide icon, secondary `View intakes →` to `/intakes`, a three-tile trust strip (Answered 24/7 · Case-ready capture · Pushed to your system) with serif micro-headings, footer `by Traxccel`.

**View 2 — IntakesPage:** `Toolbar` (free-text `q` on name/phone, `status` filter, `practice_area` filter, result count) + `DataTable` columns **Caller · Phone · Practice area · Date/time · Status** (`StatusBadge`), every header a sort toggle, default sort `captured_at desc`, whole row `<Link>` to `/intakes/:id`. Loading → skeleton rows; empty → `EmptyState`; error → `ErrorBanner`. Filter/sort/search state lives in the URL query string (`?q=&status=&area=&sort=captured_at&dir=desc`) so views are shareable and survive refresh.

**View 3 — IntakeDetailPage:** header with caller name (serif), `StatusBadge`, back link `← All intakes`, captured timestamp; two-column grid (stacks on mobile): left = `ContactCard` + `CaseCard` + `PushStatusCard`, right = sticky scrollable `TranscriptPanel`.

### 7.2 Routing (`App.tsx`) — subpath-safe via `basename`

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
const basename = (import.meta.env.BASE_URL || '/').replace(/\/+$/, '') || '/';  // '/legalEdge'

export default function App() {
  return (
    <BrowserRouter basename={basename}>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<LandingPage />} />
          <Route path="intakes" element={<IntakesPage />} />
          <Route path="intakes/:id" element={<IntakeDetailPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

| In-app path | Public URL | Page |
|---|---|---|
| `/` | `/legalEdge/` | Landing |
| `/intakes` | `/legalEdge/intakes` | Dashboard |
| `/intakes/:id` | `/legalEdge/intakes/{id}` | Detail |
| `*` | any other | 404 |

Deep links / refreshes rely on the backend SPA fallback (§3.11, route #7).

### 7.3 API client (`src/lib/api.ts`)

`apiBase` is **copied unchanged** from the sibling (the `VITE_BACKEND_URL` → `BASE_URL` derivation), so calls hit `/legalEdge/api/...` under the subpath and `http://localhost:8000/api/...` in split dev. Functions mirror the sibling's `unwrap<T>` + `fetch` style:

```ts
export function listIntakes(p: ListIntakesParams = {}): Promise<IntakeSummary[]> {
  const qs = new URLSearchParams(
    Object.entries(p).filter(([, v]) => v != null && v !== '') as [string, string][]
  ).toString();
  return fetch(`${apiBase}/api/intakes${qs ? `?${qs}` : ''}`).then(unwrap<IntakeSummary[]>);
}
export function getIntake(id: string): Promise<IntakeDetail> {
  return fetch(`${apiBase}/api/intakes/${encodeURIComponent(id)}`).then(unwrap<IntakeDetail>);
}
```

`ListIntakesParams`: `{ q?, status?, practice_area?, sort?: 'captured_at'|'caller_name'|'status'|'practice_area', dir?: 'asc'|'desc' }`.

### 7.4 Types + wire shapes (must match §5/§6 exactly)

```ts
export type IntakeStatus = 'captured' | 'pushed' | 'failed';   // rows shown are always ≥ captured

export type PracticeArea =
  | 'personal_injury' | 'family' | 'criminal_defense' | 'estate_planning'
  | 'business_contract' | 'employment' | 'immigration' | 'real_estate' | 'other';

export interface IntakeSummary {
  id: string;
  caller_name: string;
  phone: string;                 // E.164, formatted client-side
  practice_area: PracticeArea;
  captured_at: string;           // ISO-8601 UTC
  status: IntakeStatus;
}

export interface IntakeDetail extends IntakeSummary {
  email: string | null;
  preferred_contact: 'phone' | 'email' | 'text' | null;
  case: {
    practice_area: PracticeArea;
    matter_summary: string;
    urgency: 'low' | 'medium' | 'high' | null;
    opposing_party: string | null;
    incident_date: string | null;
    location: string | null;
    conflict_check_flag: boolean;
  };
  transcript: TranscriptTurn[];
  push: {
    status: IntakeStatus;        // mirrors top-level status
    target: string;              // "LegalEdge Case Manager"
    pushed_at: string | null;    // ISO when status === 'pushed'
    reference_id: string | null; // legaledge_prospect_id
    error: string | null;        // populated when status === 'failed'
    attempts: number;            // push_attempts
  };
  call: {
    duration_seconds: number;
    recording_url: string | null;  // null in the stub
    answered_at: string;           // ISO (= created_at)
    from_number: string;
  };
}

export interface TranscriptTurn { speaker: 'caller' | 'agent'; text: string; ts: number; }
```

> **Conflict resolved (practice-area enum):** Fragment C's short values (`criminal`, `estate`, `business`) are **replaced** by Fragment B's canonical values (`criminal_defense`, `estate_planning`, `business_contract`) so the frontend reads exactly what the tool schema, DB column, and API return. **preferred_contact** widened to include `'text'` to match the tool enum. **Transcript** standardized to `{speaker,text,ts}` (Fragment D's `role` key is not used).

`GET /api/intakes` returns `IntakeSummary[]`; `GET /api/intakes/{id}` returns `IntakeDetail`. Example detail payload (canonical):

```jsonc
{
  "id": "itk_9f3a21", "caller_name": "Maria Gonzalez", "phone": "+14155550142",
  "email": "maria.g@example.com", "preferred_contact": "phone",
  "practice_area": "personal_injury", "captured_at": "2026-07-12T18:04:11Z", "status": "pushed",
  "case": { "practice_area": "personal_injury",
    "matter_summary": "Rear-ended at a red light on I-280; neck and back pain, seen at ER.",
    "urgency": "high", "opposing_party": "Delivery driver (fleet vehicle)",
    "incident_date": "2026-07-10", "location": "San Mateo, CA", "conflict_check_flag": false },
  "transcript": [
    { "speaker": "agent",  "text": "Thanks for calling, how can I help?", "ts": 0 },
    { "speaker": "caller", "text": "I was in a car accident two days ago.", "ts": 4 } ],
  "push": { "status": "pushed", "target": "LegalEdge Case Manager",
    "pushed_at": "2026-07-12T18:05:02Z", "reference_id": "prospect_a1b2c3d4e5f6",
    "error": null, "attempts": 1 },
  "call": { "duration_seconds": 214, "recording_url": null,
    "answered_at": "2026-07-12T18:00:37Z", "from_number": "+14155550142" }
}
```

### 7.5 Visual identity — "Statute" theme

Deliberately **not** the interviewer's dark-navy + coral: deep **evergreen** authority + **brass** accent on warm **porcelain**, light-first with dark hero/app-bar surfaces.

`index.css`:

```css
@import "tailwindcss";
@theme {
  --color-canvas: #F6F4EF;  --color-panel: #FFFFFF;   --color-panel2: #EEEAE1;
  --color-edge: #E1DBCF;    --color-ink: #14211E;     --color-muted: #5E6B66;
  --color-primary: #0E4D45; --color-primary-deep: #0A3A33; --color-accent: #B98A2E;
  --color-slate: #3B5B7A;
  --font-display: "Fraunces", ui-serif, Georgia, serif;
  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
}
body { background: var(--color-canvas); color: var(--color-ink); font-family: var(--font-sans); }
h1, h2, .font-display { font-family: var(--font-display); letter-spacing: -0.01em; }
.tnum { font-variant-numeric: tabular-nums; }
.text-brand { background-image: linear-gradient(90deg,#C79A3D,#1C7A63);
  -webkit-background-clip:text; background-clip:text; color:transparent; }
```

**Semantic status → `IntakeStatus` (1:1):** `captured` text `#2E5A86` / bg `#E4ECF4`; `pushed` text `#0E6B4E` / bg `#DDEFE6`; `failed` text `#9E2B25` / bg `#F6E4E2`. **Practice-area tags** use low-saturation tints of slate / brass / evergreen / clay `#A9552F` / plum `#6C4A79`. **Dark hero/app-bar:** `primary-deep #0A3A33` bg, `#EAF2EE` text, `#C79A3D` CTA, subtle evergreen/brass radial wash. **Typography:** Fraunces (display: hero, page titles, caller names, card headings) + Inter (UI/body/tables/transcript; numerics with `tabular-nums`), both via a Google Fonts `<link>` in `index.html`. **Layout:** 12-col, content `max-w-6xl`, `px-6 lg:px-8`; full-bleed dark hero with centered `max-w-3xl`. **Radii** `rounded-2xl` cards / `rounded-xl` inputs+buttons / `rounded-full` badges+CTA. **Elevation** hairline `border-edge` + soft `shadow-sm/md`. **Density** table rows `h-14`, sticky `thead` `bg-panel2`, brass active-sort caret. **Motion** subtle row fade-in + transcript slide-in, no bounce. **Focus** 2px `accent` ring on all interactive elements.

**Brand module (`src/lib/brand.ts`):** re-exports hashed `legaledge-logo.png` / `legaledge-mark.png` and constants `BRAND_NAME='LegalEdge'`, `BRAND_PARENT='Traxccel'`, `BRAND_PRODUCT='LegalEdge — Client Intake'`, `BRAND_TAGLINE='Client intake, captured the moment they call.'`, `INTAKE_PHONE='+1 (415) 555-0100'`, `INTAKE_PHONE_TEL='+14155550100'`. `index.html`: `<title>LegalEdge · Client Intake</title>`, favicon = LegalEdge mark, Fonts link = Fraunces + Inter.

**Vite config:**

```ts
export default defineConfig(() => ({
  base: '/legalEdge/',
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, '.') } },
  server: { hmr: process.env.DISABLE_HMR !== 'true' },
}));
```

Because `apiBase` reads `BASE_URL`, `base: '/legalEdge/'` makes the client call `/legalEdge/api/...` in production with no code change.

---

## 8. Config / env vars — `backend/.env.example`

```dotenv
# ── Gemini (reuse the interviewer's key + Live model) ─────────────────
GEMINI_API_KEY=
GEMINI_LIVE_MODEL=gemini-3.1-flash-live-preview
GEMINI_VOICE=Puck

# ── Twilio (SAME account as the interviewer; no REST client needed) ───
# Dedicated INBOUND number this agent answers on (distinct from the outbound screener).
TWILIO_INBOUND_NUMBER=+17276070459
# Optional: enables X-Twilio-Signature validation on /api/voice. ACCOUNT_SID is not required.
TWILIO_AUTH_TOKEN=

# ── Public origin (include the /legalEdge subpath) ───────────────────
# The Voice webhook URL and the wss:// Media Stream URL derive from this.
PUBLIC_URL=https://ai.traxccel.com/legalEdge
# Optional host[/path] override for the wss base (no scheme):
# PUBLIC_DOMAIN=ai.traxccel.com/legalEdge
SUBPATH=/legalEdge

# ── Firm identity / conversation ─────────────────────────────────────
FIRM_NAME=Wexler & Associates
AGENT_NAME=Jordan
INTAKE_TIMEZONE=America/New_York

# ── SQLite (relative path so the folder relocates cleanly) ───────────
DB_PATH=./legaledge.db

# ── Dashboard read-endpoint gate (optional) ─────────────────────────
DASHBOARD_API_KEY=

# ── LegalEdge CRM push — STUBBED (log-and-store until real endpoint) ─
LEGALEDGE_API_BASE=https://api.legaledge.example/v1
LEGALEDGE_API_KEY=replace-me
```

The **per-call WS secret is NOT an env var** — it is minted at runtime (`secrets.token_urlsafe`) per call, embedded as a path segment in the `wss://` Stream URL, and verified against the in-memory session when Twilio connects.

`requirements.txt` (Python **3.12** — `audio.py` uses stdlib `audioop`, removed in 3.13; do **not** install `audioop-lts`):

```
fastapi==0.115.*
uvicorn[standard]==0.32.*
google-genai==1.*
python-dotenv==1.*
pytz==2024.*
python-multipart==0.0.*   # Starlette request.form() for the Twilio POST
# stdlib: sqlite3. No sqlalchemy, no twilio SDK, no asyncpg.
```

---

## 9. Deployment shape

Same three-layer pattern as the interviewer (loopback uvicorn → nginx subpath reverse proxy with WS upgrade → Vite base-path SPA), as a **second** instance. Served at `https://ai.traxccel.com/legalEdge`, co-hosted with `/ai-interviewer` (`127.0.0.1:8090`). LegalEdge is its **own** process on `127.0.0.1:8091` with its **own** SQLite file — nothing shared but the host and Twilio/Gemini credentials.

### 9a. Backend process — port 8091

```ini
# /etc/systemd/system/legaledge.service
[Service]
WorkingDirectory=/opt/legaledge/backend
ExecStart=/opt/legaledge/backend/.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8091
Restart=always
[Install]
WantedBy=multi-user.target
```

### 9b. nginx — `/legalEdge/` subpath with WS upgrade (prefix stripped)

```nginx
# in http { } — shared with /ai-interviewer, define ONCE
map $http_upgrade $connection_upgrade { default upgrade; '' close; }

location /legalEdge/ {
    proxy_pass http://127.0.0.1:8091/;      # trailing slash STRIPS /legalEdge/
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_set_header Host $host;
    proxy_read_timeout 3600s;               # long-lived Twilio Media Stream WS
}
```

The trailing-slash `proxy_pass` strips the `/legalEdge/` prefix, so the backend sees clean paths (`/api/voice`, `/api/media/{sid}/{secret}`, `/`, `/intakes`, `/assets/...`) — matching the route registrations in §3/§6 and the SPA served at root (§3.11). Vite `base: '/legalEdge/'` makes every built asset URL absolute under `/legalEdge/`, which nginx strips back to `/assets/...` for the backend `StaticFiles` mount, so nothing 404s under the subpath. The path-segment WS secret survives this hop unchanged.

### 9c. Twilio inbound webhook

In the Twilio Console → **Phone Numbers → Manage → Active numbers → +17276070459 → Voice Configuration → A CALL COMES IN**: Handler **Webhook**, URL `https://ai.traxccel.com/legalEdge/api/voice`, method **POST**. On an inbound call Twilio POSTs `CallSid/From/To`; `/api/voice` opens the `intakes` row (`status='in_call'`), mints the per-call secret, and returns TwiML opening `<Connect><Stream url="wss://ai.traxccel.com/legalEdge/api/media/{session_id}/{secret}"/></Connect>`. The WS handler verifies the path secret against the in-memory session for that `session_id` before bridging audio to Gemini Live.

### 9d. Zoha test

Zoha's mobile is added as a **Verified Caller ID** on this Twilio account (needed only while the account is in trial/verified-callers mode). She simply **dials +17276070459 from her verified phone**. Twilio fires the `A CALL COMES IN` webhook to `/legalEdge/api/voice`; the agent answers and runs the intake; on hang-up the row moves `in_call → captured` (then `→ pushed` once the CRM stub is swapped for the real API). Each call is a fresh `CallSid` row — she can call repeatedly, no code or Twilio change per test.

### 9e. Verify

```bash
curl https://ai.traxccel.com/legalEdge/api/health
# {"ok":true,"model":"gemini-3.1-flash-live-preview","voice":"Puck",
#  "gemini_configured":true,"firm":"Wexler & Associates","db":"ok"}
```

---

## 10. End-to-end session lifecycle

1. Client dials the firm's Twilio number → Twilio POSTs `From/To/CallSid` to `POST /legalEdge/api/voice`.
2. `/api/voice` creates `session_id`, mints `stream_secret`, stores the live session (`connecting`), calls `store.open_intake` (`status='in_call'`), returns `<Connect><Stream>` TwiML (secret is path-only).
3. Twilio opens the WS to `/api/media/{session_id}/{secret}`; guards pass → `TwilioPhoneHandler` starts the bridge.
4. `start` frame → adopt `callSid`/`streamSid`, session `in_call`, push the opener turn → Gemini greets, discloses (recording + AI/not-legal-advice), and begins intake.
5. Media flows both ways via `audio.py` resamplers (Twilio mu-law 8k → PCM16 16k → Gemini; Gemini PCM16 24k → mu-law 8k 160-byte frames → Twilio); barge-in via the `clear` event.
6. Gemini calls `submit_contact_details` / `submit_case_details` (silently, repeatably); handlers fill `session["contact"]`/`["case"]`; transcript accumulates.
7. Call ends (`stop`/`WebSocketDisconnect`, timeout, or teardown) → `finally` runs `_end_call_handler`: flush transcript, `store.save_intake` (DB `captured`), `legaledge_client.create_prospect`, `store.update_prospect` (DB `pushed`, or `failed` + `error`).
8. `ws_attached` cleared in the route `finally`. The SQLite row is the durable record; the SPA reads it via `GET /api/intakes` / `/api/intakes/{id}`.

---

## 11. Provenance (see `docs/PROVENANCE.md`)

Adapted from the Traxccel **AI-Interviewer** MVP2 **phone-screening** agent (outbound Twilio Media Streams ⇄ Gemini Live), **inverted into inbound intake**. **Reused verbatim:** the audio bridge (`audio.py`) and Gemini Live wrapper (`gemini_live.py`, incl. the no-`live_connect_constraints` rule — mint the session cleanly or the Live WS closes 1011), and the `PUBLIC_URL`-derived subpath-preserving `wss://` discipline. **New/changed:** inbound `POST /api/voice` Voice webhook (vs `calls.create`); intake prompt + two intake tools (vs question-bank/scoring); single-file SQLite `intakes` store (vs Postgres + scheduler + webhook outbox; no Recall.ai, no MS Graph); LegalEdge CRM push (stubbed). The `legaledge/` folder is self-contained (own venv, `.env`, SQLite, relative `DB_PATH`), sharing only Twilio + Gemini credentials with the interviewer.
