import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';

/**
 * EmptyState — friendly "nothing here yet" panel with a small inline
 * illustration (a quiet phone / intake sheet in Statute tones).
 */
export interface EmptyStateProps {
  /** Optional lucide-react icon shown in place of the default illustration. */
  icon?: LucideIcon;
  /** Serif micro-heading. */
  title?: string;
  /** Supporting sentence. */
  message?: string;
  /** Optional call-to-action (e.g. a link or button). */
  action?: ReactNode;
  className?: string;
}

export default function EmptyState({
  icon: Icon,
  title = 'No intakes yet',
  message = 'When a prospective client calls, their captured intake will appear here.',
  action,
  className = '',
}: EmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center rounded-2xl border border-edge bg-panel px-6 py-16 text-center shadow-sm ${className}`}
    >
      {Icon ? (
        <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border border-edge bg-panel2 text-primary">
          <Icon className="h-7 w-7" aria-hidden="true" />
        </div>
      ) : (
      <svg
        width="72"
        height="72"
        viewBox="0 0 72 72"
        fill="none"
        aria-hidden="true"
        className="mb-5"
      >
        <rect x="14" y="8" width="44" height="56" rx="6" fill="#EEEAE1" stroke="#E1DBCF" strokeWidth="2" />
        <rect x="22" y="20" width="28" height="3.5" rx="1.75" fill="#C7CFCB" />
        <rect x="22" y="30" width="22" height="3.5" rx="1.75" fill="#D6DDD9" />
        <rect x="22" y="40" width="26" height="3.5" rx="1.75" fill="#D6DDD9" />
        <circle cx="50" cy="52" r="12" fill="#0E4D45" />
        <path
          d="M45.5 48.2c-.4.6-.5 1.4-.2 2.1a11 11 0 0 0 5.6 5.6c.7.3 1.5.2 2.1-.2l1.1-.8c.5-.4.6-1 .3-1.5l-1-1.7a1.2 1.2 0 0 0-1.4-.5l-1.3.4a8 8 0 0 1-2.9-2.9l.4-1.3a1.2 1.2 0 0 0-.5-1.4l-1.7-1a1.1 1.1 0 0 0-1.5.3l-.8 1.1Z"
          fill="#B98A2E"
        />
      </svg>
      )}
      <h3 className="font-display text-lg font-semibold text-ink">{title}</h3>
      <p className="mt-1.5 max-w-sm text-sm text-muted">{message}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
