import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Inbox } from 'lucide-react';
import { listIntakes } from '../lib/api';
import type { IntakeSummary, IntakeStatus, PracticeArea } from '../lib/api';
import { formatDateTime, formatPhone } from '../lib/format';
import DataTable, { type Column } from '../components/ui/DataTable';
import Toolbar from '../components/ui/Toolbar';
import StatusBadge from '../components/ui/StatusBadge';
import PracticeAreaTag from '../components/ui/PracticeAreaTag';
import EmptyState from '../components/ui/EmptyState';
import ErrorBanner from '../components/ui/ErrorBanner';

type SortKey = 'captured_at' | 'caller_name' | 'status' | 'practice_area';
type Dir = 'asc' | 'desc';

const SORT_KEYS: SortKey[] = ['captured_at', 'caller_name', 'status', 'practice_area'];

function TableSkeleton() {
  return (
    <div className="overflow-hidden rounded-2xl border border-edge bg-panel shadow-sm">
      <div className="h-12 border-b border-edge bg-panel2" />
      <div className="divide-y divide-edge">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="flex h-14 items-center gap-4 px-4">
            <div className="h-4 w-40 animate-pulse rounded bg-panel2" />
            <div className="h-4 w-28 animate-pulse rounded bg-panel2" />
            <div className="h-4 w-24 animate-pulse rounded bg-panel2" />
            <div className="ml-auto h-5 w-20 animate-pulse rounded-full bg-panel2" />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function IntakesPage() {
  const [params, setParams] = useSearchParams();

  const q = params.get('q') ?? '';
  const status = params.get('status') ?? '';
  const area = params.get('area') ?? '';
  const sortParam = params.get('sort') ?? 'captured_at';
  const sort: SortKey = SORT_KEYS.includes(sortParam as SortKey)
    ? (sortParam as SortKey)
    : 'captured_at';
  const dir: Dir = params.get('dir') === 'asc' ? 'asc' : 'desc';

  const [rows, setRows] = useState<IntakeSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    listIntakes({
      q: q || undefined,
      // URL query values are plain strings; narrow to the API's enum types at
      // the call boundary. The backend validates, so unknown values are safe.
      status: (status || undefined) as IntakeStatus | undefined,
      practice_area: (area || undefined) as PracticeArea | undefined,
      sort,
      dir,
    })
      .then((data) => {
        if (!cancelled) setRows(data);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load intakes.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [q, status, area, sort, dir, reloadKey]);

  function patch(next: Record<string, string | undefined>) {
    const merged = new URLSearchParams(params);
    for (const [k, v] of Object.entries(next)) {
      if (v == null || v === '') merged.delete(k);
      else merged.set(k, v);
    }
    setParams(merged, { replace: true });
  }

  function handleSort(key: string) {
    if (!SORT_KEYS.includes(key as SortKey)) return;
    if (key === sort) {
      patch({ sort: key, dir: dir === 'asc' ? 'desc' : 'asc' });
    } else {
      patch({ sort: key, dir: key === 'captured_at' ? 'desc' : 'asc' });
    }
  }

  const columns: Column<IntakeSummary>[] = [
    {
      key: 'caller_name',
      header: 'Caller',
      sortable: true,
      render: (r) => (
        <span className="font-medium text-ink">
          {r.caller_name || <span className="text-muted">Unknown caller</span>}
        </span>
      ),
    },
    {
      key: 'phone',
      header: 'Phone',
      render: (r) => <span className="tnum text-muted">{formatPhone(r.phone)}</span>,
    },
    {
      key: 'practice_area',
      header: 'Practice area',
      sortable: true,
      render: (r) => <PracticeAreaTag area={r.practice_area} />,
    },
    {
      key: 'captured_at',
      header: 'Date / time',
      sortable: true,
      render: (r) => <span className="tnum text-muted">{formatDateTime(r.captured_at)}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      align: 'right',
      render: (r) => <StatusBadge status={r.status} />,
    },
  ];

  const hasFilters = Boolean(q || status || area);

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-10 lg:px-8">
      <header className="mb-6">
        <h1 className="font-display text-3xl text-ink">Intakes</h1>
        <p className="mt-1 text-sm text-muted">
          Every prospective-client call captured by the intake agent.
        </p>
      </header>

      <Toolbar
        q={q}
        status={status}
        practiceArea={area}
        count={rows.length}
        onChange={(p) => {
          const next: Record<string, string | undefined> = {};
          if ('q' in p) next.q = p.q;
          if ('status' in p) next.status = p.status;
          if ('practiceArea' in p) next.area = p.practiceArea;
          patch(next);
        }}
      />

      <div className="mt-6">
        {error ? (
          <ErrorBanner message={error} onRetry={() => setReloadKey((k) => k + 1)} />
        ) : loading ? (
          <TableSkeleton />
        ) : rows.length === 0 ? (
          <EmptyState
            icon={Inbox}
            title={hasFilters ? 'No matching intakes' : 'No intakes yet'}
            message={
              hasFilters
                ? 'No intakes match your current filters. Try clearing the search or filters.'
                : 'When a prospective client calls the intake line, their captured file will appear here.'
            }
          />
        ) : (
          <DataTable
            columns={columns}
            rows={rows}
            rowKey={(r) => r.id}
            rowHref={(r) => `/intakes/${r.id}`}
            sort={sort}
            dir={dir}
            onSort={handleSort}
          />
        )}
      </div>
    </div>
  );
}
