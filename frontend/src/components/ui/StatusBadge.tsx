import type { IntakeStatus } from '../../lib/api';

/**
 * StatusBadge — semantic pill for the canonical intake lifecycle statuses.
 * Colors are the exact Statute swatches from SPEC §7.5:
 *   captured  text #2E5A86 / bg #E4ECF4
 *   pushed    text #0E6B4E / bg #DDEFE6
 *   failed    text #9E2B25 / bg #F6E4E2
 */

/** Ordered statuses shown in the dashboard (rows are always >= captured). */
export const INTAKE_STATUSES: readonly IntakeStatus[] = ['captured', 'pushed', 'failed'] as const;

const STATUS_STYLE: Record<IntakeStatus, { fg: string; bg: string; ring: string; label: string }> = {
  captured: { fg: '#2E5A86', bg: '#E4ECF4', ring: '#C9D8E8', label: 'Captured' },
  pushed: { fg: '#0E6B4E', bg: '#DDEFE6', ring: '#BFE1D0', label: 'Pushed' },
  failed: { fg: '#9E2B25', bg: '#F6E4E2', ring: '#E7C7C4', label: 'Failed' },
};

export interface StatusBadgeProps {
  status: IntakeStatus;
  className?: string;
}

export default function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const s = STATUS_STYLE[status] ?? STATUS_STYLE.captured;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${className}`}
      style={{ color: s.fg, backgroundColor: s.bg, boxShadow: `inset 0 0 0 1px ${s.ring}` }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: s.fg }}
        aria-hidden="true"
      />
      {s.label}
    </span>
  );
}

/** Human label for a status (used by filters). */
export function statusLabel(status: IntakeStatus): string {
  return STATUS_STYLE[status]?.label ?? status;
}
