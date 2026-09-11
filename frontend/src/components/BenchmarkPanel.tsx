import { formatDateTime, formatDuration, formatRatio, formatRatioAsPercent } from '../format';
import type { BenchmarkAvailable, BenchmarkResponse } from '../types';

const CLASS_LABELS: Record<string, string> = {
  real: 'Real authority',
  fabricated: 'Fabricated authority',
  miscited: 'Miscited authority',
};

const CLASS_ORDER = ['real', 'fabricated', 'miscited'];

function classLabel(key: string): string {
  return CLASS_LABELS[key] ?? key;
}

function MetricTable({ summary }: { summary: BenchmarkAvailable['summary'] }) {
  const keys = CLASS_ORDER.filter((key) => key in summary.detection_metrics);
  const extraKeys = Object.keys(summary.detection_metrics).filter(
    (key) => !CLASS_ORDER.includes(key),
  );

  return (
    <div className="overflow-x-auto">
      <table className="mt-2 w-full min-w-[36rem] border-collapse text-sm">
        <caption className="sr-only">
          Precision, recall and F1 for each error class the tool reports.
        </caption>
        <thead>
          <tr className="border-b border-slate-400 text-left">
            <th scope="col" className="py-2 pr-4 font-semibold text-slate-800">
              Class
            </th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold text-slate-800">
              Precision
            </th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold text-slate-800">
              Recall
            </th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold text-slate-800">
              F1
            </th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold text-slate-800">
              True positive
            </th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold text-slate-800">
              False positive
            </th>
            <th scope="col" className="py-2 text-right font-semibold text-slate-800">
              False negative
            </th>
          </tr>
        </thead>
        <tbody>
          {[...keys, ...extraKeys].map((key) => {
            const metric = summary.detection_metrics[key];
            return (
              <tr key={key} className="border-b border-slate-200">
                <th scope="row" className="py-2 pr-4 text-left font-medium text-slate-900">
                  {classLabel(key)}
                </th>
                <td className="py-2 pr-4 text-right tabular-nums text-slate-900">
                  {formatRatio(metric.precision)}
                </td>
                <td className="py-2 pr-4 text-right tabular-nums text-slate-900">
                  {formatRatio(metric.recall)}
                </td>
                <td className="py-2 pr-4 text-right font-semibold tabular-nums text-slate-900">
                  {formatRatio(metric.f1)}
                </td>
                <td className="py-2 pr-4 text-right tabular-nums text-slate-900">
                  {metric.true_positive}
                </td>
                <td className="py-2 pr-4 text-right tabular-nums text-slate-900">
                  {metric.false_positive}
                </td>
                <td className="py-2 text-right tabular-nums text-slate-900">
                  {metric.false_negative}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function ConfusionMatrix({ summary }: { summary: BenchmarkAvailable['summary'] }) {
  const expectedRows = Object.keys(summary.confusion_matrix);
  const predictedColumns = Array.from(
    new Set([
      ...CLASS_ORDER.filter((key) => expectedRows.some((row) => key in summary.confusion_matrix[row])),
      'undecided',
    ]),
  );

  return (
    <div className="overflow-x-auto">
      <table className="mt-2 w-full min-w-[36rem] border-collapse text-sm">
        <caption className="sr-only">
          Confusion matrix. Rows are the hand-verified verdicts; columns are the verdicts the tool
          produced. Cells on the diagonal are correct verdicts.
        </caption>
        <thead>
          <tr className="border-b border-slate-400 text-left">
            <th scope="col" className="py-2 pr-4 font-semibold text-slate-800">
              Expected verdict
            </th>
            {predictedColumns.map((column) => (
              <th key={column} scope="col" className="py-2 pr-4 text-right font-semibold text-slate-800">
                Reported as {classLabel(column)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {expectedRows.map((row) => (
            <tr key={row} className="border-b border-slate-200">
              <th scope="row" className="py-2 pr-4 text-left font-medium text-slate-900">
                {classLabel(row)}
              </th>
              {predictedColumns.map((column) => {
                const value = summary.confusion_matrix[row]?.[column] ?? 0;
                const correct = row === column && value > 0;
                return (
                  <td
                    key={column}
                    className={`py-2 pr-4 text-right tabular-nums text-slate-900 ${
                      correct ? 'bg-emerald-50 font-semibold' : ''
                    }`}
                  >
                    {correct ? (
                      <span className="inline-flex items-center gap-1.5">
                        <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" aria-hidden="true">
                          <path
                            d="M3.5 8.5l3 3 6-7"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                        <span className="sr-only">correct, </span>
                        {value}
                      </span>
                    ) : (
                      value
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface BenchmarkPanelProps {
  benchmark: BenchmarkResponse | null;
  loading: boolean;
  error: string | null;
}

export function BenchmarkPanel({ benchmark, loading, error }: BenchmarkPanelProps) {
  return (
    <section
      aria-labelledby="benchmark-heading"
      className="rounded-lg border border-slate-300 bg-white p-5 shadow-sm sm:p-6"
    >
      <h2 id="benchmark-heading" className="text-lg font-semibold text-slate-900">
        Detection accuracy on the benchmark
      </h2>

      {loading && !benchmark ? (
        <p className="mt-1 text-sm text-slate-600" role="status">
          Loading benchmark results…
        </p>
      ) : null}

      {error ? <p className="mt-1 text-sm text-slate-700">{error}</p> : null}

      {benchmark && !benchmark.available ? (
        <p className="mt-1 text-sm text-slate-600">{benchmark.detail}</p>
      ) : null}

      {benchmark && benchmark.available ? (
        <>
          <p className="mt-1 text-sm text-slate-600">
            A benchmark document pairs the text of a filing with a hand-verified verdict for every
            citation in it. The tool audits each document and its findings are counted against those
            verdicts.
          </p>

          <div className="mt-4 grid gap-6 border-t border-slate-200 pt-4 lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
            <div>
              <p className="text-xs font-semibold tracking-wide text-slate-600 uppercase">
                Correct verdicts
              </p>
              <p className="mt-1 text-5xl font-semibold text-slate-900 tabular-nums">
                {formatRatioAsPercent(benchmark.summary.verdict_accuracy)}
              </p>
              <p className="mt-2 text-sm text-slate-700">
                {benchmark.summary.correct_verdicts} of {benchmark.summary.citations_found} citations
                that the extractor found and matched were given the hand-verified verdict, across{' '}
                {benchmark.summary.documents}{' '}
                {benchmark.summary.documents === 1 ? 'document' : 'documents'}.
              </p>
              <dl className="mt-3 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2 lg:grid-cols-1">
                <div className="flex justify-between gap-3 border-b border-slate-200 py-1">
                  <dt className="text-slate-700">Accuracy over decided citations</dt>
                  <dd className="font-medium tabular-nums text-slate-900">
                    {formatRatioAsPercent(benchmark.summary.verdict_accuracy_of_decided)}
                  </dd>
                </div>
                <div className="flex justify-between gap-3 border-b border-slate-200 py-1">
                  <dt className="text-slate-700">Citations expected in the corpus</dt>
                  <dd className="font-medium tabular-nums text-slate-900">
                    {benchmark.summary.citations_expected}
                  </dd>
                </div>
                <div className="flex justify-between gap-3 border-b border-slate-200 py-1">
                  <dt className="text-slate-700">Missed by the extractor</dt>
                  <dd className="font-medium tabular-nums text-slate-900">
                    {benchmark.summary.citations_missed_by_extractor}
                  </dd>
                </div>
                <div className="flex justify-between gap-3 border-b border-slate-200 py-1">
                  <dt className="text-slate-700">Left unverifiable</dt>
                  <dd className="font-medium tabular-nums text-slate-900">
                    {benchmark.summary.citations_unverifiable}
                  </dd>
                </div>
              </dl>
            </div>

            <div className="space-y-6">
              <div>
                <h3 className="text-sm font-semibold text-slate-800">Per-class detection metrics</h3>
                <MetricTable summary={benchmark.summary} />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-800">Confusion matrix</h3>
                <ConfusionMatrix summary={benchmark.summary} />
              </div>
            </div>
          </div>

          {benchmark.documents.length > 0 ? (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-slate-800">Benchmark documents</h3>
              <div className="overflow-x-auto">
                <table className="mt-2 w-full min-w-[36rem] border-collapse text-sm">
                  <caption className="sr-only">
                    Per-document results for the benchmark run.
                  </caption>
                  <thead>
                    <tr className="border-b border-slate-400 text-left">
                      <th scope="col" className="py-2 pr-4 font-semibold text-slate-800">
                        Document
                      </th>
                      <th scope="col" className="py-2 pr-4 text-right font-semibold text-slate-800">
                        Integrity
                      </th>
                      <th scope="col" className="py-2 pr-4 text-right font-semibold text-slate-800">
                        Verified
                      </th>
                      <th scope="col" className="py-2 pr-4 text-right font-semibold text-slate-800">
                        Fabricated
                      </th>
                      <th scope="col" className="py-2 pr-4 text-right font-semibold text-slate-800">
                        Miscited
                      </th>
                      <th scope="col" className="py-2 pr-4 text-right font-semibold text-slate-800">
                        Unverifiable
                      </th>
                      <th scope="col" className="py-2 pr-4 text-right font-semibold text-slate-800">
                        Duration
                      </th>
                      <th scope="col" className="py-2 text-right font-semibold text-slate-800">
                        API requests
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {benchmark.documents.map((document) => (
                      <tr key={document.id} className="border-b border-slate-200">
                        <th scope="row" className="py-2 pr-4 text-left font-medium text-slate-900">
                          <span className="block font-serif">{document.title}</span>
                          <span className="block font-mono text-xs text-slate-600">{document.id}</span>
                        </th>
                        <td className="py-2 pr-4 text-right tabular-nums text-slate-900">
                          {document.integrity_score === null
                            ? 'n/a'
                            : `${document.integrity_score.toFixed(1)}%`}
                        </td>
                        <td className="py-2 pr-4 text-right tabular-nums text-slate-900">
                          {document.counts.verified ?? 0}
                        </td>
                        <td className="py-2 pr-4 text-right tabular-nums text-slate-900">
                          {document.counts.fabricated ?? 0}
                        </td>
                        <td className="py-2 pr-4 text-right tabular-nums text-slate-900">
                          {document.counts.miscited ?? 0}
                        </td>
                        <td className="py-2 pr-4 text-right tabular-nums text-slate-900">
                          {document.counts.unverifiable ?? 0}
                        </td>
                        <td className="py-2 pr-4 text-right tabular-nums text-slate-900">
                          {formatDuration(document.duration_ms)}
                        </td>
                        <td className="py-2 text-right tabular-nums text-slate-900">
                          {document.api_requests}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}

          <p className="mt-4 text-xs text-slate-600">
            Run generated {formatDateTime(benchmark.generated_at)}. Case-law access used for the run:{' '}
            <code className="font-mono">{benchmark.access_mode}</code>. Proposition-support review:{' '}
            {benchmark.support_check_enabled ? 'enabled' : 'disabled'}.
          </p>
        </>
      ) : null}
    </section>
  );
}
