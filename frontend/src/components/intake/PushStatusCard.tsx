import type { ReactNode } from 'react';
import { CheckCircle2, Send, XCircle } from 'lucide-react';
import type { IntakeDetail } from '../../lib/api';
import StatusBadge from '../ui/StatusBadge';
import { formatDateTime } from '../../lib/format';

type PushStatusCardProps = { push: IntakeDetail['push'] };

function Field({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs font-medium uppercase tracking-wide text-muted">{label}</dt>
      <dd className="text-ink">{value ?? <span className="text-muted">—</span>}</dd>
    </div>
  );
}

export default function PushStatusCard({ push }: PushStatusCardProps) {
  const isPushed = push.status === 'pushed';
  const isFailed = push.status === 'failed';

  return (
    <section className="rounded-2xl border border-edge bg-panel p-6 shadow-sm">
      <header className="mb-5 flex items-center gap-2">
        {isPushed ? (
          <CheckCircle2 className="h-4 w-4 text-primary" aria-hidden />
        ) : isFailed ? (
          <XCircle className="h-4 w-4 text-[#9E2B25]" aria-hidden />
        ) : (
          <Send className="h-4 w-4 text-primary" aria-hidden />
        )}
        <h2 className="font-display text-lg text-ink">CRM push</h2>
        <span className="ml-auto">
          <StatusBadge status={push.status} />
        </span>
      </header>

      <dl className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <Field label="Target" value={push.target} />
        <Field
          label="Pushed at"
          value={push.pushed_at ? formatDateTime(push.pushed_at) : null}
        />
        <Field
          label="Reference ID"
          value={
            push.reference_id ? (
              <span className="tnum font-mono text-sm">{push.reference_id}</span>
            ) : null
          }
        />
        <Field label="Attempts" value={<span className="tnum">{push.attempts}</span>} />
      </dl>

      {isFailed && (
        <div className="mt-5 rounded-xl border border-[#E8C9C6] bg-[#F6E4E2] px-4 py-3">
          <p className="text-sm font-medium text-[#9E2B25]">Push failed</p>
          {push.error && (
            <p className="mt-1 text-sm text-[#9E2B25]/90">{push.error}</p>
          )}
          <p className="mt-2 text-xs text-[#9E2B25]/80">
            This intake is retryable and will be picked up by the next push sweep.
          </p>
        </div>
      )}
    </section>
  );
}
