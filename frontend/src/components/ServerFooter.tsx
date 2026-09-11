import type { Health, Stats } from '../types';

interface ServerFooterProps {
  health: Health | null;
  stats: Stats | null;
}

export function ServerFooter({ health, stats }: ServerFooterProps) {
  return (
    <footer className="rounded-lg border border-slate-300 bg-white p-5 text-sm text-slate-700 shadow-sm">
      <h2 className="text-base font-semibold text-slate-900">Server</h2>
      <dl className="mt-2 grid gap-x-6 gap-y-1 sm:grid-cols-2">
        <div className="flex justify-between gap-3 border-b border-slate-200 py-1">
          <dt>Application version</dt>
          <dd className="font-mono text-slate-900">{health?.version ?? 'not read'}</dd>
        </div>
        <div className="flex justify-between gap-3 border-b border-slate-200 py-1">
          <dt>Case-law access</dt>
          <dd className="font-mono text-slate-900">{health?.case_law_access ?? 'not read'}</dd>
        </div>
        <div className="flex justify-between gap-3 border-b border-slate-200 py-1">
          <dt>Language model</dt>
          <dd className="font-mono text-slate-900">{health?.language_model ?? 'none configured'}</dd>
        </div>
        <div className="flex justify-between gap-3 border-b border-slate-200 py-1">
          <dt>Proposition-support review</dt>
          <dd className="text-slate-900">
            {health ? (health.support_check_available ? 'available' : 'unavailable') : 'not read'}
          </dd>
        </div>
        <div className="flex justify-between gap-3 border-b border-slate-200 py-1">
          <dt>Cached upstream responses</dt>
          <dd className="tabular-nums text-slate-900">
            {stats ? stats.cached_responses : 'not read'}
          </dd>
        </div>
        <div className="flex flex-wrap justify-between gap-3 border-b border-slate-200 py-1 sm:col-span-2">
          <dt>Cache file</dt>
          <dd className="font-mono text-xs break-all text-slate-900">
            {stats?.cache_path ?? health?.cache_path ?? 'not read'}
          </dd>
        </div>
      </dl>
    </footer>
  );
}
