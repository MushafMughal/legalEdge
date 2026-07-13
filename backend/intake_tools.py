"""Gemini Live function-calling tools for LegalEdge intake.

Two declarations, both called SILENTLY (never narrated), with minimal required fields
so partial submissions never block, and repeatable so the agent can enrich fields as
the conversation unfolds. The schemas below are the canonical §4 shapes byte-for-byte.
"""
from google.genai import types


def submit_contact_details_tool() -> types.Tool:
    return types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="submit_contact_details",
                description=(
                    "Save the prospective client's contact information. Call silently "
                    "once the caller's name and at least one contact method (phone or "
                    "email) are confirmed. May be called again to update fields. Do not "
                    "announce that you are saving data."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "full_name": types.Schema(
                            type=types.Type.STRING,
                            description="Caller's full legal name (first and last), spelling-confirmed.",
                        ),
                        "phone": types.Schema(
                            type=types.Type.STRING,
                            description=(
                                "Best callback number in E.164 or local format. Pre-filled "
                                "from caller ID; confirm or correct verbally. Defaults to the "
                                "caller's own number."
                            ),
                        ),
                        "phone_from_caller_id": types.Schema(
                            type=types.Type.BOOLEAN,
                            description=(
                                "True if the phone value was auto-captured from caller ID and "
                                "not yet verbally confirmed."
                            ),
                        ),
                        "email": types.Schema(
                            type=types.Type.STRING,
                            description="Email address, spelled back and confirmed.",
                        ),
                        "mailing_address": types.Schema(
                            type=types.Type.OBJECT,
                            description="Postal mailing address.",
                            properties={
                                "street": types.Schema(
                                    type=types.Type.STRING,
                                    description="Street address, incl. unit/apt.",
                                ),
                                "city": types.Schema(
                                    type=types.Type.STRING, description="City."
                                ),
                                "state": types.Schema(
                                    type=types.Type.STRING,
                                    description="State or province.",
                                ),
                                "postal_code": types.Schema(
                                    type=types.Type.STRING,
                                    description="ZIP or postal code.",
                                ),
                                "country": types.Schema(
                                    type=types.Type.STRING,
                                    description="Country; default to firm's country if unstated.",
                                ),
                            },
                        ),
                        "preferred_contact_method": types.Schema(
                            type=types.Type.STRING,
                            enum=["phone", "email", "text"],
                            description="How the caller prefers to be reached.",
                        ),
                        "best_time_to_contact": types.Schema(
                            type=types.Type.STRING,
                            description=(
                                "Free-text best time/day window, e.g. 'weekday mornings' or "
                                "'after 5pm'."
                            ),
                        ),
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
                    "Save the prospective client's matter/case information for attorney "
                    "review. Call silently once the practice area and a plain-language "
                    "description of the situation are known. May be called again to enrich "
                    "fields (dates, parties, urgency). Do not announce that you are saving data."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "practice_area": types.Schema(
                            type=types.Type.STRING,
                            enum=[
                                "personal_injury",
                                "family",
                                "criminal_defense",
                                "estate_planning",
                                "business_contract",
                                "employment",
                                "immigration",
                                "real_estate",
                                "other",
                            ],
                            description=(
                                "Best-fit matter type. Use 'other' if unclear or outside the "
                                "listed areas."
                            ),
                        ),
                        "practice_area_other_text": types.Schema(
                            type=types.Type.STRING,
                            description=(
                                "If practice_area is 'other', a short label describing the "
                                "matter type."
                            ),
                        ),
                        "situation_description": types.Schema(
                            type=types.Type.STRING,
                            description=(
                                "Plain-language summary of the caller's situation, in their "
                                "own words where possible. No legal conclusions."
                            ),
                        ),
                        "location": types.Schema(
                            type=types.Type.STRING,
                            description=(
                                "City/state or jurisdiction where the matter arises, e.g. "
                                "'San Mateo, CA'."
                            ),
                        ),
                        "incident_date": types.Schema(
                            type=types.Type.STRING,
                            description=(
                                "Primary incident/injury/arrest date in YYYY-MM-DD if "
                                "determinable, else the caller's approximate phrasing."
                            ),
                        ),
                        "key_dates": types.Schema(
                            type=types.Type.ARRAY,
                            description="Relevant dates mentioned by the caller.",
                            items=types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "label": types.Schema(
                                        type=types.Type.STRING,
                                        description=(
                                            "What the date refers to, e.g. 'incident', "
                                            "'arrest', 'service of papers', 'hearing'."
                                        ),
                                    ),
                                    "date": types.Schema(
                                        type=types.Type.STRING,
                                        description=(
                                            "Date in YYYY-MM-DD if known, else the caller's "
                                            "approximate phrasing."
                                        ),
                                    ),
                                },
                            ),
                        ),
                        "opposing_or_other_parties": types.Schema(
                            type=types.Type.ARRAY,
                            description="Other people, companies, insurers, or agencies involved.",
                            items=types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "name": types.Schema(
                                        type=types.Type.STRING, description="Party name."
                                    ),
                                    "role": types.Schema(
                                        type=types.Type.STRING,
                                        description=(
                                            "Their role, e.g. 'other driver', 'ex-spouse', "
                                            "'employer', 'insurer', 'landlord'."
                                        ),
                                    ),
                                },
                            ),
                        ),
                        "has_current_or_prior_attorney": types.Schema(
                            type=types.Type.BOOLEAN,
                            description=(
                                "True if the caller has or previously had an attorney for "
                                "THIS matter (conflicts / adverse-contact). Drives "
                                "conflict_check_flag."
                            ),
                        ),
                        "attorney_status_notes": types.Schema(
                            type=types.Type.STRING,
                            description=(
                                "Optional detail on current/prior representation for this matter."
                            ),
                        ),
                        "urgency": types.Schema(
                            type=types.Type.STRING,
                            enum=["low", "medium", "high"],
                            description="Overall time-pressure of the matter.",
                        ),
                        "urgency_flag": types.Schema(
                            type=types.Type.BOOLEAN,
                            description=(
                                "True if any deadline, court date, or possible "
                                "statute-of-limitations sensitivity was mentioned or implied "
                                "(e.g., a past incident/injury/arrest date)."
                            ),
                        ),
                        "urgency_notes": types.Schema(
                            type=types.Type.STRING,
                            description=(
                                "Free-text detail on the deadline or time pressure. Do NOT "
                                "include any estimate of the legal limitations period."
                            ),
                        ),
                        "referral_source": types.Schema(
                            type=types.Type.STRING,
                            description=(
                                "How the caller heard of the firm, e.g. 'Google search', "
                                "'referred by friend', 'radio ad', 'returning client'."
                            ),
                        ),
                    },
                    required=["practice_area", "situation_description"],
                ),
            )
        ]
    )
