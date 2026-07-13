/**
 * Spinner — indeterminate loading indicator.
 * Statute theme: brass ring on a faint evergreen track.
 */
export interface SpinnerProps {
  /** Pixel size of the square spinner. Default 20. */
  size?: number;
  /** Extra classes (e.g. text color override via `text-*`). */
  className?: string;
  /** Accessible label. Default "Loading". */
  label?: string;
}

export default function Spinner({ size = 20, className = '', label = 'Loading' }: SpinnerProps) {
  return (
    <svg
      role="status"
      aria-label={label}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className={`animate-spin text-accent ${className}`}
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.2" strokeWidth="3" />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}
