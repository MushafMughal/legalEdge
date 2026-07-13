import type { ReactNode } from 'react';
import { AlertTriangle, Briefcase, CalendarClock, MapPin, Users } from 'lucide-react';
import type { IntakeDetail } from '../../lib/api';
import PracticeAreaTag from '../ui/PracticeAreaTag';
import { formatDate } from '../../lib/format';

type CaseCardProps = { case: IntakeDetail['case'] };

const URGENCY_STYLES: Record<'low' | 'medium' | 'high', string> = {
  low: 'bg-panel2 text-muted',
  medium: 'bg-[#F1E7CF] text-[#7A5B12]',
  high: 'bg-[#F6E4E2] text-[#9E2B25]',
};

function Field({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs font-medium uppercase tracking-wide text-muted">{label}</dt>
      <dd className="text-ink">{value ?? <span className="text-muted">Not provided</span>}</dd>
    </div>
  );
}

export default function CaseCard({ case: c }: CaseCardProps) {
  return (
    <section className="rounded-2xl border border-edge bg-panel p-6 shadow-sm">
      <header className="mb-5 flex items-center gap-2">
        <Briefcase className="h-4 w-4 text-primary" aria-hidden />
        <h2 className="font-display text-lg text-ink">The matter</h2>
      </header>

      <div className="mb-5 flex flex-wrap items-center gap-2">
        <PracticeAreaTag area={c.practice_area} />
        {c.urgency && (
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${URGENCY_STYLES[c.urgency]}`}
          >
            {c.urgency} urgency
          </span>
        )}
        {c.conflict_check_flag && (
          <span className="inline-flex items-center gap-1 rounded-full bg-[#F6E4E2] px-2.5 py-0.5 text-xs font-medium text-[#9E2B25]">
            <AlertTriangle className="h-3 w-3" aria-hidden />
            Conflict check
          </span>
        )}
      </div>

      <p className="mb-6 leading-relaxed text-ink">
        {c.matter_summary || <span className="text-muted">No summary captured.</span>}
      </p>

      <dl className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <Field
          label="Location"
          value={
            c.location ? (
              <span className="inline-flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5 text-muted" aria-hidden />
                {c.location}
              </span>
            ) : null
          }
        />
        <Field
          label="Incident date"
          value={
            c.incident_date ? (
              <span className="inline-flex items-center gap-1.5">
                <CalendarClock className="h-3.5 w-3.5 text-muted" aria-hidden />
                {formatDate(c.incident_date)}
              </span>
            ) : null
          }
        />
        <Field
          label="Opposing party"
          value={
            c.opposing_party ? (
              <span className="inline-flex items-center gap-1.5">
                <Users className="h-3.5 w-3.5 text-muted" aria-hidden />
                {c.opposing_party}
              </span>
            ) : null
          }
        />
        <Field
          label="Prior / current attorney"
          value={c.conflict_check_flag ? 'Yes — flagged for conflict review' : 'None reported'}
        />
      </dl>
    </section>
  );
}
