import { practiceAreaLabel } from '../../lib/format';
import { INTAKE_STATUSES, statusLabel } from './StatusBadge';
import { PRACTICE_AREAS } from './PracticeAreaTag';

/**
 * Partial filter patch emitted by the toolbar. Values are raw strings straight
 * from the form controls (URL query state is owned by the page); an empty
 * string means "clear this filter".
 */
export interface ToolbarChange {
  q?: string;
  status?: string;
  practiceArea?: string;
}

/**
 * Toolbar — dashboard controls: free-text search (name/phone), status
 * filter, practice-area filter, and a live result count.
 * State is owned by the page (URL query string, SPEC §7.1 View 2).
 */
export interface ToolbarProps {
  /** Search text (matches caller name / phone). */
  q: string;
  /** Selected status value, or '' for "All statuses". */
  status: string;
  /** Selected practice area value, or '' for "All practice areas". */
  practiceArea: string;
  /** Emits a partial patch when any control changes. */
  onChange: (patch: ToolbarChange) => void;
  /** Number of rows currently shown. */
  count: number;
  className?: string;
}

const selectClass =
  'h-11 rounded-xl border border-edge bg-panel px-3 pr-8 text-sm text-ink shadow-sm transition focus:outline-none focus-visible:ring-2 focus-visible:ring-accent';

export default function Toolbar({
  q,
  status,
  practiceArea,
  onChange,
  count,
  className = '',
}: ToolbarProps) {
  return (
    <div className={`flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center ${className}`}>
      {/* Search */}
      <div className="relative flex-1 sm:min-w-[15rem]">
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
        >
          <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
          <path d="m20 20-3.2-3.2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <input
          type="search"
          value={q}
          onChange={(e) => onChange({ q: e.target.value })}
          placeholder="Search by name or phone"
          aria-label="Search intakes by name or phone"
          className="h-11 w-full rounded-xl border border-edge bg-panel pl-9 pr-3 text-sm text-ink shadow-sm transition placeholder:text-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        />
      </div>

      {/* Status filter */}
      <select
        value={status}
        onChange={(e) => onChange({ status: e.target.value })}
        aria-label="Filter by status"
        className={selectClass}
      >
        <option value="">All statuses</option>
        {INTAKE_STATUSES.map((s) => (
          <option key={s} value={s}>
            {statusLabel(s)}
          </option>
        ))}
      </select>

      {/* Practice-area filter */}
      <select
        value={practiceArea}
        onChange={(e) => onChange({ practiceArea: e.target.value })}
        aria-label="Filter by practice area"
        className={selectClass}
      >
        <option value="">All practice areas</option>
        {PRACTICE_AREAS.map((a) => (
          <option key={a} value={a}>
            {practiceAreaLabel(a)}
          </option>
        ))}
      </select>

      {/* Count */}
      <span className="text-sm text-muted sm:ml-auto tnum">
        {count} {count === 1 ? 'intake' : 'intakes'}
      </span>
    </div>
  );
}
