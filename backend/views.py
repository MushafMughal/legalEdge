"""Server-rendered HTML views for LegalEdge — the simple demo frontend.

After an intake call, open a link to see the captured intake as a branded report
page (like the AI-Interviewer's screening/interview report). This needs no build
step and no API wiring. The richer API-driven React app in ../frontend is the
later, full-frontend phase; these pages are what the demo uses.

LegalEdge is a Traxccel product, so the pages wear Traxccel's own branding — the
deep-navy theme, coral/azure accents, Poppins, and the Traxccel logo — with
"LegalEdge · Client Intake" as a product label, not a separate brand.
"""
import base64
import html
from datetime import datetime
from pathlib import Path

_ASSETS = Path(__file__).resolve().parent / "assets"

PRACTICE_LABELS = {
    "personal_injury": "Personal Injury",
    "family": "Family Law",
    "criminal_defense": "Criminal Defense",
    "estate_planning": "Estate Planning",
    "business_contract": "Business / Contract",
    "employment": "Employment",
    "immigration": "Immigration",
    "real_estate": "Real Estate",
    "other": "Other",
}

FIRM_FIT_LABELS = {
    "likely_accepted": "Likely a fit",
    "needs_review": "Needs review",
    "likely_declined": "Likely not a fit",
}
PRIORITY_LABELS = {"same_day": "Same-day callback", "standard": "Standard callback", "low": "Low priority"}
_PRIORITY_COLORS = {
    "same_day": ("#fb7185", "rgba(244,63,94,.15)"),
    "standard": ("#7fb3e8", "rgba(46,125,209,.15)"),
    "low": ("#8593a8", "rgba(133,147,168,.14)"),
}

# Traxccel status colours on the dark theme.
_STATUS = {
    "captured": ("Captured", "#7fb3e8", "rgba(46,125,209,.15)"),
    "pushed": ("Pushed to LegalEdge", "#34d399", "rgba(16,185,129,.15)"),
    "failed": ("Push failed", "#fb7185", "rgba(244,63,94,.15)"),
    "in_call": ("In call", "#8593a8", "rgba(133,147,168,.14)"),
}

_CSS = """
*{box-sizing:border-box}
body{margin:0;background:#0a0e1a;color:#e8eef6;font-family:'Poppins',system-ui,'Segoe UI',Roboto,sans-serif;line-height:1.55}
a{color:#7fb3e8;text-decoration:none}
.wrap{max-width:940px;margin:0 auto;padding:28px 20px 60px}
.brand{display:flex;align-items:center;gap:14px;margin-bottom:22px}
.brand img{height:26px;width:auto}
.brand .wm{font-weight:800;font-size:20px;background:linear-gradient(90deg,#f26430,#e0457e,#2e7dd1);-webkit-background-clip:text;background-clip:text;color:transparent}
.brand .divider{width:1px;height:20px;background:#243149}
.brand .tag{font-size:12px;color:#8593a8;text-transform:uppercase;letter-spacing:.14em}
.hero{background:linear-gradient(180deg,#111a2e,#0f1729);border:1px solid #1f2a40;border-radius:18px;padding:26px 28px}
.hero .top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap}
h1{margin:0;font-size:26px;font-weight:700}
.sub{color:#8593a8;font-size:13px;margin-top:6px}
.pill{display:inline-block;font-size:12px;font-weight:800;padding:5px 12px;border-radius:999px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:18px}
@media(max-width:720px){.grid{grid-template-columns:1fr}}
.card{background:#0f1729;border:1px solid #1f2a40;border-radius:14px;padding:18px 20px}
h2{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#8593a8;margin:0 0 14px}
.row{display:flex;justify-content:space-between;gap:14px;padding:7px 0;border-bottom:1px solid #1a2438;font-size:14px}
.row:last-child{border-bottom:none}
.row .k{color:#8593a8;flex:0 0 auto}
.row .v{color:#e8eef6;font-weight:500;text-align:right}
.big{margin-top:16px}
.summary{background:#0b1424;border-left:3px solid #f26430;border-radius:8px;padding:12px 14px;font-size:14px;color:#dbe3ee;white-space:pre-wrap}
.tx{background:#0f1729;border:1px solid #1f2a40;border-radius:14px;padding:6px 18px;margin-top:8px}
.turn{display:flex;gap:12px;padding:9px 0;border-bottom:1px solid #1a2438}
.turn:last-child{border-bottom:none}
.spk{flex:0 0 74px;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.05em}
.spk.agent{color:#f26430}.spk.caller{color:#7fb3e8}
.txt{font-size:14px;color:#dbe3ee}
table{width:100%;border-collapse:collapse;background:#0f1729;border:1px solid #1f2a40;border-radius:14px;overflow:hidden}
th{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#8593a8;text-align:left;padding:12px 16px;background:#111a2e;border-bottom:1px solid #1f2a40}
td{padding:13px 16px;border-bottom:1px solid #1a2438;font-size:14px;color:#dbe3ee}
tr:last-child td{border-bottom:none}
tr.clickable{cursor:pointer}
tr.clickable:hover td{background:#131d31}
.name{font-weight:600;color:#e8eef6}
.muted{color:#8593a8}
.empty{text-align:center;color:#8593a8;padding:60px 20px;background:#0f1729;border:1px dashed #243149;border-radius:14px}
.flag{display:inline-block;font-size:11px;font-weight:700;color:#fb7185;background:rgba(244,63,94,.13);padding:3px 9px;border-radius:999px;margin-left:8px}
.foot{margin-top:30px;text-align:center;font-size:12px;color:#5b6981}
.back{font-size:13px;color:#7fb3e8;font-weight:600}
"""

_FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=Poppins:wght@400;500;600;700;800&display=swap">'
)


def _esc(v) -> str:
    return html.escape("" if v is None else str(v))


def _fmt_dt(iso) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y · %I:%M %p UTC")
    except ValueError:
        return _esc(iso)


def _practice(code) -> str:
    return PRACTICE_LABELS.get(code or "", _esc(code) if code else "—")


def _status_pill(status: str) -> str:
    label, fg, bg = _STATUS.get(status or "", (_esc(status) or "—", "#8593a8", "rgba(133,147,168,.14)"))
    return f'<span class="pill" style="color:{fg};background:{bg}">{label}</span>'


def _priority_pill(p) -> str:
    if not p:
        return ""
    fg, bg = _PRIORITY_COLORS.get(p, ("#8593a8", "rgba(133,147,168,.14)"))
    return f'<span class="pill" style="color:{fg};background:{bg}">{PRIORITY_LABELS.get(p, _esc(p))}</span>'


def _yn(v):
    if v is True:
        return "Yes"
    if v is False:
        return "No"
    return None


def _brand() -> str:
    if _LOGO_URI:
        logo = f'<img src="{_LOGO_URI}" alt="Traxccel">'
    else:
        logo = '<span class="wm">traxccel</span>'
    return (
        '<div class="brand">'
        f"{logo}"
        '<span class="divider"></span>'
        '<span class="tag">LegalEdge · Client Intake</span>'
        "</div>"
    )


def _data_uri(name: str) -> str:
    """Embed a bundled asset as base64 so the pages are self-contained (work under
    any deploy subpath, and the folder relocates cleanly)."""
    try:
        return "data:image/png;base64," + base64.b64encode((_ASSETS / name).read_bytes()).decode()
    except Exception:  # noqa: BLE001
        return ""


_LOGO_URI = _data_uri("traxccel-logo.png")
_MARK_URI = _data_uri("traxccel-mark.png")


def _page(title: str, body: str) -> str:
    favicon = f'<link rel="icon" href="{_MARK_URI}">' if _MARK_URI else ""
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{_esc(title)}</title>{favicon}{_FONTS}<style>{_CSS}</style></head>"
        f"<body><div class='wrap'>{_brand()}{body}"
        '<div class="foot">LegalEdge — a Traxccel product · AI-captured client intake</div>'
        "</div></body></html>"
    )


def _kv(rows) -> str:
    out = []
    for k, v in rows:
        if v in (None, "", []):
            continue
        out.append(f'<div class="row"><span class="k">{_esc(k)}</span><span class="v">{v}</span></div>')
    return "".join(out) or '<div class="row"><span class="muted">Nothing captured.</span></div>'


