import type { Finding } from './types';

/**
 * The citation offsets reported by the API are positions in the document text
 * after every whitespace run has been collapsed to a single space and the
 * result trimmed. This is that transformation, and it must stay byte-for-byte
 * identical to the server's `normalize_document_text`.
 */
export function normalizeDocumentText(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
}

export interface DocumentSegment {
  text: string;
  /** Index of the finding whose span covers this segment, or null for plain prose. */
  findingIndex: number | null;
}

/**
 * Split the normalised document into plain and highlighted segments.
 *
 * Spans arrive sorted by citation, and a citation can have several. A span that
 * overlaps one already placed is dropped rather than duplicated, so every
 * character of the document belongs to at most one highlight.
 */
export function buildDocumentSegments(
  normalizedText: string,
  findings: Finding[],
): DocumentSegment[] {
  interface Mark {
    start: number;
    end: number;
    findingIndex: number;
  }

  const marks: Mark[] = [];
  findings.forEach((finding, findingIndex) => {
    for (const span of finding.citation.spans ?? []) {
      const [rawStart, rawEnd] = span;
      const start = Math.max(0, Math.min(rawStart, normalizedText.length));
      const end = Math.max(start, Math.min(rawEnd, normalizedText.length));
      if (end > start) {
        marks.push({ start, end, findingIndex });
      }
    }
  });

  marks.sort((a, b) => a.start - b.start || a.end - b.end);

  const segments: DocumentSegment[] = [];
  let cursor = 0;
  for (const mark of marks) {
    if (mark.start < cursor) {
      continue;
    }
    if (mark.start > cursor) {
      segments.push({
        text: normalizedText.slice(cursor, mark.start),
        findingIndex: null,
      });
    }
    segments.push({
      text: normalizedText.slice(mark.start, mark.end),
      findingIndex: mark.findingIndex,
    });
    cursor = mark.end;
  }
  if (cursor < normalizedText.length) {
    segments.push({ text: normalizedText.slice(cursor), findingIndex: null });
  }
  return segments;
}
