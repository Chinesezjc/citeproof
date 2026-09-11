import { jsonUrl, markdownUrl } from '../api';
import { formatDateTime, formatDuration, formatPercent, pluralize } from '../format';
import type { AuditReport, Verdict } from '../types';
import { VERDICTS, VERDICT_ORDER } from '../verdicts';

interface SummaryHeaderProps {
  report: AuditReport;
}

function CountTile({ verdict, count }: { verdict: Verdict; count: number }) {
  const presentation = VERDICTS[verdict];
  return (
    <li
      className={`flex items-center gap-2 rounded-md border px-3 py-2 ${presentation.badge}`}
      data-count={count}
    >
      {presentation.icon}
      <span className="text-sm font-semibold">{presentation.label}</span>
      <span className="ml-auto text-lg font-semibold tabular-nums">{count}</span>
    </li>
  );
}

export function SummaryHeader({ report }: SummaryHeaderProps) {
  const { counts } = report;

  return (
    <section
      aria-labelledby="summary-heading"
      className="rounded-lg border border-slate-300 bg-white p-5 shadow-sm sm:p-6"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 id="summary-heading" className="text-lg font-semibold text-slate-900">
            Audit result
          </h2>
          <p className="mt-1 truncate text-base font-serif text-slate-900" title={report.document_title ?? 'Untitled document'}>
            {report.document_title ?? 'Untitled document'}
          </p>
          <p className="mt-1 text-xs text-slate-600">
            Audit <code className="font-mono">{report.audit_id}</code>, created{' '}
            {formatDateTime(report.created_at)}, case-law access:{' '}
            <code className="font-mono">{report.access_mode}</code>
          </p>
        </div>

        <div className="flex flex-wrap gap-2 print:hidden">
          <a
            href={markdownUrl(report.audit_id)}
            className="rounded-md border border-slate-400 bg-white px-3 py-1.5 text-sm font-medium text-slate-900 hover:bg-slate-100"
          >
            Download report (Markdown)
          </a>
          <a
            href={jsonUrl(report.audit_id)}
            className="rounded-md border border-slate-400 bg-white px-3 py-1.5 text-sm font-medium text-slate-900 hover:bg-slate-100"
          >
            Download report (JSON)
          </a>
        </div>
      </div>

      <div className="mt-5 grid gap-6 border-t border-slate-200 pt-5 lg:grid-cols-[minmax(0,18rem)_minmax(0,1fr)]">
        <div>
          <p className="text-xs font-semibold tracking-wide text-slate-600 uppercase">
            Integrity score
          </p>
          <p className="mt-1 text-5xl font-semibold text-slate-900 tabular-nums">
            {report.integrity_score === null
              ? 'Not computed'
              : `${report.integrity_score.toFixed(1)}%`}
          </p>
          <p className="mt-2 text-sm text-slate-700">
            {report.integrity_score === null
              ? 'The corpus could not adjudicate any citation in this document, so no share could be computed.'
              : 'Share of checkable citations that resolved correctly: the case exists in the corpus and the reporter citation as written belongs to it. Citations the corpus could not adjudicate are excluded from this number.'}
          </p>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-slate-800">
            Verdicts for {report.findings.length}{' '}
            {pluralize(report.findings.length, 'citation')}
          </h3>
          <ul className="mt-2 grid gap-2 sm:grid-cols-2">
            {VERDICT_ORDER.map((verdict) => (
              <CountTile key={verdict} verdict={verdict} count={counts[verdict]} />
            ))}
          </ul>
          <dl className="mt-3 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
            <div className="flex justify-between gap-3 border-b border-slate-200 py-1">
              <dt className="text-slate-700">Check coverage</dt>
              <dd className="font-medium tabular-nums text-slate-900">
                {formatPercent(report.check_coverage)}
              </dd>
            </div>
            <div className="flex justify-between gap-3 border-b border-slate-200 py-1">
              <dt className="text-slate-700">Duration</dt>
              <dd className="font-medium tabular-nums text-slate-900">
                {formatDuration(report.duration_ms)}
              </dd>
            </div>
            <div className="flex justify-between gap-3 border-b border-slate-200 py-1">
              <dt className="text-slate-700">Upstream API requests</dt>
              <dd className="font-medium tabular-nums text-slate-900">{report.api_requests}</dd>
            </div>
            <div className="flex justify-between gap-3 border-b border-slate-200 py-1">
              <dt className="text-slate-700">Cached responses used</dt>
              <dd className="font-medium tabular-nums text-slate-900">{report.cache_hits}</dd>
            </div>
            {report.statute_count > 0 ? (
              <div className="flex justify-between gap-3 border-b border-slate-200 py-1 sm:col-span-2">
                <dt className="text-slate-700">Non-case authorities listed, not checked</dt>
                <dd className="font-medium tabular-nums text-slate-900">{report.statute_count}</dd>
              </div>
            ) : null}
          </dl>
          <p className="mt-2 text-xs text-slate-600">
            Check coverage is the share of extracted citations the corpus could adjudicate.
          </p>
        </div>
      </div>

      {report.notes.length > 0 ? (
        <div className="mt-5 rounded-md border border-slate-200 bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-slate-800">Notes from the audit</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
            {report.notes.map((note, index) => (
              <li key={`${index}-${note}`}>{note}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
