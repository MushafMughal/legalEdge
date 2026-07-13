import { MessageSquare } from 'lucide-react';
import type { TranscriptTurn } from '../../lib/api';

type TranscriptPanelProps = { transcript: TranscriptTurn[] };

function formatTs(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}:${String(rem).padStart(2, '0')}`;
}

export default function TranscriptPanel({ transcript }: TranscriptPanelProps) {
  return (
    <section className="flex max-h-[calc(100vh-8rem)] flex-col rounded-2xl border border-edge bg-panel shadow-sm">
      <header className="flex items-center gap-2 border-b border-edge px-6 py-4">
        <MessageSquare className="h-4 w-4 text-primary" aria-hidden />
        <h2 className="font-display text-lg text-ink">Transcript</h2>
        <span className="ml-auto tnum text-xs text-muted">
          {transcript.length} turn{transcript.length === 1 ? '' : 's'}
        </span>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-5">
        {transcript.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted">No transcript recorded for this call.</p>
        ) : (
          <ol className="space-y-4">
            {transcript.map((turn, i) => {
              const isAgent = turn.speaker === 'agent';
              return (
                <li
                  key={`${turn.ts}-${i}`}
                  className="animate-[slideIn_0.2s_ease-out] flex flex-col gap-1"
                >
                  <div className="flex items-baseline gap-2">
                    <span
                      className={`text-xs font-semibold uppercase tracking-wide ${
                        isAgent ? 'text-primary' : 'text-slate'
                      }`}
                    >
                      {isAgent ? 'Agent' : 'Caller'}
                    </span>
                    <span className="tnum text-xs text-muted">{formatTs(turn.ts)}</span>
                  </div>
                  <p
                    className={`rounded-xl px-3.5 py-2.5 text-sm leading-relaxed ${
                      isAgent
                        ? 'bg-panel2 text-ink'
                        : 'bg-[#EAF1F7] text-ink'
                    }`}
                  >
                    {turn.text}
                  </p>
                </li>
              );
            })}
          </ol>
        )}
      </div>
    </section>
  );
}
