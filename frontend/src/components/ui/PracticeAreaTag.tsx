import type { PracticeArea } from '../../lib/api';
import { practiceAreaLabel } from '../../lib/format';

/**
 * PracticeAreaTag — low-saturation colored tag per practice area.
 * Tints derive from the Statute accent hues (SPEC §7.5):
 * slate / brass / evergreen / clay #A9552F / plum #6C4A79, with a
 * neutral porcelain tint for `other`.
 */

/** Canonical practice areas in display order (matches the tool enum, SPEC §4.2). */
export const PRACTICE_AREAS: readonly PracticeArea[] = [
  'personal_injury',
  'family',
  'criminal_defense',
  'estate_planning',
  'business_contract',
  'employment',
  'immigration',
  'real_estate',
  'other',
] as const;

const TINT: Record<PracticeArea, { fg: string; bg: string }> = {
  personal_injury: { fg: '#8A4223', bg: '#F3E7E0' }, // clay
  family: { fg: '#5A3D65', bg: '#EDE6F1' }, // plum
  criminal_defense: { fg: '#334E6B', bg: '#E5EAF1' }, // slate
  estate_planning: { fg: '#0C443D', bg: '#DCEDE8' }, // evergreen
  business_contract: { fg: '#86651F', bg: '#F3EBD6' }, // brass
  employment: { fg: '#3B5B7A', bg: '#E8EEF4' }, // slate (light)
  immigration: { fg: '#146A5C', bg: '#E2EFEB' }, // evergreen (light)
  real_estate: { fg: '#9A7526', bg: '#F5EEDD' }, // brass (light)
  other: { fg: '#5E6B66', bg: '#ECEAE3' }, // porcelain / muted
};

export interface PracticeAreaTagProps {
  area: PracticeArea;
  className?: string;
}

export default function PracticeAreaTag({ area, className = '' }: PracticeAreaTagProps) {
  const t = TINT[area] ?? TINT.other;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${className}`}
      style={{ color: t.fg, backgroundColor: t.bg }}
    >
      {practiceAreaLabel(area)}
    </span>
  );
}
