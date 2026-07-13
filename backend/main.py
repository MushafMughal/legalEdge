"""FastAPI app for the LegalEdge inbound client-intake voice agent.

Owns `intake_sessions` (live per-call state) and passes it into every
TwilioPhoneHandler. Registers all /api/* routes, then the SPA deep-link
fallback, then mounts the built SPA at root LAST so the API always wins.

Runs as its own process on 127.0.0.1:8091 behind nginx at the /legalEdge
subpath (nginx strips the prefix, so the backend serves the SPA at `/` and the
API at `/api/*`).
"""
import asyncio
import base64
import hashlib
import hmac
import logging
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, WebSocket
from fastapi.responses import HTMLResponse, Response

import config
import store
import views
from twilio_handler import TwilioPhoneHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.init_db()  # creates the SQLite file + schema if absent
    logger.info("[legaledge] database ready at %s", config.settings.DB_PATH)
    if not config.settings.TWILIO_AUTH_TOKEN:
        logger.warning(
            "[legaledge] TWILIO_AUTH_TOKEN is not set — /api/voice does NOT verify the "
            "Twilio signature, so anyone could open a call session. Set it in production."
        )
    if not config.settings.DASHBOARD_API_KEY:
        logger.warning(
            "[legaledge] DASHBOARD_API_KEY is not set — the intake dashboard API is "
            "UNAUTHENTICATED. Protect /api/intakes at the proxy (nginx basic auth) and/or set a key."
        )
    yield


app = FastAPI(title="LegalEdge — Inbound Intake Backend", lifespan=lifespan)

# Live in-memory session state: session_id -> session dict. Same role as the
# screener's screening_sessions.
intake_sessions: dict[str, dict] = {}


# ── helpers ──────────────────────────────────────────────────────────────────
def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _twilio_signature_valid(url: str, params: dict, signature: str, auth_token: str) -> bool:
    """Twilio's HMAC-SHA1 scheme: the full request URL followed by each POST
    param appended as key+value in alphabetical key order, keyed by the auth
    token, base64-encoded, compared to the X-Twilio-Signature header."""
    s = url
    for key in sorted(params.keys()):
        s += key + str(params[key])
    mac = hmac.new(auth_token.encode("utf-8"), s.encode("utf-8"), hashlib.sha1)
    computed = base64.b64encode(mac.digest()).decode("ascii")
    return hmac.compare_digest(computed, signature or "")


