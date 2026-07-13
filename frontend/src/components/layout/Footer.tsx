import { BRAND_NAME, BRAND_PARENT, INTAKE_PHONE, INTAKE_PHONE_TEL } from '../../lib/brand';

/**
 * Footer — quiet porcelain footer: "LegalEdge — a Traxccel product" on the
 * left, the intake phone (click-to-call) on the right. (SPEC §7.1.)
 */
export default function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="mt-auto border-t border-edge bg-panel">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-6 py-6 text-sm text-muted sm:flex-row lg:px-8">
        <p>
          <span className="font-display font-semibold text-ink">{BRAND_NAME}</span>
          <span className="mx-1.5 text-edge">—</span>a {BRAND_PARENT} product
        </p>
        <p className="flex items-center gap-2">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true" className="text-primary">
            <path
              d="M6.6 10.8a13 13 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.58 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1 11.4 11.4 0 0 0 .57 3.6 1 1 0 0 1-.25 1L6.6 10.8Z"
              fill="currentColor"
            />
          </svg>
          <span className="text-muted">Intake line</span>
          <a
            href={`tel:${INTAKE_PHONE_TEL}`}
            className="tnum font-medium text-ink underline-offset-2 hover:text-primary hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded"
          >
            {INTAKE_PHONE}
          </a>
        </p>
      </div>
      <div className="border-t border-edge/60 py-3 text-center text-xs text-muted">
        © {year} {BRAND_PARENT}. All rights reserved.
      </div>
    </footer>
  );
}
