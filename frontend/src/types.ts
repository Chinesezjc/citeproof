export type Verdict = 'verified' | 'fabricated' | 'miscited' | 'unverifiable';

export type ErrorClass =
  | 'none'
  | 'fabricated_cite'
  | 'fabricated_case_name'
  | 'wrong_slot'
  | 'wrong_court'
  | 'wrong_year'
  | 'quote_not_found'
  | 'mischaracterized'
  | 'not_checked';

export type AuditStatus =
  | 'queued'
  | 'extracting'
  | 'verifying'
  | 'checking'
  | 'done'
  | 'failed';

export type CitationKind = 'case' | 'statute' | 'regulation' | 'journal' | 'other';

export type CourtSource = 'document' | 'reporter' | null;

export type QuoteStatus =
  | 'verbatim'
  | 'variant'
  | 'not_found'
  | 'corpus_hit'
  | 'corpus_miss'
  | 'skipped';

export type SupportLevel =
  | 'supported'
  | 'partial'
  | 'not_supported'
  | 'contradicted'
  | 'unknown';

export interface ResolvedCase {
  case_name: string;
  cluster_id: number | null;
  court: string | null;
  date_filed: string | null;
  citations: string[];
  absolute_url: string | null;
  snippet: string | null;
  source: 'cite_search' | 'name_search' | 'citation_lookup' | 'opinion_text';
}

export interface Evidence {
  strategy: string;
  query: string;
  result_count: number;
  matched: boolean;
  top: ResolvedCase | null;
  note: string | null;
}

export interface QuoteCheck {
  text: string;
  status: QuoteStatus;
  hits: number | null;
  matched_case: string | null;
  detail: string | null;
}

export interface FidelityCheck {
  support: SupportLevel;
  confidence: number | null;
  rationale: string | null;
  model: string | null;
  passage: string | null;
}

export interface ExtractedCitation {
  index: number;
  verbatim: string;
  matched_text: string;
  kind: CitationKind;
  volume: string | null;
  reporter: string | null;
  page: string | null;
  pin_cite: string | null;
  court: string | null;
  court_source: CourtSource;
  year: string | null;
  case_name: string | null;
  plaintiff: string | null;
  defendant: string | null;
  parenthetical: string | null;
  cite_key: string | null;
  spans: [number, number][];
  occurrence_count: number;
  context: string;
  extraction_notes: string[];
}

export interface Finding {
  citation: ExtractedCitation;
  verdict: Verdict;
  error_class: ErrorClass;
  confidence: number;
  explanation: string;
  resolved_case: ResolvedCase | null;
  slot_owner: ResolvedCase | null;
  evidence: Evidence[];
  quote_check: QuoteCheck | null;
  fidelity: FidelityCheck | null;
  suggestion: string | null;
  advisories: string[];
}

export interface AuditCounts {
  verified: number;
  fabricated: number;
  miscited: number;
  unverifiable: number;
}

export interface AuditReport {
  audit_id: string;
  created_at: string;
  document_title: string | null;
  access_mode: 'token' | 'anonymous';
  counts: AuditCounts;
  statute_count: number;
  integrity_score: number | null;
  check_coverage: number | null;
  findings: Finding[];
  duration_ms: number;
  api_requests: number;
  cache_hits: number;
  notes: string[];
}

export interface AuditSummary {
  audit_id: string;
  status: AuditStatus;
  progress: number;
  message: string;
  citations_total: number;
  citations_done: number;
  error: string | null;
  report: AuditReport | null;
}

export interface ExtractResult {
  citations_total: number;
  case_citations: number;
  citations: ExtractedCitation[];
  notes: string[];
}

export interface Health {
  version: string;
  case_law_access: 'anonymous' | 'token';
  has_token: boolean;
  language_model: string | null;
  support_check_available: boolean;
  cache_path: string;
  time: string;
}

export interface ExampleDocument {
  id: string;
  title: string;
  text: string;
}

export interface Stats {
  cached_responses: number;
  cache_path: string;
}

export interface DetectionMetric {
  label: string;
  true_positive: number;
  false_positive: number;
  false_negative: number;
  precision: number | null;
  recall: number | null;
  f1: number | null;
}

export interface BenchmarkSummary {
  documents: number;
  citations_expected: number;
  citations_found: number;
  citations_missed_by_extractor: number;
  correct_verdicts: number;
  citations_decided: number;
  citations_unverifiable: number;
  verdict_accuracy: number | null;
  verdict_accuracy_of_decided: number | null;
  detection_metrics: Record<string, DetectionMetric>;
  confusion_matrix: Record<string, Record<string, number>>;
}

export interface BenchmarkDocument {
  id: string;
  title: string;
  duration_ms: number;
  api_requests: number;
  cache_hits: number;
  integrity_score: number | null;
  counts: Record<string, number>;
}

export interface BenchmarkAvailable {
  available: true;
  generated_at: string;
  access_mode: string;
  support_check_enabled: boolean;
  summary: BenchmarkSummary;
  documents: BenchmarkDocument[];
}

export interface BenchmarkUnavailable {
  available: false;
  detail: string;
}

export type BenchmarkResponse = BenchmarkAvailable | BenchmarkUnavailable;
