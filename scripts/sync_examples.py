#!/usr/bin/env python3
"""Copy the benchmark documents into the examples the application ships.

The demonstration documents are the benchmark documents. They are copied rather
than written by hand so that the example a reviewer clicks and the fixture the
accuracy figures are measured on cannot drift apart.

Usage:
    python scripts/sync_examples.py
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = REPO_ROOT / "data" / "benchmark"
EXAMPLES_DIR = REPO_ROOT / "data" / "examples"

# Benchmark id -> example file stem.
EXAMPLE_NAMES = {
    "avianca": "fabricated_and_miscited_citations",
    "real_brief": "all_citations_verified",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Delete example files that no longer correspond to a benchmark document.",
    )
    args = parser.parse_args()

    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    expected_names: set[str] = set()

    for path in sorted(BENCHMARK_DIR.glob("*.json")):
        if path.name == "results.json":
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "text" not in payload or "expected" not in payload:
            continue
        stem = EXAMPLE_NAMES.get(payload.get("id", path.stem), re.sub(r"[^a-z0-9]+", "_", payload.get("id", path.stem)).strip("_"))
        target = EXAMPLES_DIR / f"{stem}.txt"
        header = (
            f"{payload.get('title', stem)}\n"
            f"Source: {payload.get('source_url', 'see data/benchmark/README.md')}\n"
            f"Ground truth for every citation in this document: data/benchmark/{path.name}\n"
            "\n"
        )
        target.write_text(header + (payload["text"] or ""), encoding="utf-8")
        written.append(target)
        expected_names.add(target.name)
        print(f"wrote {target.relative_to(REPO_ROOT)}  ({len(payload['expected'])} expected citations)")

    if args.prune:
        for existing in sorted(EXAMPLES_DIR.glob("*.txt")):
            if existing.name not in expected_names:
                existing.unlink()
                print(f"removed {existing.relative_to(REPO_ROOT)} (no matching benchmark document)")

    if not written:
        print(f"No benchmark documents found in {BENCHMARK_DIR}.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
