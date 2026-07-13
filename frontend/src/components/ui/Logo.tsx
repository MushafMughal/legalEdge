import { BRAND_NAME } from '../../lib/brand';

/**
 * Logo — inline SVG "LegalEdge" mark + Fraunces wordmark.
 * No PNG import (SPEC 7.1): a self-contained evergreen tile with a brass
 * "edge" corner and a carved serif L, used by Navbar, Footer and Landing.
 */
export interface LogoProps {
  /** `full` = mark + wordmark; `mark` = tile only. Default `full`. */
  variant?: 'full' | 'mark';
  /** `dark` for light surfaces (default); `light` for dark hero/app-bar surfaces. */
  tone?: 'dark' | 'light';
  /** Height of the mark tile in px (wordmark scales with it). Default 28. */
  size?: number;
  className?: string;
}

export default function Logo({ variant = 'full', tone = 'dark', size = 28, className = '' }: LogoProps) {
  const wordColor = tone === 'light' ? '#EAF2EE' : 'var(--color-ink)';
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`} aria-label={BRAND_NAME}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 40 40"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        role="img"
        aria-hidden={variant === 'full' ? true : undefined}
      >
        <defs>
          <clipPath id="le-tile">
            <rect x="0" y="0" width="40" height="40" rx="10" />
          </clipPath>
        </defs>
        <g clipPath="url(#le-tile)">
          <rect x="0" y="0" width="40" height="40" fill="#0E4D45" />
          {/* brass "edge" corner */}
          <path d="M40 0 L40 18 L22 0 Z" fill="#B98A2E" />
          {/* carved serif L */}
          <path
            d="M13 9 h6 v17 h10 v6 H13 Z"
            fill="#F6F4EF"
          />
        </g>
      </svg>
      {variant === 'full' && (
        <span
          className="font-display font-semibold leading-none tracking-tight"
          style={{ color: wordColor, fontSize: size * 0.66 }}
        >
          Legal<span style={{ color: '#B98A2E' }}>Edge</span>
        </span>
      )}
    </span>
  );
}
