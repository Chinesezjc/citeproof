#!/usr/bin/env python3
"""Drive the running application and record a walkthrough video and screenshots.

The application must already be running, for example:

    python -m uvicorn citeproof.api:app --port 8000

Then:

    python scripts/record_demo.py --url http://127.0.0.1:8000 --out docs/demo

The recording is silent, so captions are rendered into the page while it runs. The
LexHack rules require the submission video to be hosted on YouTube, Vimeo or Loom, so this
artifact is a source for that upload, not a substitute for it.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]

CAPTION = """
(id => {
  let el = document.getElementById('citeproof-caption');
  if (!el) {
    el = document.createElement('div');
    el.id = 'citeproof-caption';
    document.body.appendChild(el);
  }
  el.textContent = id;
  el.style.cssText = [
    'position:fixed','left:0','right:0','bottom:0','z-index:2147483647',
    'background:rgba(15,23,42,0.94)','color:#f8fafc',
    'font:500 17px/1.45 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif',
    'padding:14px 22px','text-align:center','letter-spacing:0.01em',
    'box-shadow:0 -2px 18px rgba(15,23,42,0.35)'
  ].join(';');
})(%s)
"""


def caption(page: Page, text: str, hold_ms: int = 0) -> None:
    page.evaluate(CAPTION % repr(text).replace("'", '"', 0))
    if hold_ms:
        page.wait_for_timeout(hold_ms)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "docs" / "demo")
    parser.add_argument("--screenshots", type=Path, default=REPO_ROOT / "docs" / "screenshots")
    parser.add_argument(
        "--scale", type=float, default=2.0, help="Device scale factor for the screenshots."
    )
    parser.add_argument(
        "--no-video",
        action="store_true",
        help="Take screenshots without recording a video. Faster, and produces smaller output.",
    )
    parser.add_argument(
        "--full-page",
        action="store_true",
        help="Capture the whole page rather than the viewport. Produces much larger images.",
    )
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.screenshots.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context_kwargs = {
            "viewport": {"width": 1440, "height": 860},
            "device_scale_factor": args.scale,
        }
        if not args.no_video:
            context_kwargs["record_video_dir"] = str(args.out / "raw")
            context_kwargs["record_video_size"] = {"width": 1440, "height": 860}
        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        started = time.monotonic()
        page.goto(args.url, wait_until="networkidle")
        page.wait_for_timeout(800)

        def shot(name: str) -> None:
            page.screenshot(path=str(args.screenshots / name), full_page=args.full_page)

        caption(page, "CiteProof audits the citations in a legal document. In 2023 a filing cited six decisions that did not exist.", 6000)
        shot("01-input.png")

        caption(page, "Loading the Avianca fixture: the citations from that filing, with real authorities mixed in.", 2500)
        page.get_by_role("button", name="fabricated and miscited citations").click()
        page.wait_for_timeout(1200)
        shot("02-example-loaded.png")

        caption(page, "Each case citation costs two requests to the case-law corpus. Without an API token those requests are paced.", 1500)
        page.get_by_role("button", name="Audit citations").click()
        page.wait_for_timeout(2500)
        shot("03-progress.png")

        page.wait_for_timeout(3000)
        caption(page, "Fifteen citations. Seven do not exist. Three exist but are cited with a citation that belongs to another case.", 6000)
        shot("04-report-summary.png")

        caption(page, "Expanding a finding shows the queries behind the verdict and how many results each returned.", 1500)
        page.get_by_role("button", name="Expand all").click()
        page.wait_for_timeout(2500)
        shot("05-findings-evidence.png")

        caption(page, "Petersen v. Iran Air does not exist, but its citation number is held by United States v. ISS Marine Services. Resolving by citation number alone would call this verified.", 8000)
        page.mouse.wheel(0, 1500)
        page.wait_for_timeout(2500)
        shot("06-slot-occupancy.png")

        caption(page, "A tool that flags real citations is worse than no tool. The second fixture contains only real, correctly cited authorities.", 5000)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(400)
        page.get_by_role("button", name="all citations verified").click()
        page.wait_for_timeout(1000)
        page.get_by_role("button", name="Audit citations").click()
        page.wait_for_timeout(5000)
        caption(page, "Fourteen citations, integrity 100 per cent, and not one accusation.", 6000)
        shot("07-negative-control.png")

        caption(page, "Accuracy is measured. Precision for real citations is 1.000: no correct authority was ever accused.", 6000)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2500)
        shot("08-benchmark.png")

        caption(page, "When a citation cannot be confirmed and nothing contradicts it, the report says so instead of guessing.", 5000)
        caption(page, "Repository: github.com/Chinesezjc/citeproof", 4000)

        video_path = page.video.path() if page.video else None
        elapsed = time.monotonic() - started
        context.close()
        browser.close()

    if video_path:
        # Playwright writes the video under a generated name inside the raw
        # directory. It is published under a stable name so that the path the
        # documentation refers to is deterministic.
        published = args.out / "citeproof-walkthrough.webm"
        source = Path(video_path)
        if not source.is_file():
            candidates = sorted((args.out / "raw").glob("*.webm"), key=lambda f: f.stat().st_mtime)
            source = candidates[-1] if candidates else source
        if source.is_file():
            published.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(published))
            shutil.rmtree(args.out / "raw", ignore_errors=True)
            print(f"video recorded at {published}")
        else:
            print(f"playwright reported a video at {video_path}, which is not present")
        print(f"recording window: {elapsed:.1f} s ({elapsed / 60:.2f} min)")
    print(f"screenshots written to {args.screenshots}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
