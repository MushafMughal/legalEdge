"""LegalEdge / Traxccel CRM push — STUBBED.

A real implementation POSTs the captured intake to LEGALEDGE_API_BASE authenticated
with LEGALEDGE_API_KEY and returns the CRM's prospect id. The stub is pure, synchronous,
and does no network I/O: it logs and returns a fake prospect id so the end-of-call path
can move the row to 'pushed'. The signature is stable so the real client drops in behind
it with no caller changes (wrap with asyncio.to_thread if it does blocking I/O)."""
import logging
import uuid

logger = logging.getLogger(__name__)


def create_prospect(session: dict) -> dict:
    """Push a captured intake to the LegalEdge CRM. Returns {"prospect_id","status"}.

    A returned prospect_id means success → the intake row moves to 'pushed'. The
    "status" value ("created") is the CRM's own record status, informational only."""
    contact = session.get("contact") or {}
    case = session.get("case") or {}
    prospect_id = f"prospect_{uuid.uuid4().hex[:12]}"
    logger.info(
        "LegalEdge create_prospect (stub): name=%s matter=%s -> %s",
        contact.get("full_name"),
        case.get("practice_area"),
        prospect_id,
    )
    return {"prospect_id": prospect_id, "status": "created"}
