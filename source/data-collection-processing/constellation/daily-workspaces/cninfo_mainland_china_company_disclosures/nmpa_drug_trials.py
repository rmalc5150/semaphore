#!/usr/bin/env python3
"""Fetch NMPA drug trials first disclosed during a day or month.

The NMPA Drug Clinical Trial Registration and Information Disclosure Platform
does not publish a developer API.  This client browses the official public
search/detail pages with Chromium and streams JSON directly to S3.

Examples:
    python nmpa_drug_trials.py day 2026-08-07
    python nmpa_drug_trials.py month 2026-08
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from datetime import date
from typing import Any
from urllib.parse import urljoin

from chictr_studies import (
    TableParser,
    parse_date,
    parse_registry_date,
    period_bounds,
    upload_to_s3,
)
from decodo_scraping_api import DEFAULT_SECRET_ID, load_token, scrape_content


BASE_URL = "https://www.chinadrugtrials.org.cn/"
SEARCH_URL = urljoin(BASE_URL, "clinicaltrials.searchlist.dhtml")
# Reuse the China-registry egress proxy unless explicitly overridden.
DEFAULT_PROXY_SECRET_ID = "data-collection/chictr-proxy"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
CTR_NUMBER = re.compile(r"\bCTR20\d{6,}\b", re.I)


def parse_search_page(document: str) -> list[dict[str, Any]]:
    """Extract trial summaries from the registry's result table."""
    parser = TableParser()
    parser.feed(document)
    trials: list[dict[str, Any]] = []
    for row in parser.rows:
        row_text = " | ".join(cell["text"] for cell in row)
        number_match = CTR_NUMBER.search(row_text)
        if not number_match:
            continue
        links = [link for cell in row for link in cell["links"] if link.get("href")]
        detail_link = next(
            (
                link
                for link in links
                if "detail" in link["href"].lower()
                or number_match.group(0).lower() in link["href"].lower()
            ),
            links[0] if links else None,
        )
        if not detail_link:
            continue
        dated_cells = [
            (cell, parsed)
            for cell in row
            if (parsed := parse_registry_date(cell["text"])) is not None
        ]
        if not dated_cells:
            continue
        # The search table's public-disclosure date is its rightmost date column.
        public_date = dated_cells[-1][1]
        linked_cell = next(
            (cell for cell in row if detail_link in cell["links"]),
            None,
        )
        title = detail_link.get("title") or (linked_cell["text"] if linked_cell else "")
        trials.append(
            {
                "registrationNumber": number_match.group(0).upper(),
                "firstPublicDisclosureDate": public_date.isoformat(),
                "title": title,
                "detailUrl": urljoin(BASE_URL, detail_link["href"]),
                "searchResultColumns": [cell["text"] for cell in row],
            }
        )
    return trials


def parse_detail_page(document: str) -> list[dict[str, Any]]:
    """Preserve all labeled fields and links from an NMPA trial record."""
    parser = TableParser()
    parser.feed(document)
    fields: list[dict[str, Any]] = []
    for row in parser.rows:
        if len(row) < 2:
            continue
        # Basic-information rows contain two independent th/td pairs.
        # Preserve the disclosure date and status under their own labels.
        if len(row) >= 4 and len(row) % 2 == 0 and all(
                row[i].get("tag") == "th" and row[i + 1].get("tag") == "td" for i in range(0, len(row), 2)):
            for i in range(0, len(row), 2):
                label, value = row[i]["text"].strip(" ：:"), row[i + 1]["text"]
                if label and value:
                    field = {"label": label, "value": value}
                    links = [urljoin(BASE_URL, link["href"]) for link in row[i + 1]["links"] if link.get("href")]
                    if links:
                        field["links"] = links
                    fields.append(field)
            continue
        label = row[0]["text"].strip(" ：:")
        value = " | ".join(cell["text"] for cell in row[1:] if cell["text"])
        if not label or not value or label == value:
            continue
        field: dict[str, Any] = {"label": label, "value": value}
        links = [urljoin(BASE_URL, link["href"]) for cell in row[1:] for link in cell["links"]]
        if links:
            field["links"] = links
        fields.append(field)
    return fields


