import type { ChangeEvent, FormEvent } from 'react';
import type { ExampleDocument } from '../types';

interface InputPanelProps {
  text: string;
  onTextChange: (value: string) => void;
  title: string;
  onTitleChange: (value: string) => void;
  examples: ExampleDocument[];
  onLoadExample: (example: ExampleDocument) => void;
  onUpload: (file: File) => void;
  deep: boolean;
  onDeepChange: (value: boolean) => void;
  deepAvailable: boolean;
  languageModel: string | null;
  busy: boolean;
  onAudit: () => void;
  fileNotice: string | null;
}

export function InputPanel({
  text,
  onTextChange,
  title,
  onTitleChange,
  examples,
  onLoadExample,
  onUpload,
  deep,
  onDeepChange,
  deepAvailable,
  languageModel,
  busy,
  onAudit,
  fileNotice,
}: InputPanelProps) {
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onAudit();
  };

  const handleFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      onUpload(file);
    }
    event.target.value = '';
  };

  return (
    <section
      aria-labelledby="input-heading"
      className="rounded-lg border border-slate-300 bg-white p-5 shadow-sm sm:p-6"
    >
      <h2 id="input-heading" className="text-lg font-semibold text-slate-900">
        Document
      </h2>
      <p className="mt-1 text-sm text-slate-600">
        Paste the text of the brief, or upload a file. The audit extracts every citation, then
        checks each one against the CourtListener case-law corpus.
      </p>

      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        <div>
          <label htmlFor="document-text" className="block text-sm font-medium text-slate-800">
            Document text
          </label>
          <textarea
            id="document-text"
            name="document_text"
            value={text}
            onChange={(event) => onTextChange(event.target.value)}
            rows={12}
            spellCheck={false}
            aria-describedby="document-text-count"
            placeholder="Paste the full text of the document here."
            className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-sm leading-relaxed text-slate-900 shadow-inner placeholder:text-slate-400"
          />
          <p id="document-text-count" className="mt-1 text-xs text-slate-600 tabular-nums">
            {text.length.toLocaleString()} characters
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="document-title" className="block text-sm font-medium text-slate-800">
              Document title (optional)
            </label>
            <input
              id="document-title"
              name="document_title"
              type="text"
              value={title}
              onChange={(event) => onTitleChange(event.target.value)}
              placeholder="Motion to dismiss"
              className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400"
            />
          </div>

          <div>
            <label htmlFor="document-file" className="block text-sm font-medium text-slate-800">
              Upload a document
            </label>
            <input
              id="document-file"
              name="document_file"
              type="file"
              accept=".txt,.md,.docx,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={handleFile}
              aria-describedby="document-file-help"
              className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-700 file:mr-3 file:rounded file:border file:border-slate-300 file:bg-slate-50 file:px-3 file:py-1 file:text-sm file:font-medium file:text-slate-800 hover:file:bg-slate-100"
            />
            <p id="document-file-help" className="mt-1 text-xs text-slate-600">
              Accepted file types: .txt, .md, .docx. Uploading a file starts the audit immediately.
            </p>
          </div>
        </div>

        {fileNotice ? (
          <p className="rounded-md border border-slate-300 bg-slate-50 px-3 py-2 text-xs text-slate-700">
            {fileNotice}
          </p>
        ) : null}

        {examples.length > 0 ? (
          <div>
            <p id="examples-label" className="text-sm font-medium text-slate-800">
              Load an example
            </p>
            <ul aria-labelledby="examples-label" className="mt-2 flex flex-wrap gap-2">
              {examples.map((example) => (
                <li key={example.id}>
                  <button
                    type="button"
                    onClick={() => onLoadExample(example)}
                    className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-800 hover:bg-slate-100"
                  >
                    {example.title}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
          <div className="flex items-start gap-3">
            <input
              id="deep-check"
              name="deep"
              type="checkbox"
              checked={deep}
              disabled={!deepAvailable}
              onChange={(event) => onDeepChange(event.target.checked)}
              aria-describedby="deep-help"
              className="mt-0.5 h-4 w-4 rounded border-slate-400 text-blue-700 disabled:opacity-50"
            />
            <div>
              <label
                htmlFor="deep-check"
                className={`block text-sm font-medium ${deepAvailable ? 'text-slate-800' : 'text-slate-500'}`}
              >
                Also review whether each authority supports the proposition it is cited for
              </label>
              <p id="deep-help" className="mt-1 text-xs text-slate-600">
                {deepAvailable ? (
                  <>
                    This option runs one language-model call per citation
                    {languageModel ? ` using ${languageModel}` : ''}, in addition to the corpus
                    checks. It also compares any quoted language against the cited opinion.
                  </>
                ) : (
                  <>
                    Unavailable: the server has no language model configured, so the
                    proposition-support review cannot run. Quoted language is still checked against
                    the corpus.
                  </>
                )}
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={busy || text.trim().length === 0}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {busy ? 'Auditing…' : 'Audit citations'}
          </button>
          {busy ? (
            <span className="text-sm text-slate-600" role="status">
              An audit is running.
            </span>
          ) : null}
        </div>
      </form>
    </section>
  );
}
