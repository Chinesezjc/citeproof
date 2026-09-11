import type {
  AuditSummary,
  BenchmarkResponse,
  ExampleDocument,
  ExtractResult,
  Health,
  Stats,
} from './types';

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`.trim();
    try {
      const body: unknown = await response.json();
      if (body && typeof body === 'object' && 'detail' in body) {
        const raw = (body as { detail: unknown }).detail;
        if (typeof raw === 'string' && raw) {
          detail = raw;
        }
      }
    } catch {
      // The response body was not JSON; the status line is the message.
    }
    throw new ApiError(detail);
  }
  return (await response.json()) as T;
}

const jsonPost = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

export const getHealth = () => request<Health>('/api/health');

export const getExamples = () => request<ExampleDocument[]>('/api/examples');

export const getStats = () => request<Stats>('/api/stats');

export const getBenchmark = () => request<BenchmarkResponse>('/api/benchmark');

export const extractCitations = (text: string, documentTitle: string | null) =>
  request<ExtractResult>(
    '/api/extract',
    jsonPost({ text, document_title: documentTitle }),
  );

export const createAudit = (
  text: string,
  documentTitle: string | null,
  deep: boolean,
) =>
  request<AuditSummary>(
    '/api/audits',
    jsonPost({ text, document_title: documentTitle, deep }),
  );

export const createAuditFromFile = (file: File) => {
  const form = new FormData();
  form.append('file', file);
  return request<AuditSummary>('/api/audits/file', { method: 'POST', body: form });
};

export const getAudit = (auditId: string) =>
  request<AuditSummary>(`/api/audits/${encodeURIComponent(auditId)}`);

export const markdownUrl = (auditId: string) =>
  `/api/audits/${encodeURIComponent(auditId)}/markdown`;

export const jsonUrl = (auditId: string) =>
  `/api/audits/${encodeURIComponent(auditId)}/json`;

export function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return 'The request did not complete.';
}