def render_intake_html(intake: dict) -> str:
    contact = intake.get("contact_json") or {}
    case = intake.get("case_json") or {}
    injury = case.get("injury") or {}
    name = _esc(intake.get("caller_name") or contact.get("full_name") or "Unknown caller")
    status = intake.get("status")
    priority = case.get("callback_priority")

    addr = contact.get("mailing_address") or {}
    addr_str = ", ".join(
        _esc(addr.get(k)) for k in ("street", "city", "state", "postal_code", "country") if addr.get(k)
    )
    parties = case.get("opposing_or_other_parties") or []
    parties_str = "; ".join(
        f"{_esc(p.get('name'))}" + (f" ({_esc(p.get('role'))})" if p.get("role") else "")
        for p in parties if isinstance(p, dict) and p.get("name")
    )
    conflict = bool(intake.get("conflict_check_flag") or case.get("has_current_or_prior_attorney"))
    urgency = intake.get("urgency") or case.get("urgency")
    urgency_html = _esc((urgency or "").title())
    if case.get("urgency_flag"):
        urgency_html += '<span class="flag">deadline sensitivity</span>'

    contact_card = _kv([
        ("Full name", _esc(contact.get("full_name") or intake.get("caller_name"))),
        ("Phone", _esc(contact.get("phone") or intake.get("contact_phone") or intake.get("from_number"))),
        ("Email", _esc(contact.get("email") or intake.get("email"))),
        ("Preferred contact", _esc((contact.get("preferred_contact_method") or "").title())),
        ("Best time", _esc(contact.get("best_time_to_contact"))),
        ("Mailing address", addr_str),
    ])

    incident = _esc(case.get("incident_date") or intake.get("incident_date"))
    if case.get("incident_time"):
        incident = (incident + " · " if incident and incident != "" else "") + _esc(case.get("incident_time"))
    case_card = _kv([
        ("Practice area", _practice(case.get("practice_area") or intake.get("practice_area"))
         + (f" — {_esc(case.get('practice_area_other_text'))}" if case.get("practice_area_other_text") else "")),
        ("Sub-type", _esc(case.get("case_subtype"))),
        ("Caller's role", _esc(case.get("caller_role"))),
        ("Urgency", urgency_html or "—"),
        ("Incident date / time", incident),
        ("Location / jurisdiction", _esc(case.get("location") or intake.get("location"))),
        ("Other / opposing parties", parties_str),
        ("Prior/current attorney", ("Yes" + (f" — {_esc(case.get('attorney_status_notes'))}" if case.get("attorney_status_notes") else "")) if conflict else None),
        ("Referral source", _esc(case.get("referral_source"))),
    ])

    matter = _esc(case.get("situation_description") or intake.get("matter_summary"))
    matter_html = f'<div class="big"><div class="summary">{matter}</div></div>' if matter else ""

    # ── Personal-injury / accident layer (only rendered when captured) ──
    injury_card = ""
    accident_card = ""
    if injury:
        injury_card = '<div class="card"><h2>Injuries &amp; treatment</h2>' + _kv([
            ("Injuries", _esc(injury.get("injuries"))),
            ("Serious-injury flags", _esc(injury.get("serious_injury_flags"))),
            ("Treatment started", _yn(injury.get("treatment_started"))),
            ("First treatment", _esc(injury.get("first_treatment"))),
            ("Treatment details", _esc(injury.get("treatment_details"))),
            ("Ongoing treatment", _yn(injury.get("ongoing_treatment"))),
            ("Still symptomatic", _yn(injury.get("still_symptomatic"))),
            ("Impact on daily life", _esc(injury.get("impact_on_daily_life"))),
            ("Lost income / missed work", _esc(injury.get("lost_income"))),
            ("Prior injury history", _esc(injury.get("prior_injury_history"))),
        ]) + "</div>"
        docs = injury.get("evidence_and_documents") or []
        docs_str = ", ".join(_esc(x) for x in docs if x) if isinstance(docs, list) else _esc(docs)
        accident_card = '<div class="card"><h2>Accident, insurance &amp; evidence</h2>' + _kv([
            ("Police involved", _yn(injury.get("police_involved"))),
            ("Responding agency", _esc(injury.get("police_agency"))),
            ("Case / crash number", _esc(injury.get("police_case_number"))),
            ("Caller's insurance", _esc(injury.get("caller_insurance"))),
            ("Other party's insurance", _esc(injury.get("other_party_insurance"))),
            ("Property / vehicle damage", _esc(injury.get("property_damage"))),
            ("Out-of-pocket expenses", _esc(injury.get("out_of_pocket_expenses"))),
            ("Documents available", docs_str),
        ]) + "</div>"

    # ── Preliminary intake assessment (firm fit + callback priority + summary) ──
    assessment_card = ""
    if case.get("firm_fit") or priority or case.get("assessment_summary"):
        assessment_card = '<div class="card"><h2>Intake assessment</h2>' + _kv([
            ("Firm fit", _esc(FIRM_FIT_LABELS.get(case.get("firm_fit"), case.get("firm_fit")))),
            ("Callback priority", _priority_pill(priority) if priority else None),
            ("Summary", _esc(case.get("assessment_summary"))),
        ]) + "</div>"

    push_card = _kv([
        ("Status", _status_pill(status)),
        ("Target", _esc("LegalEdge Case Manager")),
        ("Reference id", _esc(intake.get("legaledge_prospect_id"))),
        ("Attempts", _esc(intake.get("push_attempts"))),
        ("Error", _esc(intake.get("error"))),
    ])

    call_card = _kv([
        ("From", _esc(intake.get("from_number"))),
        ("Answered", _fmt_dt(intake.get("created_at"))),
        ("Completed", _fmt_dt(intake.get("completed_at"))),
        ("Intake id", f'<span class="muted">{_esc(intake.get("id"))}</span>'),
    ])

    transcript = intake.get("transcript") or []
    if transcript:
        turns = "".join(
            f'<div class="turn"><span class="spk {"agent" if t.get("speaker")=="agent" else "caller"}">'
            f'{"Agent" if t.get("speaker")=="agent" else "Caller"}</span>'
            f'<span class="txt">{_esc(t.get("text"))}</span></div>'
            for t in transcript
        )
        transcript_html = f'<h2 style="margin-top:26px">Call transcript</h2><div class="tx">{turns}</div>'
    else:
        transcript_html = ""

    priority_hero = f'<div style="margin-top:8px">{_priority_pill(priority)}</div>' if priority else ""
    body = (
        '<a class="back" href="../">&larr; All intakes</a>'
        '<div class="hero" style="margin-top:12px"><div class="top">'
        f'<div><h1>{name}</h1><div class="sub">{_practice(case.get("practice_area") or intake.get("practice_area"))} · captured {_fmt_dt(intake.get("completed_at") or intake.get("created_at"))}</div></div>'
        f'<div style="text-align:right">{_status_pill(status)}{priority_hero}</div></div>'
        f'{matter_html}</div>'
        '<div class="grid">'
        f'<div class="card"><h2>Contact</h2>{contact_card}</div>'
        f'<div class="card"><h2>Matter</h2>{case_card}</div>'
        f'{injury_card}{accident_card}{assessment_card}'
        f'<div class="card"><h2>LegalEdge push</h2>{push_card}</div>'
        f'<div class="card"><h2>Call</h2>{call_card}</div>'
        '</div>'
        f'{transcript_html}'
    )
    return _page(f"Intake — {name}", body)


