import { useCallback, useEffect, useState } from 'react';
import {
  createAudit,
  createAuditFromFile,
  errorMessage,
  extractCitations,
  getAudit,
  getBenchmark,
  getExamples,
  getHealth,
  getStats,
} from './api';
import { AccessNotice } from './components/AccessNotice';
import { BenchmarkPanel } from './components/BenchmarkPanel';
import { DocumentView } from './components/DocumentView';
import { FindingsList, type FocusRequest } from './components/FindingsList';
import { InputPanel } from './components/InputPanel';
import { ProgressPanel } from './components/ProgressPanel';
import { ServerFooter } from './components/ServerFooter';
import { SummaryHeader } from './components/SummaryHeader';
import type {
  AuditSummary,
  BenchmarkResponse,
  ExampleDocument,
  ExtractResult,
  Health,
  Stats,
} from './types';

type Phase = 'idle' | 'running' | 'done' | 'failed';

function stripExtension(filename: string): string {
  return filename.replace(/\.[^./\\]+$/, '').replace(/[_-]+/g, ' ').trim();
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [examples, setExamples] = useState<ExampleDocument[]>([]);
  const [benchmark, setBenchmark] = useState<BenchmarkResponse | null>(null);
  const [benchmarkError, setBenchmarkError] = useState<string | null>(null);
  const [benchmarkLoading, setBenchmarkLoading] = useState(true);

  const [text, setText] = useState('');
  const [title, setTitle] = useState('');
  const [deep, setDeep] = useState(false);
  const [fileNotice, setFileNotice] = useState<string | null>(null);

  const [auditId, setAuditId] = useState<string | null>(null);
  const [summary, setSummary] = useState<AuditSummary | null>(null);
  const [phase, setPhase] = useState<Phase>('idle');
  const [requestError, setRequestError] = useState<string | null>(null);

  const [extract, setExtract] = useState<ExtractResult | null>(null);
  const [extractPending, setExtractPending] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);

  /** Text the current audit was started from, or null when it is only known to the server. */
  const [submittedText, setSubmittedText] = useState<string | null>(null);

  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const [focusRequest, setFocusRequest] = useState<FocusRequest | null>(null);

  useEffect(() => {
    let cancelled = false;
    void getHealth()
      .then((value) => {
        if (!cancelled) setHealth(value);
      })
      .catch(() => {
        if (!cancelled) setHealth(null);
      });
    void getStats()
      .then((value) => {
        if (!cancelled) setStats(value);
      })
      .catch(() => {
        if (!cancelled) setStats(null);
      });
    void getExamples()
      .then((value) => {
        if (!cancelled) setExamples(value);
      })
      .catch(() => {
        if (!cancelled) setExamples([]);
      });
    void getBenchmark()
      .then((value) => {
        if (!cancelled) setBenchmark(value);
      })
      .catch((error: unknown) => {
        if (!cancelled) setBenchmarkError(`Benchmark results could not be read: ${errorMessage(error)}`);
      })
      .finally(() => {
        if (!cancelled) setBenchmarkLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const report = summary?.status === 'done' ? summary.report : null;

  // Poll the audit once per second until it finishes; the interval is cleared on unmount.
  useEffect(() => {
    if (!auditId) {
      return;
    }
    let cancelled = false;
    let timer: number | undefined;

    const poll = async () => {
      try {
        const next = await getAudit(auditId);
        if (cancelled) return;
        setSummary(next);
        if (next.status === 'done') {
          setPhase('done');
          void getStats()
            .then((value) => {
              if (!cancelled) setStats(value);
            })
            .catch(() => undefined);
          return;
        }
        if (next.status === 'failed') {
          setPhase('failed');
          return;
        }
      } catch (error: unknown) {
        if (!cancelled) {
          setRequestError(`The audit status could not be read: ${errorMessage(error)}`);
          setPhase('failed');
        }
        return;
      }
      timer = window.setTimeout(poll, 1000);
    };

    void poll();

    return () => {
      cancelled = true;
      if (timer !== undefined) {
        window.clearTimeout(timer);
      }
    };
  }, [auditId]);

  const resetResults = useCallback(() => {
    setSummary(null);
    setAuditId(null);
    setPhase('idle');
    setRequestError(null);
    setExtract(null);
    setExtractError(null);
    setActiveIndex(null);
    setFocusRequest(null);
  }, []);

  const runExtractPass = useCallback((documentText: string, documentTitle: string | null) => {
    setExtract(null);
    setExtractError(null);
    setExtractPending(true);
    void extractCitations(documentText, documentTitle)
      .then((value) => setExtract(value))
      .catch((error: unknown) => setExtractError(errorMessage(error)))
      .finally(() => setExtractPending(false));
  }, []);

  const startAuditFromText = useCallback(
    async (documentText: string, documentTitle: string | null) => {
      resetResults();
      setSubmittedText(documentText);
      setPhase('running');
      runExtractPass(documentText, documentTitle);
      try {
        const created = await createAudit(documentText, documentTitle, deep);
        setSummary(created);
        setAuditId(created.audit_id);
      } catch (error: unknown) {
        setRequestError(errorMessage(error));
        setPhase('failed');
      }
    },
    [deep, resetResults, runExtractPass],
  );

  const startAuditFromFile = useCallback(
    async (file: File) => {
      resetResults();
      setSubmittedText(null);
      setPhase('running');
      try {
        const created = await createAuditFromFile(file);
        setSummary(created);
        setAuditId(created.audit_id);
      } catch (error: unknown) {
        setRequestError(errorMessage(error));
        setPhase('failed');
      }
    },
    [resetResults],
  );

  const handleAudit = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed) {
      setRequestError('Enter or load a document before running an audit.');
      return;
    }
    void startAuditFromText(trimmed, title.trim() || null);
  }, [startAuditFromText, text, title]);

  const handleLoadExample = useCallback((example: ExampleDocument) => {
    setText(example.text);
    setTitle(example.title);
    setFileNotice(null);
  }, []);

  const handleUpload = useCallback(
    async (file: File) => {
      const isPlainText = /\.(txt|md|markdown)$/i.test(file.name);
      if (isPlainText) {
        const content = await file.text();
        const derivedTitle = stripExtension(file.name) || file.name;
        setText(content);
        setTitle(derivedTitle);
        setFileNotice(
          `Read ${file.name} in the browser and started the audit from that text, so the document view can mark the citations.`,
        );
        void startAuditFromText(content.trim(), derivedTitle);
        return;
      }

      setText('');
      setTitle(stripExtension(file.name) || file.name);
      setFileNotice(
        `Uploaded ${file.name} to the server, which extracted its text. The browser never sees that text, so the document view cannot mark the citations for this audit; the findings, the evidence and the exports are unaffected.`,
      );
      await startAuditFromFile(file);
    },
    [startAuditFromFile, startAuditFromText],
  );

  const findings = report?.findings ?? [];

  return (
    <div className="min-h-screen">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2 focus:text-sm focus:font-medium focus:text-slate-900"
      >
        Skip to main content
      </a>

      <header className="border-b border-slate-300 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-baseline gap-x-4 gap-y-1 px-4 py-4">
          <h1 className="font-serif text-2xl font-semibold tracking-tight text-slate-900">
            CiteProof
          </h1>
          <p className="text-sm text-slate-700">
            Extracts every citation from a legal document, checks each one against the CourtListener
            case-law corpus, and records the queries behind every verdict.
          </p>
        </div>
      </header>

      <AccessNotice health={health} />

      <main id="main" className="mx-auto max-w-5xl space-y-6 px-4 py-6">
        <InputPanel
          text={text}
          onTextChange={setText}
          title={title}
          onTitleChange={setTitle}
          examples={examples}
          onLoadExample={handleLoadExample}
          onUpload={(file) => void handleUpload(file)}
          deep={deep}
          onDeepChange={setDeep}
          deepAvailable={health?.support_check_available ?? false}
          languageModel={health?.language_model ?? null}
          busy={phase === 'running'}
          onAudit={handleAudit}
          fileNotice={fileNotice}
        />

        {requestError ? (
          <div
            role="alert"
            className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-950"
          >
            <p className="font-semibold">The request did not complete.</p>
            <p className="mt-1">{requestError}</p>
          </div>
        ) : null}

        {phase === 'failed' && summary?.status === 'failed' ? (
          <section
            aria-labelledby="failure-heading"
            role="alert"
            className="rounded-lg border border-red-300 bg-red-50 p-5 text-red-950"
          >
            <h2 id="failure-heading" className="text-lg font-semibold">
              The audit failed
            </h2>
            <p className="mt-1 text-sm">
              {summary.error ?? 'The server reported a failure without an error message.'}
            </p>
            <p className="mt-2 text-xs">
              Audit identifier <code className="font-mono">{summary.audit_id}</code>.
            </p>
          </section>
        ) : null}

        {phase === 'running' && summary ? (
          <ProgressPanel
            summary={summary}
            extract={extract}
            extractPending={extractPending}
            extractError={extractError}
          />
        ) : null}

        {phase === 'running' && !summary ? (
          <section
            aria-labelledby="starting-heading"
            className="rounded-lg border border-slate-300 bg-white p-5 shadow-sm"
          >
            <h2 id="starting-heading" className="text-lg font-semibold text-slate-900">
              Audit in progress
            </h2>
            <p className="mt-1 text-sm text-slate-700" role="status">
              Submitting the document to the audit endpoint.
            </p>
          </section>
        ) : null}

        <div className="min-h-[24rem] space-y-6">
          {report ? (
            <>
              <SummaryHeader report={report} />
              <FindingsList
                findings={findings}
                statuteCount={report.statute_count}
                activeIndex={activeIndex}
                onActiveChange={setActiveIndex}
                focusRequest={focusRequest}
              />
              <DocumentView
                text={submittedText ?? ''}
                findings={findings}
                activeIndex={activeIndex}
                onActiveChange={setActiveIndex}
                onFocusRequest={setFocusRequest}
                unavailableReason={
                  submittedText === null
                    ? 'The text of this document was extracted on the server, so the browser has no text to mark. Run the audit from pasted text or from a .txt or .md file to see the marked-up document view.'
                    : null
                }
              />
            </>
          ) : phase === 'idle' ? (
            <section className="rounded-lg border border-dashed border-slate-400 bg-white p-5 text-sm text-slate-700">
              <h2 className="text-base font-semibold text-slate-900">No audit yet</h2>
              <p className="mt-1">
                Paste a document or load an example, then select “Audit citations”. The result lists
                every citation the extractor found, the verdict for each one, and the corpus queries
                that produced it.
              </p>
            </section>
          ) : null}
        </div>

        <BenchmarkPanel
          benchmark={benchmark}
          loading={benchmarkLoading}
          error={benchmarkError}
        />

        <ServerFooter health={health} stats={stats} />
      </main>
    </div>
  );
}
