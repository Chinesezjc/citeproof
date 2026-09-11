#!/usr/bin/env python3
"""Measure detection accuracy against the bundled benchmark.

Each benchmark file pairs a document with a hand-verified verdict for every
citation in it. This script audits each document, matches the produced findings
to the expected entries, and reports precision, recall and F1 for the two error
classes the tool claims to detect, plus the confusion matrix it came from.

Usage:
    python scripts/run_benchmark.py
    python scripts/run_benchmark.py --deep --out data/benchmark/results.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from citeproof.config import load_settings  # noqa: E402
from citeproof.courtlistener import CourtListenerClient, ResponseCache  # noqa: E402
from citeproof.llm import LLMClient  # noqa: E402
from citeproof.normalize import (  # noqa: E402
    normalize_case_name,
    normalize_cite_key,
)
from citeproof.verify import CitationVerifier, VerifierOptions  # noqa: E402

BENCHMARK_DIR = REPO_ROOT / "data" / "benchmark"

# The verdict vocabulary the benchmark uses, mapped onto the tool's verdicts.
_REAL = "real"
_FABRICATED = "fabricated"
_MISCITED = "miscited"

_VERDICT_TO_LABEL = {
    "verified": _REAL,
    "fabricated": _FABRICATED,
    "miscited": _MISCITED,
}

_ERROR_CLASSES = (_REAL, _FABRICATED, _MISCITED)


@dataclass
class Match:
    document_id: str
    citation: str
    expected: str
    predicted: str | None
    error_class: str | None
    confidence: float | None
    detail: str = ""


@dataclass
class Metrics:
    label: str
    true_positive: int = 0
    false_positive: int = 0
    false_negative: int = 0

    @property
    def precision(self) -> float | None:
        denominator = self.true_positive + self.false_positive
        return round(self.true_positive / denominator, 4) if denominator else None

    @property
    def recall(self) -> float | None:
        denominator = self.true_positive + self.false_negative
        return round(self.true_positive / denominator, 4) if denominator else None

    @property
    def f1(self) -> float | None:
        precision, recall = self.precision, self.recall
        if not precision or not recall:
            return 0.0 if (precision is not None and recall is not None) else None
        return round(2 * precision * recall / (precision + recall), 4)

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "true_positive": self.true_positive,
            "false_positive": self.false_positive,
            "false_negative": self.false_negative,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
        }


@dataclass
class DocumentResult:
    document_id: str
    title: str
    matches: list[Match] = field(default_factory=list)
    unmatched_findings: list[dict[str, Any]] = field(default_factory=list)
    missed_expected: list[dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0
    api_requests: int = 0
    cache_hits: int = 0
    counts: dict[str, int] = field(default_factory=dict)
    integrity_score: float | None = None


def _expected_key(entry: dict[str, Any]) -> str | None:
    key = normalize_cite_key(entry.get("volume"), entry.get("reporter"), entry.get("page"))
    return key or None


def _expected_name(entry: dict[str, Any]) -> str:
    return normalize_case_name(entry.get("case_name"))


def load_documents(directory: Path) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        if path.name == "results.json":
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "text" not in payload or "expected" not in payload:
            print(f"Skipping {path.name}: not a benchmark document.", file=sys.stderr)
            continue
        payload.setdefault("id", path.stem)
        documents.append(payload)
    return documents


def run(
    documents: list[dict[str, Any]],
    deep: bool,
    check_quotes: bool,
    quiet: bool,
) -> dict[str, Any]:
    settings = load_settings()
    cache = ResponseCache(settings.cache_path)
    client = CourtListenerClient(
        token=settings.courtlistener_token or None,
        base_url=settings.courtlistener_base_url,
        min_interval=settings.min_interval,
        max_retries=settings.max_retries,
        timeout=settings.request_timeout,
        cache=cache,
    )
    llm = (
        LLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
        )
        if settings.has_llm
        else None
    )

    results: list[DocumentResult] = []
    for document in documents:
        if not quiet:
            print(f"Auditing {document['id']} ({len(document['expected'])} expected citations)", file=sys.stderr)

        def progress(message: str, fraction: float) -> None:
            if not quiet:
                print(f"  [{fraction * 100:5.1f}%] {message}", file=sys.stderr)

        verifier = CitationVerifier(
            client,
            llm=llm,
            options=VerifierOptions(
                check_quotes=check_quotes,
                check_support=deep and settings.has_llm,
                progress=progress,
            ),
        )
        report = verifier.audit(document["text"], title=document.get("title"))
        result = DocumentResult(
            document_id=document["id"],
            title=document.get("title") or document["id"],
            duration_ms=report.duration_ms,
            api_requests=report.api_requests,
            cache_hits=report.cache_hits,
            integrity_score=report.integrity_score,
            counts={
                "verified": report.counts.verified,
                "fabricated": report.counts.fabricated,
                "miscited": report.counts.miscited,
                "unverifiable": report.counts.unverifiable,
            },
        )

        findings_by_key: dict[str, Any] = {}
        findings_by_name: dict[str, Any] = {}
        for finding in report.findings:
            if finding.citation.cite_key:
                findings_by_key.setdefault(finding.citation.cite_key, finding)
            if finding.citation.case_name:
                findings_by_name.setdefault(normalize_case_name(finding.citation.case_name), finding)

        used: set[int] = set()
        for entry in document["expected"]:
            key = _expected_key(entry)
            name = _expected_name(entry)
            finding = findings_by_key.get(key) if key else None
            if finding is None and name:
                finding = findings_by_name.get(name)
            expected_verdict = str(entry.get("verdict", "")).strip().lower()
            if finding is None:
                result.missed_expected.append(
                    {
                        "citation": entry.get("citation_verbatim"),
                        "case_name": entry.get("case_name"),
                        "expected": expected_verdict,
                    }
                )
                continue
            used.add(id(finding))
            result.matches.append(
                Match(
                    document_id=document["id"],
                    citation=finding.citation.verbatim or finding.citation.matched_text,
                    expected=expected_verdict,
                    predicted=_VERDICT_TO_LABEL.get(finding.verdict.value, finding.verdict.value),
                    error_class=finding.error_class.value,
                    confidence=finding.confidence,
                    detail=finding.explanation,
                )
            )

        for finding in report.findings:
            if id(finding) not in used:
                result.unmatched_findings.append(
                    {
                        "citation": finding.citation.verbatim,
                        "case_name": finding.citation.case_name,
                        "predicted": _VERDICT_TO_LABEL.get(
                            finding.verdict.value, finding.verdict.value
                        ),
                        "explanation": finding.explanation,
                    }
                )
        results.append(result)

    client.close()
    cache.close()

    all_matches = [match for result in results for match in result.matches]
    metrics = {
        label: Metrics(label=label)
        for label in _ERROR_CLASSES
    }
    confusion: dict[str, dict[str, int]] = {
        expected: {predicted: 0 for predicted in (*_ERROR_CLASSES, "undecided")}
        for expected in _ERROR_CLASSES
    }

    for match in all_matches:
        predicted = match.predicted or "undecided"
        if match.expected in confusion:
            confusion[match.expected][predicted] = confusion[match.expected].get(predicted, 0) + 1
        for label, metric in metrics.items():
            if match.expected == label and match.predicted == label:
                metric.true_positive += 1
            elif match.expected == label and match.predicted != label:
                metric.false_negative += 1
            elif match.expected != label and match.predicted == label:
                metric.false_positive += 1

    matched = len(all_matches)
    missed = sum(len(result.missed_expected) for result in results)
    total_expected = matched + missed
    correct = sum(1 for match in all_matches if match.expected == match.predicted)
    accurate = [
        match for match in all_matches if match.predicted is not None and match.predicted != "unverifiable"
    ]
    unverifiable = sum(1 for match in all_matches if match.predicted == "unverifiable")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "access_mode": "token" if settings.has_token else "anonymous",
        "support_check_enabled": bool(deep and settings.has_llm),
        "documents": [
            {
                "id": result.document_id,
                "title": result.title,
                "duration_ms": result.duration_ms,
                "api_requests": result.api_requests,
                "cache_hits": result.cache_hits,
                "integrity_score": result.integrity_score,
                "counts": result.counts,
                "matches": [match.__dict__ for match in result.matches],
                "unmatched_findings": result.unmatched_findings,
                "missed_expected": result.missed_expected,
            }
            for result in results
        ],
        "summary": {
            "documents": len(results),
            "citations_expected": total_expected,
            "citations_found": matched,
            "citations_missed_by_extractor": missed,
            "correct_verdicts": correct,
            "citations_decided": len(accurate),
            "citations_unverifiable": unverifiable,
            "verdict_accuracy": round(correct / matched, 4) if matched else None,
            "verdict_accuracy_of_decided": round(correct / len(accurate), 4) if accurate else None,
            "detection_metrics": {label: metric.as_dict() for label, metric in metrics.items()},
            "confusion_matrix": confusion,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure detection accuracy on the benchmark.")
    parser.add_argument("--deep", action="store_true", help="Also run the language-model support check.")
    parser.add_argument("--no-quotes", action="store_true", help="Skip the quotation check.")
    parser.add_argument(
        "--out",
        type=Path,
        default=BENCHMARK_DIR / "results.json",
        help="Where to write the results.",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    documents = load_documents(BENCHMARK_DIR)
    if not documents:
        print(
            f"No benchmark documents found in {BENCHMARK_DIR}. "
            "Each benchmark file needs a 'text' field and an 'expected' list.",
            file=sys.stderr,
        )
        return 2

    started = time.time()
    payload = run(documents, args.deep, not args.no_quotes, args.quiet)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    summary = payload["summary"]
    print(f"\nBenchmark finished in {time.time() - started:.1f}s")
    print(
        f"  expected {summary['citations_expected']} citations, "
        f"matched {summary['citations_found']}, extractor missed {summary['citations_missed_by_extractor']}"
    )
    print(
        f"  correct verdicts: {summary['correct_verdicts']}/{summary['citations_found']} "
        f"({summary['verdict_accuracy']}), {summary['citations_unverifiable']} left unverifiable"
    )
    for label, metric in summary["detection_metrics"].items():
        print(
            f"  {label:11s} precision={metric['precision']} recall={metric['recall']} f1={metric['f1']} "
            f"(tp={metric['true_positive']} fp={metric['false_positive']} fn={metric['false_negative']})"
        )
    print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
