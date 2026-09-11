import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Finding } from '../types';
import { VERDICTS } from '../verdicts';
import { FindingRow } from './FindingRow';

export interface FocusRequest {
  index: number;
  nonce: number;
}

interface FindingsListProps {
  findings: Finding[];
  statuteCount: number;
  activeIndex: number | null;
  onActiveChange: (index: number | null) => void;
  focusRequest: FocusRequest | null;
}

export function FindingsList({
  findings,
  statuteCount,
  activeIndex,
  onActiveChange,
  focusRequest,
}: FindingsListProps) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const rowRefs = useRef(new Map<number, HTMLElement>());

  const registerRow = useCallback((index: number, element: HTMLElement | null) => {
    if (element) {
      rowRefs.current.set(index, element);
    } else {
      rowRefs.current.delete(index);
    }
  }, []);

  // Findings are ordered by severity; the original order is kept inside each group.
  const ordered = useMemo(() => {
    return findings
      .map((finding, index) => ({ finding, index }))
      .sort(
        (a, b) =>
          VERDICTS[a.finding.verdict].severity - VERDICTS[b.finding.verdict].severity ||
          a.index - b.index,
      );
  }, [findings]);

  const toggle = useCallback((index: number) => {
    setExpanded((previous) => {
      const next = new Set(previous);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }, []);

  useEffect(() => {
    if (!focusRequest) {
      return;
    }
    const { index } = focusRequest;
    setExpanded((previous) => new Set(previous).add(index));
    const element = rowRefs.current.get(index);
    if (element) {
      requestAnimationFrame(() => {
        element.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      });
    }
  }, [focusRequest]);

  const expandAll = () => setExpanded(new Set(findings.map((_, index) => index)));
  const collapseAll = () => setExpanded(new Set());

  if (findings.length === 0) {
    return (
      <section
        aria-labelledby="findings-heading"
        className="rounded-lg border border-slate-300 bg-white p-5 shadow-sm sm:p-6"
      >
        <h2 id="findings-heading" className="text-lg font-semibold text-slate-900">
          Findings
        </h2>
        <p className="mt-2 text-sm text-slate-700">
          No case citations were found in this document, so there is nothing to check against the
          case-law corpus.
        </p>
        {statuteCount > 0 ? (
          <p className="mt-2 text-sm text-slate-700">
            {statuteCount} non-case {statuteCount === 1 ? 'authority was' : 'authorities were'} listed
            in the document. Statutes, regulations and journal articles are not checked against the
            case-law corpus.
          </p>
        ) : null}
      </section>
    );
  }

  return (
    <section
      aria-labelledby="findings-heading"
      className="rounded-lg border border-slate-300 bg-white p-5 shadow-sm sm:p-6"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="findings-heading" className="text-lg font-semibold text-slate-900">
            Findings
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {findings.length} {findings.length === 1 ? 'citation' : 'citations'}, most severe first.
            Expanding a row shows the explanation, the case matched in the corpus and every query the
            engine ran.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={expandAll}
            className="rounded-md border border-slate-400 bg-white px-3 py-1 text-sm font-medium text-slate-900 hover:bg-slate-100"
          >
            Expand all
          </button>
          <button
            type="button"
            onClick={collapseAll}
            className="rounded-md border border-slate-400 bg-white px-3 py-1 text-sm font-medium text-slate-900 hover:bg-slate-100"
          >
            Collapse all
          </button>
        </div>
      </div>

      <ul className="mt-4 space-y-2">
        {ordered.map(({ finding, index }) => (
          <FindingRow
            key={`${finding.citation.index}-${finding.citation.cite_key ?? finding.citation.matched_text}`}
            finding={finding}
            index={index}
            expanded={expanded.has(index)}
            active={activeIndex === index}
            onToggle={toggle}
            onActiveChange={onActiveChange}
            registerRow={registerRow}
          />
        ))}
      </ul>
    </section>
  );
}