class NMPABrowser:
    def __init__(self, token: str, delay: float) -> None:
        self.delay = delay
        self.token = token
        self._last_request = 0.0
        self._page_number = 1

    def _pace(self) -> None:
        remaining = self.delay - (time.monotonic() - self._last_request)
        if remaining > 0:
            time.sleep(remaining)

    def load(self, url: str) -> str:
        self._pace()
        try:
            document = scrape_content(
                url, self.token, proxy_pool="premium", headless="html", geo="China"
            )
            self._last_request = time.monotonic()
            lowered = document.lower()
            if "验证码" in document or "request has been blocked" in lowered:
                raise RuntimeError("NMPA requested verification; retry later or use another approved proxy")
            return document
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"could not load NMPA page {url}: {exc}") from exc

    def next_page(self) -> str | None:
        """Render the next registry page using Decodo browser click actions."""
        self._page_number += 1
        self._pace()
        try:
            actions = []
            for _ in range(self._page_number - 1):
                actions.extend([
                    {"type": "click", "selector": {"type": "text", "value": "下一页"}, "on_error": "error"},
                    {"type": "wait", "wait_time_s": 2},
                ])
            document = scrape_content(
                SEARCH_URL, self.token, proxy_pool="premium", headless="html",
                geo="China", browser_actions=actions,
            )
            self._last_request = time.monotonic()
        except Exception as exc:
            raise RuntimeError(f"could not advance the NMPA result page: {exc}") from exc
        if "验证码" in document or "request has been blocked" in document.lower():
            raise RuntimeError("NMPA requested verification while paginating")
        return document

    def close(self) -> None:
        pass


def fetch_trials(
    start: date,
    end: date,
    token: str,
    delay: float,
) -> list[dict[str, Any]]:
    browser = NMPABrowser(token, delay)
    try:
        summaries: dict[str, dict[str, Any]] = {}
        document: str | None = browser.load(SEARCH_URL)
        page_number = 1
        while document is not None:
            page_trials = parse_search_page(document)
            if not page_trials:
                raise RuntimeError(f"NMPA result page {page_number} contained no parseable trials")
            dates = [date.fromisoformat(item["firstPublicDisclosureDate"]) for item in page_trials]
            for trial, public_date in zip(page_trials, dates):
                if start <= public_date <= end:
                    summaries[trial["registrationNumber"]] = trial
            # Results are newest-first; later pages cannot re-enter the period.
            if min(dates) < start:
                break
            document = browser.next_page()
            page_number += 1

        trials: list[dict[str, Any]] = []
        for summary in sorted(
            summaries.values(), key=lambda item: item["firstPublicDisclosureDate"]
        ):
            summary["fields"] = parse_detail_page(browser.load(summary["detailUrl"]))
            trials.append(summary)
        return trials
    finally:
        browser.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch NMPA drug trials first disclosed during a day or month."
    )
    parser.add_argument("period", choices=("day", "month"))
    parser.add_argument("date", type=parse_date, help="YYYY-MM-DD (or YYYY-MM for month)")
    parser.add_argument("--s3-key", help="S3 object name (default: nmpa_PERIOD_START_END.json)")
    parser.add_argument("--delay", type=float, default=3.0, help="seconds between requests")
    parser.add_argument(
        "--proxy",
        default=os.environ.get("NMPA_PROXY"),
        help="proxy URL override (or set NMPA_PROXY)",
    )
    parser.add_argument(
        "--proxy-secret-id",
        default=DEFAULT_SECRET_ID,
        help=f"Secrets Manager Decodo token secret (default: {DEFAULT_SECRET_ID})",
    )
    return parser.parse_args()


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in {"historical", "daily"}:
        from regulatory_collection import main as shared_main
        return shared_main('nmpa', sys.argv[1:])
    args = parse_args()
    if args.delay < 0:
        raise SystemExit("--delay must be zero or greater")
    start, end = period_bounds(args.period, args.date)
    object_name = args.s3_key or f"nmpa_{args.period}_{start}_{end}.json"
    try:
        token = load_token(args.proxy_secret_id, os.getenv("AWS_REGION", "us-east-1"))
        trials = fetch_trials(start, end, token, args.delay)
        payload = {
            "registry": "NMPA Drug Clinical Trial Registration and Information Disclosure Platform",
            "source": SEARCH_URL,
            "period": args.period,
            "dateField": "firstPublicDisclosureDate",
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "trialCount": len(trials),
            "trials": trials,
        }
        destination = upload_to_s3(payload, object_name)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(
        f"Uploaded {len(trials):,} NMPA trials first disclosed {start} through {end} "
        f"to {destination}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
