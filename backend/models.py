"""Lightweight typing for the LegalEdge backend (no ORM).

Pydantic response models mirror the §7.4 wire shapes the SPA consumes; the
TypedDicts document the in-memory session sub-dicts that the two intake tools
fill. Nothing here touches SQLite — persistence lives in store.py.
"""
from typing import List, Literal, Optional, TypedDict

from pydantic import BaseModel

# ── Enums / literals (match the tool schemas in §4 and the DB columns in §5) ──
IntakeStatus = Literal["captured", "pushed", "failed"]
PracticeArea = Literal[
    "personal_injury",
    "family",
    "criminal_defense",
    "estate_planning",
    "business_contract",
    "employment",
    "immigration",
    "real_estate",
    "other",
]
PreferredContact = Literal["phone", "email", "text"]
Urgency = Literal["low", "medium", "high"]


# ── Health ────────────────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    ok: bool
    model: str
    voice: str
    gemini_configured: bool
    firm: str
    db: str


# ── Session sub-dict shapes (filled by the intake tools) ──────────────────────
class ContactDetails(TypedDict, total=False):
    full_name: str
    phone: str
    phone_from_caller_id: bool
    email: str
    mailing_address: dict
    preferred_contact_method: str
    best_time_to_contact: str


class CaseDetails(TypedDict, total=False):
    practice_area: str
    practice_area_other_text: str
    situation_description: str
    location: str
    incident_date: str
    key_dates: list
    opposing_or_other_parties: list
    has_current_or_prior_attorney: bool
    attorney_status_notes: str
    urgency: str
    urgency_flag: bool
    urgency_notes: str
    referral_source: str


# ── Transcript ────────────────────────────────────────────────────────────────
class TranscriptTurn(BaseModel):
    speaker: Literal["caller", "agent"]
    text: str
    ts: int


# ── Wire shapes (§7.4) ────────────────────────────────────────────────────────
class IntakeSummary(BaseModel):
    id: str
    caller_name: Optional[str] = None
    phone: Optional[str] = None
    practice_area: Optional[PracticeArea] = None
    captured_at: Optional[str] = None
    status: IntakeStatus


class CaseInfo(BaseModel):
    practice_area: Optional[PracticeArea] = None
    matter_summary: Optional[str] = None
    urgency: Optional[Urgency] = None
    opposing_party: Optional[str] = None
    incident_date: Optional[str] = None
    location: Optional[str] = None
    conflict_check_flag: bool = False


class PushInfo(BaseModel):
    status: IntakeStatus
    target: str
    pushed_at: Optional[str] = None
    reference_id: Optional[str] = None
    error: Optional[str] = None
    attempts: int = 0


class CallInfo(BaseModel):
    duration_seconds: int
    recording_url: Optional[str] = None
    answered_at: Optional[str] = None
    from_number: Optional[str] = None


class IntakeDetail(IntakeSummary):
    email: Optional[str] = None
    preferred_contact: Optional[PreferredContact] = None
    case: CaseInfo
    transcript: List[TranscriptTurn] = []
    push: PushInfo
    call: CallInfo
