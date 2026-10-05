"""Render actual generated reports over loopback; no external network or login."""

import argparse
import functools
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("runs"))
    parser.add_argument("--control", default="control")
    parser.add_argument("--live", default="live-report")
    parser.add_argument("--out", type=Path, default=Path("test-results/browser"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass

    handler = functools.partial(Quiet, directory=str(args.root.resolve()))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    checks = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(
                viewport={"width": 1440, "height": 1000},
                record_video_dir=str(args.out),
                record_video_size={"width": 1440, "height": 1000},
                reduced_motion="reduce",
            )
            page = context.new_page()
            errors = []
            requests = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: requests.append(request.url))
            page.goto(
                f"{base}/{args.control}/blocked-report/", wait_until="networkidle"
            )
            expect(
                page.get_by_role("heading", name="Do not ship this candidate.")
            ).to_be_visible()
            expect(
                page.get_by_text("CONTROL FIXTURES · NOT MODEL PERFORMANCE", exact=True)
            ).to_be_visible()
            expect(page.get_by_text("26/32", exact=True)).to_be_visible()
            expect(page.get_by_text("30/32", exact=True)).to_be_visible()
            page.screenshot(
                path=str(args.out / "control-overview.png"), full_page=False
            )
            page.wait_for_timeout(1200)  # Recording dwell for a human viewer.
            page.locator("#case-sync-no-deadline > summary").click()
            page.locator("#case-sync-no-deadline").scroll_into_view_if_needed()
            expect(
                page.locator("#case-sync-no-deadline").get_by_text(
                    "UNSUPPORTED_SPAN_DEADLINE", exact=False
                )
            ).to_have_count(2)
            page.screenshot(
                path=str(args.out / "critical-regression.png"), full_page=False
            )
            page.wait_for_timeout(1600)
            with page.expect_download() as download_info:
                page.get_by_role("link", name="Download JSON").click()
            download = download_info.value
            download.save_as(args.out / "downloaded-comparison.json")
            downloaded = json.loads(
                (args.out / "downloaded-comparison.json").read_text(encoding="utf-8")
            )
            assert downloaded["verdict"] == "BLOCK"
            page.goto(f"{base}/{args.control}/fixed-report/", wait_until="networkidle")
            expect(
                page.get_by_role("heading", name="This candidate meets the checks.")
            ).to_be_visible()
            page.wait_for_timeout(1000)
            checks.append(
                "Control regression blocked despite aggregate improvement; corrected control passes; JSON download matches."
            )
            page.goto(f"{base}/{args.live}/", wait_until="networkidle")
            expect(
                page.get_by_text("REAL LOCAL MODEL · SYNTHETIC INPUTS", exact=True)
            ).to_be_visible()
            live = json.loads(
                (args.root / args.live / "comparison.json").read_text(encoding="utf-8")
            )
            assert live["kind"] == "LIVE_LOCAL_MODEL"
            expect(
                page.get_by_text(
                    f"{live['candidate_pass']}/{live['total']}", exact=True
                )
            ).to_be_visible()
            page.screenshot(path=str(args.out / "live-overview.png"), full_page=False)
            page.wait_for_timeout(1400)
            page.locator("#case-sync-no-deadline > summary").click()
            page.locator("#case-sync-no-deadline").scroll_into_view_if_needed()
            page.screenshot(path=str(args.out / "live-failure.png"), full_page=False)
            page.wait_for_timeout(1600)
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(f"{base}/{args.live}/", wait_until="networkidle")
            assert page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth"
            )
            page.screenshot(path=str(args.out / "mobile.png"), full_page=False)
            page.wait_for_timeout(800)
            page.set_viewport_size({"width": 1440, "height": 1000})
            page.goto(f"{base}/{args.live}/#provenance", wait_until="networkidle")
            page.wait_for_timeout(1000)
            assert not errors, errors
            assert all(url.startswith(base + "/") for url in requests), requests
            checks.append(
                "Real model evidence rendered; desktop/mobile layout, provenance, no JS errors or external requests."
            )
            video = page.video
            context.close()
            video.save_as(str(args.out / "evaluation-demo.webm"))
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
    (args.out / "checks.json").write_text(
        json.dumps({"status": "PASS", "checks": checks}, indent=2), encoding="utf-8"
    )
    print(
        "BROWSER PASS: control and live reports; download; 390px layout; no external requests."
    )


if __name__ == "__main__":
    main()
