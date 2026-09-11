import { useMemo } from 'react';
import { buildDocumentSegments, normalizeDocumentText } from '../normalize';
import type { Finding } from '../types';
import { VERDICTS, VERDICT_ORDER } from '../verdicts';
import type { FocusRequest } from './FindingsList';

interface DocumentViewProps {
  text: string;
  findings: Finding[];
  activeIndex: number | null;
  onActiveChange: (index: number | null) => void;
  onFocusRequest: (request: FocusRequest) => void;
  /** Set when the audited text is not available in the browser, for example an uploaded .docx. */
  unavailableReason: string | null;
}

export function DocumentView({
  text,
  findings,
  activeIndex,
  onActiveChange,
  onFocusRequest,
  unavailableReason,
}: DocumentViewProps) {
  const normalized = useMemo(() => normalizeDocumentText(text), [text]);
  const segments = useMemo(
    () => buildDocumentSegments(normalized, findings),
    [normalized, findings],
  );
  const highlightedCount = segments.filter((segment) => segment.findingIndex !== null).length;
  const spanCount = findings.reduce((total, finding) => total + finding.citation.spans.length, 0);

  return (
    <section
      aria-labelledby="document-heading"
      className="rounded-lg border border-slate-300 bg-white p-5 shadow-sm sm:p-6"
    >
      <h2 id="document-heading" className="text-lg font-semibold text-slate-900">
        Document with citations marked
      </h2>
      <p className="mt-1 text-sm text-slate-600">
        The text below is the submitted document with every run of whitespace collapsed to a single
        space and the ends trimmed. That is the text the offsets reported by the API refer to.{' '}
        {highlightedCount} of {spanCount} reported citation {spanCount === 1 ? 'position' : 'positions'}{' '}
        {highlightedCount === 1 ? 'is' : 'are'} marked. Moving the pointer over a mark, or activating
        it, opens the matching finding.
      </p>

      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-2" aria-label="Legend for citation marks">
        {VERDICT_ORDER.map((verdict) => {
          const presentation = VERDICTS[verdict];
          return (
            <li key={verdict} className="flex items-center gap-1.5 text-xs text-slate-800">
              <span
                aria-hidden="true"
                className={`inline-block h-3.5 w-3.5 rounded-sm border border-slate-400 ${presentation.swatch}`}
              />
              <span className="inline-flex items-center gap-1">
                {presentation.icon}
                {presentation.label}
              </span>
            </li>
          );
        })}
      </ul>

      {unavailableReason ? (
        <p className="mt-3 rounded-md border border-slate-300 bg-slate-50 p-3 text-sm text-slate-700">
          {unavailableReason}
        </p>
      ) : (
        <p className="doc-text mt-4 rounded-md border border-slate-200 bg-slate-50 p-4 text-slate-900">
          {segments.map((segment, index) => {
            if (segment.findingIndex === null) {
              return <span key={index}>{segment.text}</span>;
            }
            const findingIndex = segment.findingIndex;
            const finding = findings[findingIndex];
            const presentation = VERDICTS[finding.verdict];
            const isActive = activeIndex === findingIndex;
            return (
              <button
                key={index}
                type="button"
                className={`cursor-pointer rounded-sm border-0 p-0 font-serif text-left text-inherit ${presentation.documentMark} ${
                  isActive ? 'outline outline-2 outline-offset-1 outline-blue-700' : ''
                }`}
                title={`${presentation.label}: ${finding.citation.case_name ?? finding.citation.verbatim}`}
                aria-label={`${presentation.label} citation: ${finding.citation.case_name ?? finding.citation.verbatim}. Open the matching finding.`}
                onMouseEnter={() => {
                  onActiveChange(findingIndex);
                  onFocusRequest({ index: findingIndex, nonce: Date.now() });
                }}
                onFocus={() => onActiveChange(findingIndex)}
                onBlur={() => onActiveChange(null)}
                onClick={() => {
                  onActiveChange(findingIndex);
                  onFocusRequest({ index: findingIndex, nonce: Date.now() });
                }}
              >
                {segment.text}
              </button>
            );
          })}
        </p>
      )}
    </section>
  );
}
