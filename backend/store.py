"""LegalEdge intake persistence — stdlib sqlite3 ONLY (no ORM, no external deps).

Single-file SQLite DB at settings.DB_PATH. A module-level connection is opened
with check_same_thread=False and every write is serialized through a threading.Lock
(writes happen at call end, so serializing them is cheap and race-free). WAL journal
mode keeps the dashboard reads from blocking the end-of-call write.

Schema is the SPEC §5 hybrid: flat sortable columns for everything the list/sort/
cards/API need, PLUS contact_json / case_json blobs that retain the full tool-arg
payloads (mailing_address, key_dates[], parties[], notes, referral). `id` is the
primary key and equals the in-memory session_id.

to_summary(row) / to_detail(row) serialize a row to the exact §7.4 wire shapes so
main.py can hand the results straight back to the SPA.
"""
import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone

from config import settings

logger = logging.getLogger(__name__)

# ── module-level connection (shared across the app's threads) ────────────────
_lock = threading.Lock()
_conn = sqlite3.connect(settings.DB_PATH, check_same_thread=False)
_conn.row_factory = sqlite3.Row

PUSH_TARGET = "LegalEdge Case Manager"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS intakes (
    id                     TEXT PRIMARY KEY,
    call_sid               TEXT UNIQUE,
    from_number            TEXT,

    status                 TEXT NOT NULL DEFAULT 'in_call'
                             CHECK (status IN ('in_call','captured','pushed','failed')),

    -- flattened contact (list + cards + sort)
    caller_name            TEXT,
    contact_phone          TEXT,
    email                  TEXT,
    preferred_contact      TEXT,

    -- flattened case (list + cards + sort)
    practice_area          TEXT,
    matter_summary         TEXT,
    urgency                TEXT,
    opposing_party         TEXT,
    incident_date          TEXT,
    location               TEXT,
    conflict_check_flag    INTEGER NOT NULL DEFAULT 0,

    -- rich JSON payloads (full tool args, retained for detail/future use)
    contact_json           TEXT,
    case_json              TEXT,
    transcript             TEXT,

    -- push / CRM
    legaledge_prospect_id  TEXT,
    push_attempts          INTEGER NOT NULL DEFAULT 0,
    error                  TEXT,

    -- timing
    created_at             TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    completed_at           TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_intakes_call_sid ON intakes(call_sid);
CREATE INDEX IF NOT EXISTS idx_intakes_status_created ON intakes(status, created_at);
"""

# whitelist for list_intakes ORDER BY — never interpolate raw user input as SQL
_SORT_COLUMNS = {
    "captured_at": "COALESCE(completed_at, created_at)",
    "caller_name": "caller_name",
    "status": "status",
    "practice_area": "practice_area",
}


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ── schema / lifecycle ───────────────────────────────────────────────────────
def init_db() -> None:
    """Create the file + schema if absent and set WAL. Also used by the health check."""
    with _lock:
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.executescript(_SCHEMA)
        _conn.commit()


def open_intake(session: dict) -> str:
    """INSERT OR IGNORE a row at call start (status='in_call'). Idempotent on the
    call_sid UNIQUE index so a retried Twilio webhook cannot duplicate the row.
    Returns the intake id (== session_id)."""
    intake_id = session["session_id"]
    with _lock:
        _conn.execute(
            "INSERT OR IGNORE INTO intakes (id, call_sid, from_number, status, created_at) "
            "VALUES (?, ?, ?, 'in_call', ?)",
            (
                intake_id,
                session.get("twilio_call_sid"),
                session.get("caller_number"),
                session.get("created_at") or _now_iso(),
            ),
        )
        _conn.commit()
    return intake_id


def save_intake(session: dict) -> str:
    """UPSERT (INSERT OR REPLACE) the whole row from the live session at call end.
    Flattens session['contact']/['case'] into the sortable columns AND retains the
    full tool args as contact_json / case_json, dumps transcripts into transcript,
    sets status='captured' and completed_at=now. A caller who hangs up early still
    yields a row with whatever was captured (contact/case may be None → NULL columns).
    Returns the intake id."""
    intake_id = session["session_id"]
    contact = session.get("contact") or {}
    case = session.get("case") or {}
    from_number = session.get("caller_number")

    parties = case.get("opposing_or_other_parties") or []
    # Guard each element: LLM tool-call output is not guaranteed to match the schema,
    # so a non-dict party must not crash (and abort) the whole intake persistence.
    opposing_party = (
        ", ".join(p["name"] for p in parties if isinstance(p, dict) and p.get("name")) or None
    )

    contact_json = json.dumps(session["contact"]) if session.get("contact") else None
    # Fold the personal-injury layer into case_json under an "injury" key so the whole
    # matter (classification, assessment, and injury facts) travels in one blob — no
    # schema change needed as the intake grows.
    case_full = dict(session.get("case") or {})
    if session.get("injury"):
        case_full["injury"] = session["injury"]
    case_json = json.dumps(case_full) if case_full else None
    transcript = json.dumps(session.get("transcripts") or [])

    with _lock:
        _conn.execute(
            """
            INSERT OR REPLACE INTO intakes (
                id, call_sid, from_number, status,
                caller_name, contact_phone, email, preferred_contact,
                practice_area, matter_summary, urgency, opposing_party,
                incident_date, location, conflict_check_flag,
                contact_json, case_json, transcript,
                legaledge_prospect_id, push_attempts, error,
                created_at, completed_at
            ) VALUES (?, ?, ?, 'captured', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                intake_id,
                session.get("twilio_call_sid"),
                from_number,
                contact.get("full_name") or None,
                contact.get("phone") or from_number,
                contact.get("email") or None,
                contact.get("preferred_contact_method") or None,
                case.get("practice_area") or None,
                case.get("situation_description") or None,
                case.get("urgency") or None,
                opposing_party,
                case.get("incident_date") or None,
                case.get("location") or None,
                1 if case.get("has_current_or_prior_attorney") else 0,
                contact_json,
                case_json,
                transcript,
                session.get("prospect_id"),
                0,
                None,
                session.get("created_at") or _now_iso(),
                _now_iso(),
            ),
        )
        _conn.commit()
    return intake_id


