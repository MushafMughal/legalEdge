// Display helpers for the LegalEdge monitoring SPA (SPEC §7).
import type { PracticeArea } from './api';

/**
 * Format an E.164 (or loosely-formatted) phone number for display.
 * US/NANP numbers render as +1 (415) 555-0142; anything else is returned with
 * light cleanup so we never hide a number we can't parse.
 */
export function formatPhone(raw: string | null | undefined): string {
  if (!raw) return '—';
  const trimmed = raw.trim();
  const digits = trimmed.replace(/[^\d]/g, '');

  // +1 NANP (11 digits leading 1) or bare 10-digit NANP.
  const nanp =
    digits.length === 11 && digits.startsWith('1')
      ? digits.slice(1)
      : digits.length === 10
        ? digits
        : null;
  if (nanp) {
    return `+1 (${nanp.slice(0, 3)}) ${nanp.slice(3, 6)}-${nanp.slice(6)}`;
  }

  // Other E.164 numbers: keep the leading + and the digits.
  if (trimmed.startsWith('+') && digits.length) return `+${digits}`;
  return trimmed;
}

/**
 * Format an ISO-8601 UTC timestamp for display in the viewer's locale.
 * Returns e.g. "Jul 12, 2026, 6:04 PM". Invalid/empty input yields "—".
 */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

/**
 * Format an ISO-8601 UTC timestamp as a combined date + time for display in
 * the viewer's locale. Returns e.g. "Jul 12, 2026, 6:04 PM". Invalid/empty
 * input yields "—".
 */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

const PRACTICE_AREA_LABELS: Record<PracticeArea, string> = {
  personal_injury: 'Personal Injury',
  family: 'Family',
  criminal_defense: 'Criminal Defense',
  estate_planning: 'Estate Planning',
  business_contract: 'Business & Contract',
  employment: 'Employment',
  immigration: 'Immigration',
  real_estate: 'Real Estate',
  other: 'Other',
};

/** Human label for a canonical practice-area enum value (SPEC §4.2 / §7.4). */
export function practiceAreaLabel(area: PracticeArea | string | null | undefined): string {
  if (!area) return '—';
  return PRACTICE_AREA_LABELS[area as PracticeArea] ?? titleCase(area);
}

function titleCase(s: string): string {
  return s
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}
