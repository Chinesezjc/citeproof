import type { ReactElement } from 'react';
import type { Verdict } from './types';

/**
 * Every verdict is identified in the interface by a word, a distinct icon
 * shape and a colour, so no statement depends on colour alone.
 */
interface VerdictPresentation {
  label: string;
  /** Sort rank: lower is more severe. */
  severity: number;
  definition: string;
  badge: string;
  swatch: string;
  documentMark: string;
  icon: ReactElement;
}

function IconVerified() {
  return (
    <svg viewBox="0 0 20 20" className="h-4 w-4 shrink-0" aria-hidden="true">
      <circle cx="10" cy="10" r="8" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M6.2 10.3l2.5 2.5 5-5.2"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function IconFabricated() {
  return (
    <svg viewBox="0 0 20 20" className="h-4 w-4 shrink-0" aria-hidden="true">
      <path
        d="M6.4 1.6h7.2l4.8 4.8v7.2l-4.8 4.8H6.4L1.6 13.6V6.4z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path
        d="M7.2 7.2l5.6 5.6M12.8 7.2l-5.6 5.6"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function IconMiscited() {
  return (
    <svg viewBox="0 0 20 20" className="h-4 w-4 shrink-0" aria-hidden="true">
      <path
        d="M10 2.2l8 14.6H2z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path d="M10 7.4v4.2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <circle cx="10" cy="14.2" r="1.1" fill="currentColor" />
    </svg>
  );
}

function IconUnverifiable() {
  return (
    <svg viewBox="0 0 20 20" className="h-4 w-4 shrink-0" aria-hidden="true">
      <circle
        cx="10"
        cy="10"
        r="7.6"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeDasharray="3.2 2.4"
      />
      <path d="M7.9 8.1a2.2 2.2 0 1 1 2.6 2.6v1.1" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="10.5" cy="14" r="1.05" fill="currentColor" />
    </svg>
  );
}

export const VERDICTS: Record<Verdict, VerdictPresentation> = {
  fabricated: {
    label: 'Fabricated',
    severity: 0,
    definition:
      'No case in the case-law corpus matches this citation, so the authority cited does not exist as written.',
    badge: 'border-red-300 bg-red-100 text-red-900',
    swatch: 'bg-red-600',
    documentMark:
      'bg-red-100 text-red-950 border-b-2 border-red-600 hover:bg-red-200',
    icon: <IconFabricated />,
  },
  miscited: {
    label: 'Miscited',
    severity: 1,
    definition:
      'A real case matches the name, but the reporter citation as written belongs to a different case.',
    badge: 'border-amber-400 bg-amber-100 text-amber-950',
    swatch: 'bg-amber-500',
    documentMark:
      'bg-amber-100 text-amber-950 border-b-2 border-amber-600 hover:bg-amber-200',
    icon: <IconMiscited />,
  },
  unverifiable: {
    label: 'Unverifiable',
    severity: 2,
    definition:
      'The corpus could not adjudicate this citation. No conclusion about the authority is drawn.',
    badge: 'border-slate-400 bg-slate-200 text-slate-900',
    swatch: 'bg-slate-500',
    documentMark:
      'bg-slate-200 text-slate-900 border-b-2 border-slate-500 hover:bg-slate-300',
    icon: <IconUnverifiable />,
  },
  verified: {
    label: 'Verified',
    severity: 3,
    definition:
      'The case exists in the corpus and the reporter citation as written belongs to it.',
    badge: 'border-emerald-300 bg-emerald-100 text-emerald-950',
    swatch: 'bg-emerald-600',
    documentMark:
      'bg-emerald-100 text-emerald-950 border-b-2 border-emerald-600 hover:bg-emerald-200',
    icon: <IconVerified />,
  },
};

export const VERDICT_ORDER: Verdict[] = ['fabricated', 'miscited', 'unverifiable', 'verified'];

export const ERROR_CLASS_LABELS: Record<string, string> = {
  none: 'No defect',
  fabricated_cite: 'Reporter citation does not exist',
  fabricated_case_name: 'Case name does not exist',
  wrong_slot: 'Reporter slot belongs to another case',
  wrong_court: 'Court in the document does not match the corpus record',
  wrong_year: 'Year in the document does not match the corpus record',
  quote_not_found: 'Quoted language is not in the cited authority',
  mischaracterized: 'Cited authority does not support the stated proposition',
  not_checked: 'Not checked against the corpus',
};

export const SUPPORT_LABELS: Record<string, string> = {
  supported: 'Supported',
  partial: 'Partially supported',
  not_supported: 'Not supported',
  contradicted: 'Contradicted',
  unknown: 'Not determined',
};

export const SUPPORT_STYLES: Record<string, string> = {
  supported: 'border-emerald-300 bg-emerald-50 text-emerald-950',
  partial: 'border-amber-300 bg-amber-50 text-amber-950',
  not_supported: 'border-red-300 bg-red-50 text-red-950',
  contradicted: 'border-red-400 bg-red-100 text-red-950',
  unknown: 'border-slate-300 bg-slate-100 text-slate-800',
};

export const QUOTE_STATUS_LABELS: Record<string, string> = {
  verbatim: 'Verbatim match in the cited authority',
  variant: 'Close variant in the cited authority',
  not_found: 'Not found in the cited authority',
  corpus_hit: 'Phrase occurs somewhere in the corpus',
  corpus_miss: 'Phrase does not occur anywhere in the corpus',
  skipped: 'Quotation check skipped',
};

export const QUOTE_STATUS_STYLES: Record<string, string> = {
  verbatim: 'border-emerald-300 bg-emerald-50 text-emerald-950',
  variant: 'border-amber-300 bg-amber-50 text-amber-950',
  not_found: 'border-red-300 bg-red-50 text-red-950',
  corpus_hit: 'border-sky-300 bg-sky-50 text-sky-950',
  corpus_miss: 'border-slate-300 bg-slate-100 text-slate-800',
  skipped: 'border-slate-300 bg-slate-100 text-slate-800',
};
