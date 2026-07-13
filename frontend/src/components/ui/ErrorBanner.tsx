import Spinner from './Spinner';

/**
 * ErrorBanner — inline failure notice using the Statute danger color
 * (matches the `failed` status swatch: text #9E2B25 on #F6E4E2).
 */
export interface ErrorBannerProps {
  /** Human-readable error message. */
  message: string;
  /** Optional retry handler; renders a retry button when provided. */
  onRetry?: () => void;
  /** When true the retry button shows a spinner and is disabled. */
  retrying?: boolean;
  className?: string;
}

export default function ErrorBanner({ message, onRetry, retrying = false, className = '' }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-sm ${className}`}
      style={{ backgroundColor: '#F6E4E2', borderColor: '#E7C7C4', color: '#9E2B25' }}
    >
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        className="mt-0.5 shrink-0"
        aria-hidden="true"
      >
        <path
          d="M12 8v5m0 3.5h.01M10.3 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.7 3.86a2 2 0 0 0-3.42 0Z"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <div className="flex-1">
        <p className="font-medium">Something went wrong</p>
        <p className="mt-0.5 opacity-90">{message}</p>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          disabled={retrying}
          className="ml-2 inline-flex items-center gap-1.5 rounded-full border border-current/30 px-3 py-1 text-xs font-medium transition hover:bg-white/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-60"
        >
          {retrying && <Spinner size={13} className="text-current" />}
          Retry
        </button>
      )}
    </div>
  );
}
