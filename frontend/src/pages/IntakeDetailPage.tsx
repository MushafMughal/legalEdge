import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Clock, PhoneIncoming } from 'lucide-react';
import { getIntake } from '../lib/api';
import type { IntakeDetail } from '../lib/api';
import { formatDateTime, formatPhone } from '../lib/format';
import StatusBadge from '../components/ui/StatusBadge';
import Spinner from '../components/ui/Spinner';
import ErrorBanner from '../components/ui/ErrorBanner';
import ContactCard from '../components/intake/ContactCard';
import CaseCard from '../components/intake/CaseCard';
import PushStatusCard from '../components/intake/PushStatusCard';
import TranscriptPanel from '../components/intake/TranscriptPanel';

function formatDuration(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}m ${String(rem).padStart(2, '0')}s`;
}

const BackLink = () => (
  <Link
    to="/intakes"
    className="inline-flex items-center gap-1.5 text-sm text-muted transition hover:text-ink focus:outline-none focus:ring-2 focus:ring-accent rounded"
  >
    <ArrowLeft className="h-4 w-4" aria-hidden />
    All intakes
  </Link>
);

export default function IntakeDetailPage() {
  const { id = '' } = useParams();
  const [intake, setIntake] = useState<IntakeDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    getIntake(id)
      .then((data) => {
        if (!cancelled) setIntake(data);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load this intake.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [id, reloadKey]);

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-10 lg:px-8">
      <div className="mb-6">
        <BackLink />
      </div>

      {loading ? (
        <div className="flex justify-center py-24">
          <Spinner />
        </div>
      ) : error ? (
        <ErrorBanner
          message={`We couldn't load this intake. ${error}`}
          onRetry={() => setReloadKey((k) => k + 1)}
        />
      ) : intake ? (
        <>
          {/* Header */}
          <header className="mb-8 flex flex-col gap-3 border-b border-edge pb-6 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="flex items-center gap-3">
                <h1 className="font-display text-3xl text-ink">
                  {intake.caller_name || 'Unknown caller'}
                </h1>
                <StatusBadge status={intake.status} />
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1 text-sm text-muted">
                <span className="inline-flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5" aria-hidden />
                  Captured {formatDateTime(intake.captured_at)}
                </span>
                <span className="inline-flex items-center gap-1.5 tnum">
                  <PhoneIncoming className="h-3.5 w-3.5" aria-hidden />
                  {formatPhone(intake.call.from_number)}
                </span>
                <span className="tnum">Call length {formatDuration(intake.call.duration_seconds)}</span>
              </div>
            </div>
          </header>

          {/* Two-column grid */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
            <div className="space-y-6 lg:col-span-3">
              <ContactCard
                caller_name={intake.caller_name}
                phone={intake.phone}
                email={intake.email}
                preferred_contact={intake.preferred_contact}
              />
              <CaseCard case={intake.case} />
              <PushStatusCard push={intake.push} />
            </div>

            <div className="lg:col-span-2">
              <div className="lg:sticky lg:top-6">
                <TranscriptPanel transcript={intake.transcript} />
              </div>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
