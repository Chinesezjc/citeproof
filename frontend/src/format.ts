export function formatPercent(value: number | null, digits = 1): string {
  if (value === null || Number.isNaN(value)) {
    return 'Not available';
  }
  return `${value.toFixed(digits)}%`;
}

/** Benchmark ratios arrive as 0..1 fractions. */
export function formatRatio(value: number | null, digits = 3): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'n/a';
  }
  return value.toFixed(digits);
}

/** Benchmark ratios arrive as 0..1 fractions; this states one as a percentage. */
export function formatRatioAsPercent(value: number | null, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'n/a';
  }
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatDuration(milliseconds: number): string {
  if (!Number.isFinite(milliseconds) || milliseconds < 0) {
    return 'unknown';
  }
  if (milliseconds < 1000) {
    return `${Math.round(milliseconds)} ms`;
  }
  return `${(milliseconds / 1000).toFixed(2)} s`;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return 'unknown';
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatConfidence(value: number): string {
  if (!Number.isFinite(value)) {
    return 'unknown';
  }
  return value.toFixed(2);
}

export function formatCount(value: number): string {
  return new Intl.NumberFormat().format(value);
}

export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return count === 1 ? singular : plural;
}
