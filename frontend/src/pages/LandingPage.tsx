import { Link } from 'react-router-dom';
import { ArrowRight, Clock, FileCheck2, Phone, Send } from 'lucide-react';
import {
  BRAND_NAME,
  BRAND_PARENT,
  BRAND_TAGLINE,
  INTAKE_PHONE,
  INTAKE_PHONE_TEL,
} from '../lib/brand';

const TRUST_TILES = [
  {
    icon: Clock,
    title: 'Answered 24/7',
    body: 'Every prospective client reaches a warm, professional intake — day or night, no voicemail.',
  },
  {
    icon: FileCheck2,
    title: 'Case-ready capture',
    body: 'Contact details, the matter, dates, and parties — structured and confirmed on the call.',
  },
  {
    icon: Send,
    title: 'Pushed to your system',
    body: 'Each intake lands in your case manager as a ready-to-review file before you pick up.',
  },
];

export default function LandingPage() {
  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="relative overflow-hidden bg-primary-deep text-[#EAF2EE]">
        <div
          className="pointer-events-none absolute inset-0 opacity-70"
          style={{
            background:
              'radial-gradient(60% 80% at 20% 0%, rgba(28,122,99,0.35) 0%, transparent 60%), radial-gradient(50% 70% at 90% 20%, rgba(199,154,61,0.18) 0%, transparent 55%)',
          }}
          aria-hidden
        />
        <div className="relative mx-auto max-w-3xl px-6 py-24 text-center lg:px-8 lg:py-32">
          <p className="mb-4 text-sm font-medium uppercase tracking-[0.2em] text-[#C79A3D]">
            {BRAND_NAME} · a {BRAND_PARENT} product
          </p>
          <h1 className="font-display text-5xl leading-tight tracking-tight text-white sm:text-6xl">
            {BRAND_NAME}
          </h1>
          <p className="mt-4 font-display text-xl text-[#CFE0D9] sm:text-2xl">{BRAND_TAGLINE}</p>
          <p className="mx-auto mt-6 max-w-2xl text-base leading-relaxed text-[#B7C9C1] sm:text-lg">
            AI-answered intake calls that capture every detail and hand your firm a case-ready file
            — before you pick up the phone.
          </p>

          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <a
              href={`tel:${INTAKE_PHONE_TEL}`}
              className="inline-flex items-center gap-2 rounded-full bg-[#C79A3D] px-7 py-3.5 font-medium text-[#14211E] shadow-md transition hover:bg-[#d5a94a] focus:outline-none focus:ring-2 focus:ring-[#C79A3D] focus:ring-offset-2 focus:ring-offset-primary-deep"
            >
              <Phone className="h-5 w-5" aria-hidden />
              Call for a free intake
            </a>
            <Link
              to="/intakes"
              className="group inline-flex items-center gap-1.5 rounded-full px-5 py-3.5 font-medium text-[#EAF2EE] transition hover:text-white focus:outline-none focus:ring-2 focus:ring-[#C79A3D] focus:ring-offset-2 focus:ring-offset-primary-deep"
            >
              View intakes
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" aria-hidden />
            </Link>
          </div>

          <p className="mt-6 tnum text-sm text-[#9FB4AC]">{INTAKE_PHONE}</p>
        </div>
      </section>

      {/* Trust strip */}
      <section className="mx-auto w-full max-w-6xl px-6 py-16 lg:px-8">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {TRUST_TILES.map(({ icon: Icon, title, body }) => (
            <div
              key={title}
              className="rounded-2xl border border-edge bg-panel p-6 shadow-sm"
            >
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-panel2 text-primary">
                <Icon className="h-5 w-5" aria-hidden />
              </span>
              <h2 className="mt-4 font-display text-lg text-ink">{title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-muted">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* by-Traxccel footer */}
      <footer className="border-t border-edge">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-2 px-6 py-8 text-sm text-muted sm:flex-row lg:px-8">
          <p>
            {BRAND_NAME} — a {BRAND_PARENT} product
          </p>
          <a
            href={`tel:${INTAKE_PHONE_TEL}`}
            className="tnum inline-flex items-center gap-1.5 hover:text-ink focus:outline-none focus:ring-2 focus:ring-accent rounded"
          >
            <Phone className="h-3.5 w-3.5" aria-hidden />
            {INTAKE_PHONE}
          </a>
        </div>
      </footer>
    </div>
  );
}
