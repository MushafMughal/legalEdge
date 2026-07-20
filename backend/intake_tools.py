"""Gemini Live function-calling tools for LegalEdge intake.

Three declarations, all called SILENTLY (never narrated), with minimal required fields
so partial submissions never block, and repeatable so the agent can enrich fields as the
conversation unfolds:

- submit_contact_details  — who the caller is + how to reach them
- submit_case_details     — the matter: classification, facts, parties, deadlines, and a
                            preliminary firm-fit / callback-priority assessment
- submit_injury_details   — personal-injury / accident layer (injuries, treatment,
                            insurance, police, damages, evidence) for injury/accident matters

The richer set mirrors what a real PI intake call captures (accident facts, injuries,
treatment, insurance, evidence, damages) so the intake team gets a case-ready file.
"""
from google.genai import types

S = types.Schema
T = types.Type


def submit_contact_details_tool() -> types.Tool:
    return types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="submit_contact_details",
                description=(
                    "Save the prospective client's contact information. Call silently once "
                    "the caller's name and at least one contact method (phone or email) are "
                    "confirmed. May be called again to update fields. Do not announce that "
                    "you are saving data."
                ),
                parameters=S(
                    type=T.OBJECT,
                    properties={
                        "full_name": S(type=T.STRING, description="Caller's full legal name as on their driver's license or ID, spelling-confirmed."),
                        "phone": S(type=T.STRING, description="Best callback number. Pre-filled from caller ID; confirm or correct verbally. Defaults to the caller's own number."),
                        "phone_from_caller_id": S(type=T.BOOLEAN, description="True if the phone was auto-captured from caller ID and not yet verbally confirmed."),
                        "email": S(type=T.STRING, description="Email address, spelled back and confirmed."),
                        "mailing_address": S(
                            type=T.OBJECT,
                            description="Postal mailing address (or at least city + state).",
                            properties={
                                "street": S(type=T.STRING, description="Street address, incl. unit/apt."),
                                "city": S(type=T.STRING, description="City."),
                                "state": S(type=T.STRING, description="State or province."),
                                "postal_code": S(type=T.STRING, description="ZIP or postal code."),
                                "country": S(type=T.STRING, description="Country; default to the firm's country if unstated."),
                            },
                        ),
                        "preferred_contact_method": S(type=T.STRING, enum=["phone", "email", "text"], description="How the caller prefers to be reached."),
                        "best_time_to_contact": S(type=T.STRING, description="Best time/day window, e.g. 'this afternoon', 'weekday mornings'."),
                    },
                    required=["full_name"],
                ),
            )
        ]
    )


def submit_case_details_tool() -> types.Tool:
    return types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="submit_case_details",
                description=(
                    "Save the matter/case information for attorney review. Call silently once "
                    "the practice area and a plain-language description are known, and again to "
                    "enrich fields (classification, dates, parties, deadlines) and to set the "
                    "preliminary assessment near the end — firm fit, callback priority, a 0-100 "
                    "case score with its drivers and review flags, and a short summary. Do not "
                    "announce that you are saving data."
                ),
                parameters=S(
                    type=T.OBJECT,
                    properties={
                        "practice_area": S(
                            type=T.STRING,
                            enum=["personal_injury", "family", "criminal_defense", "estate_planning",
                                  "business_contract", "employment", "immigration", "real_estate", "other"],
                            description="Best-fit matter type. Use 'other' if unclear or outside the listed areas.",
                        ),
                        "practice_area_other_text": S(type=T.STRING, description="If practice_area is 'other', a short label for the matter type."),
                        "case_subtype": S(type=T.STRING, description="More specific classification, e.g. 'personal vehicle collision', 'rear-end', 'non-commercial vehicle collision'."),
                        "incident_type": S(
                            type=T.STRING,
                            enum=["motor_vehicle", "commercial_trucking", "workplace_industrial", "medical_negligence", "premises", "product", "other"],
                            description="For an injury/accident matter, the accident/injury category (maps to the firm's case types). Use 'other' if it is not an injury/accident matter.",
                        ),
                        "caller_role": S(type=T.STRING, description="The caller's role in the incident if applicable, e.g. 'driver', 'passenger', 'pedestrian', 'cyclist', or 'calling on behalf of someone else'."),
                        "situation_description": S(type=T.STRING, description="Plain-language summary of the caller's situation, in their own words where possible. No legal conclusions."),
                        "location": S(type=T.STRING, description="City/state or jurisdiction where the matter arises, e.g. 'Cypress, TX'."),
                        "incident_date": S(type=T.STRING, description="Primary incident/injury/arrest date in YYYY-MM-DD if determinable, else the caller's approximate phrasing."),
                        "incident_time": S(type=T.STRING, description="Approximate time of day the incident happened, e.g. '8:07 AM', if applicable."),
                        "key_dates": S(
                            type=T.ARRAY,
                            description="Other relevant dates mentioned.",
                            items=S(type=T.OBJECT, properties={
                                "label": S(type=T.STRING, description="What the date refers to, e.g. 'incident', 'hearing', 'service of papers'."),
                                "date": S(type=T.STRING, description="Date in YYYY-MM-DD if known, else approximate phrasing."),
                            }),
                        ),
                        "opposing_or_other_parties": S(
                            type=T.ARRAY,
                            description="Other people, companies, insurers, or agencies involved.",
                            items=S(type=T.OBJECT, properties={
                                "name": S(type=T.STRING, description="Party name."),
                                "role": S(type=T.STRING, description="Their role, e.g. 'other driver', 'ex-spouse', 'employer', 'insurer'."),
                            }),
                        ),
                        "has_current_or_prior_attorney": S(type=T.BOOLEAN, description="True if the caller has or previously had an attorney for THIS matter (conflicts / adverse-contact)."),
                        "attorney_status_notes": S(type=T.STRING, description="Optional detail on current/prior representation for this matter."),
                        "urgency": S(type=T.STRING, enum=["low", "medium", "high"], description="Overall time-pressure of the matter."),
                        "urgency_flag": S(type=T.BOOLEAN, description="True if any deadline, court date, or possible statute-of-limitations sensitivity was mentioned or implied (e.g. a past incident date)."),
                        "urgency_notes": S(type=T.STRING, description="Detail on the deadline or time pressure. Do NOT include any estimate of the legal limitations period."),
                        "referral_source": S(type=T.STRING, description="How the caller heard of the firm, e.g. 'Google search', 'referred by a friend'."),
                        # ── preliminary assessment (set near the end, for the intake team) ──
                        "firm_fit": S(type=T.STRING, enum=["likely_accepted", "needs_review", "likely_declined"], description="Your preliminary, NON-LEGAL read on whether the matter fits the firm's typical caseload — for triage only."),
                        "callback_priority": S(type=T.STRING, enum=["same_day", "standard", "low"], description="How urgently the intake team should call back, based on injury severity, documentation, deadlines, and firm fit."),
                        "assessment_summary": S(type=T.STRING, description="A brief 2-4 sentence factual summary of the matter for the intake team and why the priority was set. No legal advice or merits assessment."),
                        "case_score": S(type=T.INTEGER, description="Preliminary 0-100 intake-fit score (NOT a legal judgment): higher = firm-preferred case type with a reported injury, treatment started, documentation, law-enforcement involvement, and insurance identified."),
                        "score_factors": S(type=T.ARRAY, description="Short positive drivers behind the score.", items=S(type=T.STRING, description="e.g. 'firm-preferred motor vehicle accident', 'injury reported', 'treatment started', 'police report available', 'both insurers identified'.")),
                        "review_flags": S(type=T.ARRAY, description="Short deductions / items for the intake team to confirm.", items=S(type=T.STRING, description="e.g. 'only one medical visit', 'no imaging yet', 'confirm liability', 'confirm prior injury history'.")),
                    },
                    required=["practice_area", "situation_description"],
                ),
            )
        ]
    )


