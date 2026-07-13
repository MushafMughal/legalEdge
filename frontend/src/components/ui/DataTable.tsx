import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

/** Sort direction shared with the URL query state. */
export type SortDir = 'asc' | 'desc';

export interface Column<T> {
  /** Unique column id; also the sort key sent to `onSort` unless `sortKey` overrides. */
  key: string;
  /** Header content. */
  header: ReactNode;
  /** Cell renderer. */
  render: (row: T) => ReactNode;
  /** When true the header becomes a sort toggle. */
  sortable?: boolean;
  /** Sort key sent to `onSort` (defaults to `key`). */
  sortKey?: string;
  /** Text alignment. Default 'left'. */
  align?: 'left' | 'right' | 'center';
  /** Extra classes applied to both header and body cells. */
  className?: string;
  /** Fixed/hint width (e.g. '10rem'). */
  width?: string;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  /** Stable key per row. */
  rowKey: (row: T) => string;
  /** Active sort key. */
  sort?: string;
  /** Active sort direction. */
  dir?: SortDir;
  /** Called with a column's sort key when its header is toggled. */
  onSort?: (key: string) => void;
  /** Makes the whole row interactive (pointer, hover, keyboard). */
  onRowClick?: (row: T) => void;
  /**
   * Renders each row as a link to the returned href (client-side navigation).
   * Takes precedence over `onRowClick` for making the row interactive.
   */
  rowHref?: (row: T) => string;
  /** Loading → render shimmering skeleton rows instead of data. */
  loading?: boolean;
  /** Skeleton row count while loading. Default 6. */
  skeletonRows?: number;
  /** Rendered in place of the table body when there are no rows and not loading. */
  emptyContent?: ReactNode;
  className?: string;
}

const alignClass = { left: 'text-left', right: 'text-right', center: 'text-center' } as const;

function Caret({ active, dir }: { active: boolean; dir?: SortDir }) {
  return (
    <span className="ml-1 inline-flex flex-col leading-[0]" aria-hidden="true">
      <svg width="8" height="5" viewBox="0 0 8 5" className="-mb-px">
        <path d="M4 0 8 5H0Z" fill={active && dir === 'asc' ? 'var(--color-accent)' : 'currentColor'} opacity={active && dir === 'asc' ? 1 : 0.35} />
      </svg>
      <svg width="8" height="5" viewBox="0 0 8 5">
        <path d="M4 5 0 0h8Z" fill={active && dir === 'desc' ? 'var(--color-accent)' : 'currentColor'} opacity={active && dir === 'desc' ? 1 : 0.35} />
      </svg>
    </span>
  );
}

export default function DataTable<T>({
  columns,
  rows,
  rowKey,
  sort,
  dir,
  onSort,
  onRowClick,
  rowHref,
  loading = false,
  skeletonRows = 6,
  emptyContent,
  className = '',
}: DataTableProps<T>) {
  const linkable = Boolean(rowHref);
  const clickable = !linkable && Boolean(onRowClick);
  const interactive = linkable || clickable;

  return (
    <div className={`overflow-x-auto rounded-2xl border border-edge bg-panel shadow-sm ${className}`}>
      <table className="w-full border-collapse text-sm">
        <thead className="sticky top-0 z-10">
          <tr className="bg-panel2 text-muted">
            {columns.map((col) => {
              const active = col.sortable && sort === (col.sortKey ?? col.key);
              const a = alignClass[col.align ?? 'left'];
              return (
                <th
                  key={col.key}
                  scope="col"
                  style={col.width ? { width: col.width } : undefined}
                  className={`h-11 border-b border-edge px-4 text-xs font-semibold uppercase tracking-wide ${a} ${col.className ?? ''}`}
                  aria-sort={active ? (dir === 'asc' ? 'ascending' : 'descending') : undefined}
                >
                  {col.sortable && onSort ? (
                    <button
                      type="button"
                      onClick={() => onSort(col.sortKey ?? col.key)}
                      className={`inline-flex items-center rounded transition-colors hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent ${active ? 'text-ink' : ''} ${col.align === 'right' ? 'flex-row-reverse' : ''}`}
                    >
                      {col.header}
                      <Caret active={Boolean(active)} dir={dir} />
                    </button>
                  ) : (
                    col.header
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {loading &&
            Array.from({ length: skeletonRows }).map((_, i) => (
              <tr key={`sk-${i}`} className="border-b border-edge/70 last:border-0">
                {columns.map((col) => (
                  <td key={col.key} className={`h-14 px-4 ${alignClass[col.align ?? 'left']}`}>
                    <span className="block h-3.5 w-2/3 animate-pulse rounded bg-panel2" />
                  </td>
                ))}
              </tr>
            ))}

          {!loading &&
            rows.map((row, i) => {
              const href = rowHref?.(row);
              return (
                <tr
                  key={rowKey(row)}
                  onClick={clickable ? () => onRowClick!(row) : undefined}
                  onKeyDown={
                    clickable
                      ? (e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            onRowClick!(row);
                          }
                        }
                      : undefined
                  }
                  tabIndex={clickable ? 0 : undefined}
                  role={clickable ? 'link' : undefined}
                  style={{ animationDelay: `${Math.min(i, 12) * 20}ms` }}
                  className={`animate-[fadeIn_.25s_ease-both] border-b border-edge/70 last:border-0 ${
                    href ? 'relative' : ''
                  } ${
                    interactive
                      ? 'cursor-pointer transition-colors hover:bg-panel2/60 focus-within:bg-panel2/60 focus:outline-none focus-visible:bg-panel2/60 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent'
                      : ''
                  }`}
                >
                  {columns.map((col, ci) => (
                    <td
                      key={col.key}
                      className={`h-14 px-4 align-middle text-ink ${alignClass[col.align ?? 'left']} ${col.className ?? ''}`}
                    >
                      {href && ci === 0 && (
                        <Link
                          to={href}
                          className="absolute inset-0 rounded-2xl focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent"
                          aria-label="View row details"
                        />
                      )}
                      {col.render(row)}
                    </td>
                  ))}
                </tr>
              );
            })}
        </tbody>
      </table>

      {!loading && rows.length === 0 && emptyContent != null && <div className="p-2">{emptyContent}</div>}
    </div>
  );
}
