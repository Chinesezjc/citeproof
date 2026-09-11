#!/usr/bin/env python3
"""Audit one document from the command line.

Examples:
    python scripts/run_audit.py data/examples/avianca-style_motion_excerpt.txt
    python scripts/run_audit.py brief.txt --deep --markdown-out report.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from citeproof.config import load_settings  # noqa: E402
from citeproof.courtlistener import CourtListenerClient, ResponseCache  # noqa: E402
from citeproof.llm import LLMClient  # noqa: E402
from citeproof.report import to_markdown  # noqa: E402
from citeproof.verify import CitationVerifier, VerifierOptions  # noqa: E402


def read_document(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        import docx

        document = docx.Document(str(path))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    return path.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the citations in a legal document.")
    parser.add_argument("document", type=Path, help="Path to a .txt, .md or .docx document.")
    parser.add_argument("--deep", action="store_true", help="Also run the support check with the language model.")
    parser.add_argument("--no-quotes", action="store_true", help="Skip the quotation check.")
    parser.add_argument("--markdown-out", type=Path, help="Write the Markdown report to this path.")
    parser.add_argument("--json-out", type=Path, help="Write the JSON report to this path.")
    parser.add_argument("--quiet", action="store_true", help="Do not print progress.")
    args = parser.parse_args()

    if not args.document.is_file():
        print(f"No such document: {args.document}", file=sys.stderr)
        return 2

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

    def progress(message: str, fraction: float) -> None:
        if not args.quiet:
            print(f"[{fraction * 100:5.1f}%] {message}", file=sys.stderr)

    verifier = CitationVerifier(
        client,
        llm=llm,
        options=VerifierOptions(
            check_quotes=not args.no_quotes,
            check_support=args.deep and settings.has_llm,
            progress=progress,
        ),
    )
    text = read_document(args.document)
    report = verifier.audit(text, title=args.document.stem)
    client.close()
    cache.close()

    markdown = to_markdown(report)
    if args.markdown_out:
        args.markdown_out.write_text(markdown, encoding="utf-8")
        print(f"Wrote {args.markdown_out}", file=sys.stderr)
    if args.json_out:
        import json

        from citeproof.report import to_json

        args.json_out.write_text(
            json.dumps(to_json(report), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Wrote {args.json_out}", file=sys.stderr)

    print(markdown)
    return 0 if report.counts.fabricated == 0 and report.counts.miscited == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
