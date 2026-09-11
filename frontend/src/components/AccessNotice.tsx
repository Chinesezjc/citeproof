import type { Health } from '../types';

interface AccessNoticeProps {
  health: Health | null;
}

/**
 * Persistent notice about how the server reaches the case-law corpus.
 * Anonymous access changes what the tool can check, so the state is always visible.
 */
export function AccessNotice({ health }: AccessNoticeProps) {
  if (!health || health.case_law_access !== 'anonymous') {
    return null;
  }

  return (
    <div className="border-b border-amber-300 bg-amber-50">
      <div className="mx-auto flex max-w-5xl gap-3 px-4 py-3">
        <svg viewBox="0 0 20 20" className="mt-0.5 h-5 w-5 shrink-0 text-amber-900" aria-hidden="true">
          <circle cx="10" cy="10" r="8" fill="none" stroke="currentColor" strokeWidth="1.8" />
          <path d="M10 5.6v5.2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          <circle cx="10" cy="14.1" r="1.05" fill="currentColor" />
        </svg>
        <div className="text-sm text-amber-950">
          <p className="font-semibold">
            Case-law access: anonymous. The server is running without a CourtListener API token.
          </p>
          <p className="mt-1">
            Two effects on the audit. Upstream requests are paced with a minimum interval between
            them, so a document with many citations takes longer to check. Opinion text cannot be
            read, so quoted language is compared against a phrase search of the whole corpus rather
            than against the text of the cited opinion. Case lookup by name and by reporter citation
            works as usual. Setting <code className="font-mono">COURTLISTENER_TOKEN</code> on the
            server switches the run to token access.
          </p>
        </div>
      </div>
    </div>
  );
}
