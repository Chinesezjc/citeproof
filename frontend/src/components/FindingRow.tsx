import { formatConfidence, pluralize } from '../format';
import type { Evidence, Finding, ResolvedCase } from '../types';
import {
  ERROR_CLASS_LABELS,
  QUOTE_STATUS_LABELS,
  QUOTE_STATUS_STYLES,
  SUPPORT_LABELS,
  SUPPORT_STYLES,
  VERDICTS,
} from '../verdicts';

interface FindingRowProps {
  finding: Finding;
  index: number;
  expanded: boolean;
  active: boolean;
  onToggle: (index: number) => void;
  onActiveChange: (index: number | null) => void;
  registerRow: (index: number, element: HTMLElement | null) => void;
}

function CaseRecord({
  record,
  heading,
  note,
}: {
  record: ResolvedCase;
  heading: string;
  note?: string;
}) {
  return (
    <div className="rounded-md border border-slate-300 bg-slate-50 p-3">
      <h5 className="text-xs font-semibold tracking-wide text-slate-600 uppercase">{heading}</h5>
      <p className="mt-1 font-serif text-base leading-snug text-slate-900">{record.case_name}</p>
      {note ? <p className="mt-1 text-sm text-slate-700">{note}</p> : null}
      <dl className="mt-2 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
        <div className="flex justify-between gap-3">
          <dt className="text-slate-600">Court</dt>
          <dd className="text-right text-slate-900">{record.court ?? 'not recorded'}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-slate-600">Date filed</dt>
          <dd className="text-right text-slate-900">{record.date_filed ?? 'not recorded'}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-slate-600">Cluster identifier</dt>
          <dd className="text-right font-mono text-slate-900">
            {record.cluster_id === null ? 'not recorded' : record.cluster_id}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-slate-600">Matched by</dt>
          <dd className="text-right font-mono text-slate-900">{record.source}</dd>
        </div>
      </dl>

      {record.citations.length > 0 ? (
        <div className="mt-2">
          <p className="text-xs font-semibold tracking-wide text-slate-600 uppercase">
            Reporter citations recorded by the corpus
          </p>
          <ul className="mt-1 flex flex-wrap gap-1.5">
            {record.citations.map((citation) => (
              <li
                key={citation}
                className="rounded border border-slate-300 bg-white px-2 py-0.5 font-mono text-xs text-slate-900"
              >
                {citation}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {record.snippet ? (
        <blockquote className="mt-2 border-l-2 border-slate-400 pl-3 font-serif text-sm text-slate-800">
          {record.snippet}
        </blockquote>
      ) : null}

      {record.absolute_url ? (
        <p className="mt-2">
          <a
            href={record.absolute_url}
            target="_blank"
            rel="noreferrer noopener"
            className="text-sm font-medium text-blue-800 underline underline-offset-2 hover:text-blue-900"
          >
            Open this case on CourtListener
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
        </p>
      ) : (
        <p className="mt-2 text-xs text-slate-600">
          The corpus returned no link for this case record.
        </p>
      )}
    </div>
  );
}

function MatchIndicator({ matched }: { matched: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium">
      {matched ? (
        <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" aria-hidden="true">
          <circle cx="8" cy="8" r="6.4" fill="none" stroke="currentColor" strokeWidth="1.6" />
          <path
            d="M5.2 8.2l2 2 3.6-4"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ) : (
        <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" aria-hidden="true">
          <path d="M4.6 4.6l6.8 6.8M11.4 4.6l-6.8 6.8" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      )}
      {matched ? 'matched' : 'no match'}
    </span>
  );
}

function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  if (evidence.length === 0) {
    return <p className="mt-2 text-sm text-slate-700">No upstream query was recorded for this finding.</p>;
  }
  return (
    <ol className="mt-2 space-y-2">
      {evidence.map((item, index) => (
        <li
          key={`${index}-${item.strategy}-${item.query}`}
          className="rounded-md border border-slate-300 bg-white p-3"
        >
          <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <span className="text-xs text-slate-600">
              Query {index + 1} of {evidence.length}
            </span>
            <span className="font-mono text-xs text-slate-900">{item.strategy}</span>
            <MatchIndicator matched={item.matched} />
            <span className="text-xs text-slate-700 tabular-nums">
              {item.result_count} {pluralize(item.result_count, 'result')} returned
            </span>
          </div>
          <p className="mt-1.5 rounded border border-slate-200 bg-slate-50 px-2 py-1 font-mono text-sm break-all text-slate-900">
            {item.query}
          </p>
          {item.note ? <p className="mt-1.5 text-sm text-slate-700">{item.note}</p> : null}
          {item.top ? (
            <p className="mt-1.5 text-sm text-slate-700">
              Closest record returned: <span className="font-serif text-slate-900">{item.top.case_name}</span>
              {item.top.court ? `, ${item.top.court}` : ''}
              {item.top.date_filed ? `, ${item.top.date_filed}` : ''}
              {item.top.citations.length > 0 ? ` — ${item.top.citations.join('; ')}` : ''}
            </p>
          ) : null}
        </li>
      ))}
    </ol>
  );
}

export function FindingRow({
  finding,
  index,
  expanded,
  active,
  onToggle,
  onActiveChange,
  registerRow,
}: FindingRowProps) {
  const presentation = VERDICTS[finding.verdict];
  const citation = finding.citation;
  const caseName = citation.case_name ?? citation.verbatim;
  const bodyId = `finding-body-${index}`;
  const headingId = `finding-heading-${index}`;

  return (
    <li
      id={`finding-${index}`}
      ref={(element) => registerRow(index, element)}
      className={`scroll-mt-24 rounded-md border bg-white transition-shadow ${
        active ? 'border-blue-700 ring-2 ring-blue-600' : 'border-slate-300'
      }`}
      onMouseEnter={() => onActiveChange(index)}
      onMouseLeave={() => onActiveChange(null)}
    >
      <h3 id={headingId} className="m-0">
        <button
          type="button"
          aria-expanded={expanded}
          aria-controls={bodyId}
          onClick={() => onToggle(index)}
          className="flex w-full items-start gap-3 rounded-md p-3 text-left hover:bg-slate-50"
        >
          <span
            className={`mt-0.5 inline-flex shrink-0 items-center gap-1.5 rounded border px-2 py-1 text-xs font-semibold ${presentation.badge}`}
          >
            {presentation.icon}
            {presentation.label}
          </span>

          <span className="min-w-0 flex-1">
            <span className="block font-serif text-base leading-snug text-slate-900">{caseName}</span>
            <span className="mt-0.5 block font-mono text-xs text-slate-700">{citation.verbatim}</span>
            <span className="mt-1 block text-xs text-slate-600">
              {ERROR_CLASS_LABELS[finding.error_class] ?? finding.error_class}
              {citation.kind !== 'case' ? ` — kind: ${citation.kind}` : ''}
            </span>
          </span>

          <span className="shrink-0 text-right">
            <span className="block text-xs text-slate-600">
              confidence <span className="tabular-nums">{formatConfidence(finding.confidence)}</span>
            </span>
            <span className="mt-1 inline-flex items-center gap-1 text-xs font-medium text-slate-800">
              {expanded ? 'Hide details' : 'Show details'}
              <svg
                viewBox="0 0 16 16"
                className={`h-3.5 w-3.5 transition-transform ${expanded ? 'rotate-180' : ''}`}
                aria-hidden="true"
              >
                <path
                  d="M4 6.5l4 4 4-4"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
          </span>
        </button>
      </h3>

      {expanded ? (
        <div
          id={bodyId}
          role="region"
          aria-labelledby={headingId}
          className="space-y-4 border-t border-slate-200 p-3 sm:p-4"
        >
          <div>
            <h4 className="text-xs font-semibold tracking-wide text-slate-600 uppercase">Explanation</h4>
            <p className="mt-1 text-sm text-slate-800">{finding.explanation || 'No explanation was recorded.'}</p>
          </div>

          {finding.verdict !== 'verified' ? (
            <p className="rounded-md border border-slate-300 bg-slate-50 p-2 text-xs text-slate-700">
              {presentation.definition}
            </p>
          ) : null}

          {finding.advisories.length > 0 ? (
            <div>
              <h4 className="text-xs font-semibold tracking-wide text-slate-600 uppercase">
                Advisories ({finding.advisories.length})
              </h4>
              <ul className="mt-1 space-y-1">
                {finding.advisories.map((advisory, advisoryIndex) => (
                  <li key={`${advisoryIndex}-${advisory}`} className="flex gap-2 text-sm text-slate-800">
                    <span aria-hidden="true" className="mt-2 h-1.5 w-1.5 shrink-0 bg-slate-600" />
                    <span>{advisory}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-1 text-xs text-slate-600">
                Advisories record secondary observations and do not change the verdict.
              </p>
            </div>
          ) : null}

          {finding.resolved_case ? (
            <CaseRecord
              record={finding.resolved_case}
              heading="Case matched in the corpus"
              note={
                finding.verdict === 'verified'
                  ? 'The reporter citation in the document belongs to this case.'
                  : undefined
              }
            />
          ) : (
            <p className="text-sm text-slate-700">
              The corpus returned no case record for this citation.
            </p>
          )}

          {finding.slot_owner ? (
            <CaseRecord
              record={finding.slot_owner}
              heading="Case that owns the reporter citation as written"
              note="The document attributes this reporter citation to a different case than the corpus does."
            />
          ) : null}

          {finding.suggestion ? (
            <div>
              <h4 className="text-xs font-semibold tracking-wide text-slate-600 uppercase">Suggested correction</h4>
              <p className="mt-1 rounded border border-slate-300 bg-slate-50 px-2 py-1 font-mono text-sm break-words text-slate-900">
                {finding.suggestion}
              </p>
            </div>
          ) : null}

          {finding.quote_check ? (
            <div>
              <h4 className="text-xs font-semibold tracking-wide text-slate-600 uppercase">Quoted language</h4>
              <div className="mt-1 rounded-md border border-slate-300 p-3">
                <span
                  className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-semibold ${
                    QUOTE_STATUS_STYLES[finding.quote_check.status] ?? 'border-slate-300 bg-slate-100 text-slate-800'
                  }`}
                >
                  {QUOTE_STATUS_LABELS[finding.quote_check.status] ?? finding.quote_check.status}
                </span>
                <blockquote className="mt-2 border-l-2 border-slate-400 pl-3 font-serif text-sm text-slate-900">
                  {finding.quote_check.text}
                </blockquote>
                <dl className="mt-2 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
                  <div className="flex justify-between gap-3">
                    <dt className="text-slate-600">Status value</dt>
                    <dd className="font-mono text-slate-900">{finding.quote_check.status}</dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt className="text-slate-600">Phrase hits</dt>
                    <dd className="tabular-nums text-slate-900">
                      {finding.quote_check.hits === null ? 'not counted' : finding.quote_check.hits}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-3 sm:col-span-2">
                    <dt className="text-slate-600">Case the phrase matched</dt>
                    <dd className="text-right text-slate-900">
                      {finding.quote_check.matched_case ?? 'none recorded'}
                    </dd>
                  </div>
                </dl>
                {finding.quote_check.detail ? (
                  <p className="mt-2 text-sm text-slate-700">{finding.quote_check.detail}</p>
                ) : null}
              </div>
            </div>
          ) : null}

          {finding.fidelity ? (
            <div>
              <h4 className="text-xs font-semibold tracking-wide text-slate-600 uppercase">
                Support for the cited proposition
              </h4>
              <div className="mt-1 rounded-md border border-slate-300 p-3">
                <span
                  className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-semibold ${
                    SUPPORT_STYLES[finding.fidelity.support] ?? 'border-slate-300 bg-slate-100 text-slate-800'
                  }`}
                >
                  {SUPPORT_LABELS[finding.fidelity.support] ?? finding.fidelity.support}
                </span>
                <dl className="mt-2 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
                  <div className="flex justify-between gap-3">
                    <dt className="text-slate-600">Reviewer confidence</dt>
                    <dd className="tabular-nums text-slate-900">
                      {finding.fidelity.confidence === null
                        ? 'not reported'
                        : formatConfidence(finding.fidelity.confidence)}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt className="text-slate-600">Model</dt>
                    <dd className="font-mono text-slate-900">{finding.fidelity.model ?? 'not recorded'}</dd>
                  </div>
                </dl>
                {finding.fidelity.rationale ? (
                  <p className="mt-2 text-sm text-slate-800">{finding.fidelity.rationale}</p>
                ) : null}
                {finding.fidelity.passage ? (
                  <blockquote className="mt-2 border-l-2 border-slate-400 pl-3 font-serif text-sm text-slate-800">
                    {finding.fidelity.passage}
                  </blockquote>
                ) : null}
              </div>
            </div>
          ) : null}

          <div>
            <h4 className="text-xs font-semibold tracking-wide text-slate-600 uppercase">
              Queries issued to the corpus ({finding.evidence.length})
            </h4>
            <p className="mt-1 text-xs text-slate-600">
              Every query the verification engine ran for this citation, with the number of records
              the corpus returned and how the engine scored them.
            </p>
            <EvidenceList evidence={finding.evidence} />
          </div>

          {citation.extraction_notes.length > 0 ? (
            <div>
              <h4 className="text-xs font-semibold tracking-wide text-slate-600 uppercase">
                Extraction notes
              </h4>
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-700">
                {citation.extraction_notes.map((note, noteIndex) => (
                  <li key={`${noteIndex}-${note}`}>{note}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="border-t border-slate-200 pt-3">
            <h4 className="text-xs font-semibold tracking-wide text-slate-600 uppercase">
              Citation as extracted
            </h4>
            <dl className="mt-1 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
              <div className="flex justify-between gap-3">
                <dt className="text-slate-600">Kind</dt>
                <dd className="font-mono text-slate-900">{citation.kind}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-slate-600">Volume, reporter, page</dt>
                <dd className="font-mono text-slate-900">
                  {[citation.volume, citation.reporter, citation.page].filter(Boolean).join(' ') || 'not parsed'}
                </dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-slate-600">Pin cite</dt>
                <dd className="font-mono text-slate-900">{citation.pin_cite ?? 'none'}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-slate-600">Court</dt>
                <dd className="text-right text-slate-900">
                  {citation.court ?? 'not recorded'}
                  {citation.court_source ? ` (from the ${citation.court_source})` : ''}
                </dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-slate-600">Year</dt>
                <dd className="font-mono text-slate-900">{citation.year ?? 'not recorded'}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-slate-600">Occurrences in the document</dt>
                <dd className="tabular-nums text-slate-900">{citation.occurrence_count}</dd>
              </div>
            </dl>
            {citation.context ? (
              <p className="mt-2 rounded border border-slate-200 bg-slate-50 px-2 py-1.5 font-serif text-sm text-slate-800">
                {citation.context}
              </p>
            ) : null}
          </div>
        </div>
      ) : null}
    </li>
  );
}