def require_dashboard_key(x_api_key: Optional[str] = Header(default=None)):
    """Gate GET /api/intakes* iff DASHBOARD_API_KEY is set; open otherwise (MVP,
    trusted subpath)."""
    key = config.settings.DASHBOARD_API_KEY
    # Constant-time compare (no per-byte timing leak). Enforced only when a key is
    # configured; when unset the dashboard is open — see the startup warning and
    # protect it at the proxy layer (nginx basic auth) for production.
    if key and not hmac.compare_digest(x_api_key or "", key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def _duration_seconds(created_at: Optional[str], completed_at: Optional[str]) -> int:
    if not created_at or not completed_at:
        return 0
    try:
        a = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        b = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        return max(0, int((b - a).total_seconds()))
    except Exception:  # noqa: BLE001
        return 0


def _to_summary(r: dict) -> dict:
    return {
        "id": r.get("id"),
        "caller_name": r.get("caller_name") or "",
        "phone": r.get("phone") or r.get("contact_phone") or r.get("from_number"),
        "practice_area": r.get("practice_area"),
        "captured_at": r.get("captured_at") or r.get("completed_at") or r.get("created_at"),
        "status": r.get("status"),
    }


def _to_detail(r: dict) -> dict:
    status = r.get("status")
    created_at = r.get("created_at")
    completed_at = r.get("completed_at")
    return {
        "id": r.get("id"),
        "caller_name": r.get("caller_name") or "",
        "phone": r.get("contact_phone") or r.get("phone") or r.get("from_number"),
        "practice_area": r.get("practice_area"),
        "captured_at": r.get("captured_at") or completed_at or created_at,
        "status": status,
        "email": r.get("email"),
        "preferred_contact": r.get("preferred_contact"),
        "case": {
            "practice_area": r.get("practice_area"),
            "matter_summary": r.get("matter_summary"),
            "urgency": r.get("urgency"),
            "opposing_party": r.get("opposing_party"),
            "incident_date": r.get("incident_date"),
            "location": r.get("location"),
            "conflict_check_flag": bool(r.get("conflict_check_flag")),
        },
        "transcript": r.get("transcript") or [],
        "push": {
            "status": status,
            "target": "LegalEdge Case Manager",
            "pushed_at": completed_at if status == "pushed" else None,
            "reference_id": r.get("legaledge_prospect_id"),
            "error": r.get("error"),
            "attempts": r.get("push_attempts") or 0,
        },
        "call": {
            "duration_seconds": _duration_seconds(created_at, completed_at),
            "recording_url": None,
            "answered_at": created_at,
            "from_number": r.get("from_number"),
        },
    }


# ── API ──────────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    try:
        store.init_db()
        db_status = "ok"
    except Exception as e:  # noqa: BLE001
        logger.error("health db check failed: %s", e)
        db_status = "error"
    return {
        "ok": True,
        "model": config.settings.GEMINI_LIVE_MODEL,
        "voice": config.settings.GEMINI_VOICE,
        "gemini_configured": bool(config.settings.GEMINI_API_KEY),
        "firm": config.settings.FIRM_NAME,
        "db": db_status,
    }


@app.post("/api/voice")
async def voice(request: Request):
    """Twilio inbound Voice webhook. Opens the in_call row, mints the per-call
    secret, and returns <Connect><Stream> TwiML (secret as a path segment)."""
    form = await request.form()

    if config.settings.TWILIO_AUTH_TOKEN:
        signature = request.headers.get("X-Twilio-Signature", "")
        url = f"{config.settings.PUBLIC_URL}/api/voice"
        params = {k: v for k, v in form.items()}
        if not _twilio_signature_valid(url, params, signature, config.settings.TWILIO_AUTH_TOKEN):
            logger.warning("Rejected /api/voice: bad X-Twilio-Signature")
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    session_id = str(uuid.uuid4())               # == the intake row id
    stream_secret = secrets.token_urlsafe(18)    # per-call; lives ONLY in the TwiML
    intake_sessions[session_id] = {
        "session_id": session_id,
        "caller_number": form.get("From", ""),
        "twilio_call_sid": form.get("CallSid"),
        "contact": None,
        "case": None,
        "transcripts": [],
        "status": "connecting",
        "stream_secret": stream_secret,
        "ws_attached": False,
        "created_at": _now_iso(),
        "prospect_id": None,
        "prospect_status": None,
    }
    store.open_intake(intake_sessions[session_id])  # INSERT OR IGNORE, status='in_call'
    logger.info(
        "Inbound intake %s from %s (call_sid=%s)",
        session_id, form.get("From", ""), form.get("CallSid"),
    )

    # Secret is a PATH segment, never a query param.
    wss_url = f"{config.settings.public_ws_base}/api/media/{session_id}/{stream_secret}"
    twiml = f'<Response><Connect><Stream url="{wss_url}"/></Connect></Response>'
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/api/media/{session_id}/{secret}")
async def media(ws: WebSocket, session_id: str, secret: str):
    sess = intake_sessions.get(session_id)
    if not sess:
        await ws.close(1008)
        return
    if not hmac.compare_digest(secret, sess["stream_secret"]):
        logger.warning("Rejected media WS %s: bad stream secret", session_id)
        await ws.close(1008)
        return
    if sess["ws_attached"]:
        logger.warning("Rejected media WS %s: a stream is already attached", session_id)
        await ws.close(1008)
        return
    sess["ws_attached"] = True
    # accept() and the handler construction must be INSIDE the try so a failure
    # (e.g. Gemini misconfig) can never leave ws_attached stuck True (which would
    # permanently reject re-attach) or leak the session.
    try:
        await ws.accept()
        handler = TwilioPhoneHandler(session_id, intake_sessions)
        await handler.handle_media_stream(ws)
    except Exception as e:  # noqa: BLE001
        logger.error("media WS %s failed: %s", session_id, e)
        try:
            await ws.close()
        except Exception:  # noqa: BLE001
            pass
    finally:
        sess["ws_attached"] = False
        # Free the live session (transcripts + PII + per-call secret) once the call
        # is over and persisted; the durable record lives in SQLite.
        intake_sessions.pop(session_id, None)


@app.post("/api/voice/status")
async def voice_status(request: Request):
    form = await request.form()
    logger.info("Twilio call status (%s): %s", form.get("CallSid"), form.get("CallStatus"))
    return Response(status_code=204)


@app.get("/api/intakes", dependencies=[Depends(require_dashboard_key)])
async def list_intakes(
    q: Optional[str] = None,
    status: Optional[str] = None,
    practice_area: Optional[str] = None,
    sort: str = "captured_at",
    dir: str = "desc",
):
    # Offload the blocking SQLite read off the event loop so it can't stall the
    # real-time audio of concurrent live calls.
    rows = await asyncio.to_thread(
        store.list_intakes, q=q, status=status, practice_area=practice_area, sort=sort, dir=dir
    )
    return [_to_summary(r) for r in rows]


@app.get("/api/intakes/{intake_id}", dependencies=[Depends(require_dashboard_key)])
async def get_intake(intake_id: str):
    row = await asyncio.to_thread(store.get_intake, intake_id)
    # in_call rows are mid-call and hidden from the dashboard (the list filters them
    # too); treat as not-found so a detail status never falls outside the frontend
    # IntakeStatus enum (captured|pushed|failed).
    if not row or row.get("status") == "in_call":
        raise HTTPException(status_code=404, detail="Intake not found")
    return _to_detail(row)


# ── Simple server-rendered HTML views (the demo frontend) ─────────────────────
# Open a link to view captured intakes — no build step, no API wiring. The richer
# API-driven React app in ../frontend is the later, full-frontend phase; it reuses
# the /api/intakes endpoints above. These pages contain client PII: gate them at
# the proxy (nginx basic auth) for anything beyond a demo.
@app.get("/", response_class=HTMLResponse)
async def index():
    rows = await asyncio.to_thread(store.list_intakes)
    return HTMLResponse(views.render_index_html(rows))


@app.get("/intake/{intake_id}", response_class=HTMLResponse)
async def intake_page(intake_id: str):
    row = await asyncio.to_thread(store.get_intake, intake_id)
    if not row or row.get("status") == "in_call":
        return HTMLResponse(views.render_not_found_html(), status_code=404)
    return HTMLResponse(views.render_intake_html(row))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8091)
