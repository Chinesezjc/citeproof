import type { AuditStatus, AuditSummary, ExtractResult } from '../types';
import { pluralize } from '../format';

const STATUS_LABELS: Record<AuditStatus, string> = {
  queued: 'Queued',
  extracting: 'Extracting citations',
  verifying: 'Checking citations against the corpus',
  checking: 'Running quotation and support checks',
  done: 'Done',
  failed: 'Failed',
};

interface ProgressPanelProps {
  summary: AuditSummary;
  extract: ExtractResult | null;
  extractPending: boolean;
  extractError: string | null;
}

export function ProgressPanel({
  summary,
  extract,
  extractPending,
  extractError,
}: ProgressPanelProps) {
  const percent = Math.max(0, Math.min(100, Math.round(summary.progress * 100)));

  return (
    <section
      aria-labelledby="progress-heading"
      className="rounded-lg border border-slate-300 bg-white p-5 shadow-sm sm:p-6"
    >
      <h2 id="progress-heading" className="text-lg font-semibold text-slate-900">
        Audit in progress
      </h2>

      <div className="mt-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <p className="text-sm font-medium text-slate-800">
            {STATUS_LABELS[summary.status]} — status <code className="font-mono">{summary.status}</code>
          </p>
          <p className="text-sm text-slate-700 tabular-nums">{percent}%</p>
        </div>
        <div
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
          aria-valuetext={`${percent}% — ${summary.message || STATUS_LABELS[summary.status]}`}
          aria-labelledby="progress-heading"
          className="mt-2 h-2.5 w-full overflow-hidden rounded-full border border-slate-300 bg-slate-200"
        >
          <div
            className="h-full bg-slate-800 transition-[width] duration-300"
            style={{ width: `${percent}%` }}
          />
        </div>
        <p className="mt-2 min-h-5 text-sm text-slate-700" aria-live="polite">
          {summary.message}
        </p>
      </div>

      <dl className="mt-4 grid gap-4 sm:grid-cols-2">
        <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
          <dt className="text-xs font-semibold tracking-wide text-slate-600 uppercase">
            Citations extracted
          </dt>
          <dd className="mt-1 text-sm text-slate-800">
            {extract ? (
              <>
                <span className="text-xl font-semibold tabular-nums">{extract.case_citations}</span>{' '}
                case {pluralize(extract.case_citations, 'citation')} out of{' '}
                <span className="tabular-nums">{extract.citations_total}</span>{' '}
                {pluralize(extract.citations_total, 'citation string')} found in the document.
              </>
            ) : extractError ? (
              <span className="text-red-900">
                The extraction pass did not complete: {extractError}
              </span>
            ) : (
              <span className="text-slate-600">
                {extractPending ? 'Running the offline extraction pass…' : 'Not started.'}
              </span>
            )}
          </dd>
        </div>

        <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
          <dt className="text-xs font-semibold tracking-wide text-slate-600 uppercase">
            Citations checked
          </dt>
          <dd className="mt-1 text-sm text-slate-800">
            <span className="text-xl font-semibold tabular-nums">{summary.citations_done}</span> of{' '}
            <span className="tabular-nums">{summary.citations_total}</span>
          </dd>
        </div>
      </dl>

      {extract && extract.citations.length > 0 ? (
        <div className="mt-4">
          <h3 className="text-sm font-medium text-slate-800">Extracted citations</h3>
          <ul className="mt-2 space-y-1">
            {extract.citations.map((citation) => (
              <li
                key={`${citation.index}-${citation.matched_text}`}
                className="flex flex-wrap items-baseline gap-x-3 border-l-2 border-slate-300 pl-3 text-sm"
              >
                <span className="font-serif text-slate-900">
                  {citation.case_name ?? citation.verbatim}
                </span>
                <span className="font-mono text-xs text-slate-700">{citation.matched_text}</span>
                <span className="text-xs text-slate-600">
                  kind: {citation.kind}
                  {citation.court ? `, court: ${citation.court}` : ''}
                  {citation.year ? `, year: ${citation.year}` : ''}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <p className="mt-4 text-xs text-slate-600">
        Audit identifier <code className="font-mono">{summary.audit_id}</code>. The page requests the
        status of this audit once per second until it finishes.
      </p>
    </section>
  );
}