def render_index_html(intakes: list) -> str:
    if not intakes:
        body = (
            '<div class="hero"><h1>Client intakes</h1>'
            '<div class="sub">Captured intake calls appear here as soon as a call ends.</div></div>'
            '<div class="empty" style="margin-top:16px">No intakes yet.<br>'
            'When a client calls the intake line, their captured details will show up here.</div>'
        )
        return _page("LegalEdge — Intakes", body)

    def _row(i):
        pill = _priority_pill(i.get("callback_priority")) or '<span class="muted">—</span>'
        iid = _esc(i.get("id"))
        return (
            f'<tr class="clickable" onclick="location.href=\'intake/{iid}\'">'
            f'<td class="name">{_esc(i.get("caller_name") or "Unknown")}</td>'
            f'<td class="muted">{_esc(i.get("contact_phone") or i.get("from_number") or "—")}</td>'
            f'<td>{_practice(i.get("practice_area"))}</td>'
            f'<td class="muted">{_fmt_dt(i.get("completed_at") or i.get("created_at"))}</td>'
            f'<td>{_status_pill(i.get("status"))}</td>'
            f'<td>{pill}</td>'
            f'<td><a href="intake/{iid}">View &rarr;</a></td></tr>'
        )

    rows = "".join(_row(i) for i in intakes)
    body = (
        '<div class="hero"><h1>Client intakes</h1>'
        f'<div class="sub">{len(intakes)} captured intake call(s). Click a row to open the full report.</div></div>'
        '<table style="margin-top:16px"><thead><tr>'
        '<th>Caller</th><th>Phone</th><th>Practice area</th><th>Captured</th><th>Status</th><th>Priority</th><th></th>'
        f'</tr></thead><tbody>{rows}</tbody></table>'
    )
    return _page("LegalEdge — Intakes", body)


def render_not_found_html() -> str:
    body = (
        '<div class="hero"><h1>Not found</h1>'
        '<div class="sub">No intake with that id (or the call is still in progress).</div></div>'
        '<p style="margin-top:18px"><a class="back" href="../">&larr; All intakes</a></p>'
    )
    return _page("LegalEdge — Not found", body)
