import type { ReactNode } from 'react';
import { Mail, Phone, User } from 'lucide-react';
import type { IntakeDetail } from '../../lib/api';
import { formatPhone } from '../../lib/format';

type ContactCardProps = Pick<
  IntakeDetail,
  'caller_name' | 'phone' | 'email' | 'preferred_contact'
>;

const PREFERRED_LABEL: Record<'phone' | 'email' | 'text', string> = {
  phone: 'Phone call',
  email: 'Email',
  text: 'Text message',
};

function Field({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs font-medium uppercase tracking-wide text-muted">{label}</dt>
      <dd className="text-ink">{value ?? <span className="text-muted">Not provided</span>}</dd>
    </div>
  );
}

export default function ContactCard({
  caller_name,
  phone,
  email,
  preferred_contact,
}: ContactCardProps) {
  return (
    <section className="rounded-2xl border border-edge bg-panel p-6 shadow-sm">
      <header className="mb-5 flex items-center gap-2">
        <User className="h-4 w-4 text-primary" aria-hidden />
        <h2 className="font-display text-lg text-ink">Contact</h2>
      </header>

      <dl className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <Field label="Caller" value={caller_name || <span className="text-muted">Unknown</span>} />
        <Field
          label="Phone"
          value={
            phone ? (
              <a
                href={`tel:${phone}`}
                className="tnum inline-flex items-center gap-1.5 text-primary hover:underline focus:outline-none focus:ring-2 focus:ring-accent rounded"
              >
                <Phone className="h-3.5 w-3.5" aria-hidden />
                {formatPhone(phone)}
              </a>
            ) : null
          }
        />
        <Field
          label="Email"
          value={
            email ? (
              <a
                href={`mailto:${email}`}
                className="inline-flex items-center gap-1.5 text-primary hover:underline focus:outline-none focus:ring-2 focus:ring-accent rounded"
              >
                <Mail className="h-3.5 w-3.5" aria-hidden />
                {email}
              </a>
            ) : null
          }
        />
        <Field
          label="Preferred contact"
          value={preferred_contact ? PREFERRED_LABEL[preferred_contact] : null}
        />
      </dl>
    </section>
  );
}