def submit_injury_details_tool() -> types.Tool:
    return types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="submit_injury_details",
                description=(
                    "Save personal-injury / accident-specific details — injuries, medical "
                    "treatment, insurance, police, damages, evidence, and prior history — for "
                    "matters that involve an injury or accident. Call silently and repeatedly "
                    "as these facts come out. Only used for injury/accident matters; skip it "
                    "otherwise. Do not announce that you are saving data."
                ),
                parameters=S(
                    type=T.OBJECT,
                    properties={
                        "injuries": S(type=T.STRING, description="The caller's injuries and body areas affected, in their words, e.g. 'low back / lumbar pain with MRI findings at L5-S1'."),
                        "serious_injury_flags": S(type=T.STRING, description="Serious-injury indicators mentioned: death, emergency transport, hospitalization, brain/spinal injury, fracture, or surgery. Say 'none reported' if none."),
                        "treatment_started": S(type=T.BOOLEAN, description="True if the caller has received any medical treatment for the injury."),
                        "first_treatment": S(type=T.STRING, description="Where and when the caller first sought treatment, e.g. 'AFC Urgent Care, April 13 2025'."),
                        "treatment_details": S(type=T.STRING, description="Treatment/medication received, e.g. 'injections; meloxicam 15mg daily'."),
                        "ongoing_treatment": S(type=T.BOOLEAN, description="True if the caller is continuing treatment beyond the first visit."),
                        "still_symptomatic": S(type=T.BOOLEAN, description="True if the caller reports they are still in pain or symptomatic."),
                        "impact_on_daily_life": S(type=T.STRING, description="How the injury affects work, driving, sleep, movement, or normal activities."),
                        "lost_income": S(type=T.STRING, description="Missed work or lost wages, or 'none documented yet' / 'unknown'."),
                        "police_involved": S(type=T.BOOLEAN, description="True if police or law enforcement responded to the scene."),
                        "police_agency": S(type=T.STRING, description="The responding law-enforcement agency, if any."),
                        "police_case_number": S(type=T.STRING, description="Crash report / case number, if provided."),
                        "caller_insurance": S(type=T.STRING, description="The caller's own insurance company."),
                        "other_party_insurance": S(type=T.STRING, description="The other / at-fault party's insurance company."),
                        "property_damage": S(type=T.STRING, description="Vehicle or property damage, and whether a damage claim has been opened."),
                        "out_of_pocket_expenses": S(type=T.STRING, description="Out-of-pocket costs so far (copays, prescriptions, rental, towing, repairs), or 'still being gathered'."),
                        "prior_injury_history": S(type=T.STRING, description="Any prior injuries, claims, or treatment for the same body area, or 'none'."),
                        "evidence_and_documents": S(
                            type=T.ARRAY,
                            description="Documents/evidence the caller says they have.",
                            items=S(type=T.STRING, description="e.g. 'police report', 'insurance exchange form', 'photos', 'urgent care records'."),
                        ),
                    },
                    required=[],
                ),
            )
        ]
    )