def update_prospect(
    session_id: str, prospect_id: str | None, status: str, error: str | None = None
) -> None:
    """Record the CRM push outcome: set legaledge_prospect_id + status ('pushed'|'failed')
    + error, increment push_attempts, and refresh completed_at."""
    with _lock:
        _conn.execute(
            "UPDATE intakes SET legaledge_prospect_id = ?, status = ?, error = ?, "
            "push_attempts = push_attempts + 1, completed_at = ? WHERE id = ?",
            (prospect_id, status, error, _now_iso(), session_id),
        )
        _conn.commit()


def get_intake(session_id: str) -> dict | None:
    """Return a single intake as a dict with contact_json / case_json / transcript
    parsed back into Python objects, or None if unknown."""
    with _lock:
        cur = _conn.execute("SELECT * FROM intakes WHERE id = ?", (session_id,))
        row = cur.fetchone()
    if row is None:
        return None
    d = dict(row)
    d["contact_json"] = _loads(d.get("contact_json"))
    d["case_json"] = _loads(d.get("case_json"))
    d["transcript"] = _loads(d.get("transcript")) or []
    return d


def list_intakes(
    q: str | None = None,
    status: str | None = None,
    practice_area: str | None = None,
    sort: str = "captured_at",
    dir: str = "desc",
) -> list[dict]:
    """Filtered, sorted list of captured-or-later rows. `q` matches caller_name OR
    contact_phone. Returns list-row dicts (pass each to to_summary)."""
    where = ["status != 'in_call'"]
    params: list = []
    if q:
        where.append("(caller_name LIKE ? OR contact_phone LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like])
    if status:
        where.append("status = ?")
        params.append(status)
    if practice_area:
        where.append("practice_area = ?")
        params.append(practice_area)

    order_col = _SORT_COLUMNS.get(sort, _SORT_COLUMNS["captured_at"])
    order_dir = "ASC" if str(dir).lower() == "asc" else "DESC"
    sql = (
        "SELECT * FROM intakes WHERE "
        + " AND ".join(where)
        + f" ORDER BY {order_col} {order_dir}"
    )
    with _lock:
        cur = _conn.execute(sql, params)
        rows = cur.fetchall()
    out = []
    for r in rows:
        d = dict(r)
        case = _loads(d.get("case_json")) or {}
        # Surface the triage fields for the dashboard list without a schema change.
        d["callback_priority"] = case.get("callback_priority")
        d["firm_fit"] = case.get("firm_fit")
        out.append(d)
    return out


# ── serialization to the §7.4 wire shapes ────────────────────────────────────
def to_summary(row) -> dict:
    """Row → IntakeSummary (§7.4)."""
    r = _asdict(row)
    return {
        "id": r.get("id"),
        "caller_name": r.get("caller_name") or "",
        "phone": r.get("contact_phone") or r.get("from_number") or "",
        "practice_area": r.get("practice_area"),
        "captured_at": r.get("completed_at") or r.get("created_at"),
        "status": r.get("status"),
    }


def to_detail(row) -> dict:
    """Row → IntakeDetail (§7.4). Accepts a raw sqlite row/dict or the parsed dict
    from get_intake (json columns may already be objects)."""
    r = _asdict(row)
    status = r.get("status")
    created_at = r.get("created_at")
    completed_at = r.get("completed_at")
    prospect_id = r.get("legaledge_prospect_id")

    detail = to_summary(r)
    detail.update(
        {
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
            "transcript": _loads(r.get("transcript")) or [],
            "push": {
                "status": status,
                "target": PUSH_TARGET,
                "pushed_at": completed_at if status == "pushed" else None,
                "reference_id": prospect_id,
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
    )
    return detail


# ── helpers ──────────────────────────────────────────────────────────────────
def _asdict(row) -> dict:
    return dict(row) if not isinstance(row, dict) else row


def _loads(value):
    """json.loads a TEXT column; pass through if already parsed (or None)."""
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return None


def _parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _duration_seconds(created_at, completed_at) -> int:
    start, end = _parse_iso(created_at), _parse_iso(completed_at)
    if not start or not end:
        return 0
    return max(0, int((end - start).total_seconds()))
