// Typed client for the LegalEdge FastAPI backend (read-only monitoring SPA).
//
// API base resolution (in priority order):
//   1. VITE_BACKEND_URL if set (local split dev, e.g. http://localhost:8091).
//   2. Otherwise derive from the app's own base path (Vite's BASE_URL). This ties
//      the API prefix to wherever the app is served: '' at the domain root, or
//      '/legalEdge' when built with base: '/legalEdge/'. So subpath hosting works
//      automatically — the browser hits '/legalEdge/api/...' in production and
//      nginx strips '/legalEdge/' back to '/api/...' for the backend.
// Copied unchanged from the sibling AI-Interviewer client.
const explicitBackend = import.meta.env.VITE_BACKEND_URL?.trim();
const basePrefix = (import.meta.env.BASE_URL || '/').replace(/\/+$/, '');
export const apiBase = (
  explicitBackend && explicitBackend.length ? explicitBackend : basePrefix
).replace(/\/+$/, '');

// ── Wire types (must match SPEC §5 / §6 / §7.4 exactly) ────────────────────

export type IntakeStatus = 'captured' | 'pushed' | 'failed'; // rows shown are always ≥ captured

export type PracticeArea =
  | 'personal_injury'
  | 'family'
  | 'criminal_defense'
  | 'estate_planning'
  | 'business_contract'
  | 'employment'
  | 'immigration'
  | 'real_estate'
  | 'other';

export interface IntakeSummary {
  id: string;
  caller_name: string;
  phone: string; // E.164, formatted client-side
  practice_area: PracticeArea;
  captured_at: string; // ISO-8601 UTC
  status: IntakeStatus;
}

export interface TranscriptTurn {
  speaker: 'caller' | 'agent';
  text: string;
  ts: number;
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
    status: IntakeStatus; // mirrors top-level status
    target: string; // "LegalEdge Case Manager"
    pushed_at: string | null; // ISO when status === 'pushed'
    reference_id: string | null; // legaledge_prospect_id
    error: string | null; // populated when status === 'failed'
    attempts: number; // push_attempts
  };
  call: {
    duration_seconds: number;
    recording_url: string | null; // null in the stub
    answered_at: string; // ISO (= created_at)
    from_number: string;
  };
}

export interface ListIntakesParams {
  q?: string;
  status?: IntakeStatus;
  practice_area?: PracticeArea;
  sort?: 'captured_at' | 'caller_name' | 'status' | 'practice_area';
  dir?: 'asc' | 'desc';
}

async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(`${res.status} ${detail}`);
  }
  return res.json() as Promise<T>;
}

// ── Endpoints (SPEC §7.3) ──────────────────────────────────────────────────

export function listIntakes(p: ListIntakesParams = {}): Promise<IntakeSummary[]> {
  const qs = new URLSearchParams(
    Object.entries(p).filter(([, v]) => v != null && v !== '') as [string, string][],
  ).toString();
  return fetch(`${apiBase}/api/intakes${qs ? `?${qs}` : ''}`).then(unwrap<IntakeSummary[]>);
}

export function getIntake(id: string): Promise<IntakeDetail> {
  return fetch(`${apiBase}/api/intakes/${encodeURIComponent(id)}`).then(unwrap<IntakeDetail>);
}
