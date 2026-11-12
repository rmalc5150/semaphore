#!/usr/bin/env python3
"""Fetch ChiCTR trials registered during a day, week, or month and upload to S3.

ChiCTR does not provide a public API.  This client uses its official public
search and trial-detail HTML pages, spaces requests to reduce load, and never
writes the resulting JSON to local disk.

Examples:
    python chictr_studies.py day 2026-08-07
    python chictr_studies.py week 2026-08-03
    python chictr_studies.py month 2026-07 --s3-key chictr/2026-07.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import date, timedelta
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import unquote, urlencode, urljoin, urlsplit, urlunsplit

from decodo_scraping_api import DEFAULT_SECRET_ID, load_token, scrape_content


BASE_URL = "https://www.chictr.org.cn/"
SEARCH_URL = urljoin(BASE_URL, "searchproj.html")
S3_PREFIX = "s3://processed-059416028963-us-east-1-an/clinical-trials/"
DEFAULT_PROXY_SECRET_ID = "data-collection/chictr-proxy"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(f"{value}-01" if len(value) == 7 else value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid date {value!r}; use YYYY-MM-DD (or YYYY-MM for a month)"
        ) from exc


def period_bounds(period: str, selected: date) -> tuple[date, date]:
    if period == "day":
        return selected, selected
    if period == "week":
        start = selected - timedelta(days=selected.weekday())
        return start, start + timedelta(days=6)
    start = selected.replace(day=1)
    following = (
        start.replace(year=start.year + 1, month=1)
        if start.month == 12
        else start.replace(month=start.month + 1)
    )
    return start, following - timedelta(days=1)


def clean_text(parts: list[str]) -> str:
    return " ".join("".join(parts).replace("\xa0", " ").split())


class TableParser(HTMLParser):
    """Collect top-level cells from every HTML table row."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[dict[str, Any]]] = []
        self._row: list[dict[str, Any]] | None = None
        self._cell: dict[str, Any] | None = None
        self._cell_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "tr" and self._row is None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            if self._cell is None:
                self._cell = {"text": [], "links": [], "tag": tag}
                self._cell_depth = 1
            else:
                self._cell_depth += 1
        elif tag == "a" and self._cell is not None:
            self._cell["links"].append(
                {"href": attributes.get("href", ""), "title": attributes.get("title", "")}
            )
        elif tag == "br" and self._cell is not None:
            self._cell["text"].append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._cell is not None:
            self._cell_depth -= 1
            if self._cell_depth == 0:
                self._cell["text"] = clean_text(self._cell["text"])
                assert self._row is not None
                self._row.append(self._cell)
                self._cell = None
        elif tag == "tr" and self._row is not None and self._cell is None:
            if self._row:
                self.rows.append(self._row)
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell["text"].append(data)


def parse_registry_date(value: str) -> date | None:
    match = re.search(r"(20\d{2})[/.\-](\d{1,2})[/.\-](\d{1,2})", value)
    if not match:
        return None
    try:
        return date(*(int(part) for part in match.groups()))
    except ValueError:
        return None


def parse_search_page(document: str) -> tuple[list[dict[str, Any]], int | None]:
    parser = TableParser()
    parser.feed(document)
    trials: list[dict[str, Any]] = []
    for row in parser.rows:
        if len(row) < 5:
            continue
        link = next(
            (
                link
                for cell in row
                for link in cell["links"]
                if re.search(r"(?:showproj|showproject).*?(?:proj|id)=\d+", link["href"], re.I)
            ),
            None,
        )
        if not link:
            continue
        id_match = re.search(r"(?:proj|id)=(\d+)", link["href"])
        regno = next(
            (cell["text"] for cell in row if re.search(r"ChiCTR[A-Za-z0-9-]*\d{5,}", cell["text"])),
            "",
        )
        registered = parse_registry_date(row[-1]["text"])
        if not id_match or not regno or not registered:
            continue
        title_cell = next((cell for cell in row if link in cell["links"]), row[2])
        trials.append(
            {
                "registrationNumber": re.search(r"ChiCTR[A-Za-z0-9-]*\d{5,}", regno).group(0),
                "projectId": id_match.group(1),
                "title": link.get("title") or title_cell["text"],
                "studyType": row[-2]["text"],
                "registrationDate": registered.isoformat(),
                "detailUrl": urljoin(BASE_URL, link["href"]),
            }
        )

    visible_text = unescape(re.sub(r"<[^>]+>", " ", document))
    page_match = re.search(r"共\s*(\d+)\s*页", visible_text)
    return trials, int(page_match.group(1)) if page_match else None


def parse_detail_page(document: str) -> list[dict[str, Any]]:
    """Return all labelled fields without imposing a brittle fixed schema."""
    parser = TableParser()
    parser.feed(document)
    fields: list[dict[str, Any]] = []
    for row in parser.rows:
        if len(row) < 2:
            continue
        label = row[0]["text"].strip(" ：:")
        value = " | ".join(cell["text"] for cell in row[1:] if cell["text"])
        if label and value and label != value:
            links = [urljoin(BASE_URL, link["href"]) for cell in row[1:] for link in cell["links"]]
            field: dict[str, Any] = {"label": label, "value": value}
            if links:
                field["links"] = links
            fields.append(field)
    return fields


def proxy_settings(value: str) -> dict[str, str]:
    """Convert a proxy URL, including optional URL credentials, for Playwright."""
    value = value.strip()
    if not value:
        raise RuntimeError("the ChiCTR proxy value is empty")
    parsed = urlsplit(value)
    if not parsed.scheme or not parsed.hostname:
        raise RuntimeError("the ChiCTR proxy must be a URL such as http://host:port")
    hostname = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
    netloc = f"{hostname}:{parsed.port}" if parsed.port else hostname
    settings = {"server": urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))}
    if parsed.username is not None:
        settings["username"] = unquote(parsed.username)
    if parsed.password is not None:
        settings["password"] = unquote(parsed.password)
    return settings


def load_proxy(secret_id: str | None, explicit_proxy: str | None) -> dict[str, str] | None:
    """Resolve an override or retrieve the configured proxy from Secrets Manager."""
    if explicit_proxy:
        return proxy_settings(explicit_proxy)
    if not secret_id:
        return None
    try:
        completed = subprocess.run(
            [
                "aws",
                "secretsmanager",
                "get-secret-value",
                "--secret-id",
                secret_id,
                "--query",
                "SecretString",
                "--output",
                "text",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("AWS CLI is not installed or is not on PATH") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or f"exit code {exc.returncode}"
        raise RuntimeError(f"could not retrieve proxy secret {secret_id!r}: {detail}") from exc

    secret = completed.stdout.strip()
    try:
        decoded = json.loads(secret)
    except json.JSONDecodeError:
        return proxy_settings(secret)
    if isinstance(decoded, str):
        return proxy_settings(decoded)
    if not isinstance(decoded, dict):
        raise RuntimeError(f"proxy secret {secret_id!r} must contain a URL or JSON object")
    if "decodo" in decoded and not any(
        decoded.get(key) for key in ("server", "proxy", "url", "username", "password")
    ):
        raise RuntimeError(
            f"proxy secret {secret_id!r} contains only a Decodo API key; proxy traffic "
            "requires server, username, and password (the API key cannot authenticate requests)"
        )
    server = decoded.get("server") or decoded.get("proxy") or decoded.get("url")
    if not isinstance(server, str):
        raise RuntimeError(f"proxy secret {secret_id!r} JSON has no server, proxy, or url")
    settings = proxy_settings(server)
    for key in ("username", "password"):
        if decoded.get(key) is not None:
            settings[key] = str(decoded[key])
    if bool(settings.get("username")) != bool(settings.get("password")):
        raise RuntimeError(
            f"proxy secret {secret_id!r} must contain both username and password"
        )
    return settings


class ChiCTRClient:
    def __init__(self, delay: float, token: str) -> None:
        self.delay = delay
        self._requested = False
        self.token = token

    def close(self) -> None:
        pass

    def get(self, url: str, retries: int = 3) -> str:
        if self._requested and self.delay:
            time.sleep(self.delay + random.uniform(0, min(1.0, self.delay / 2)))
        self._requested = True
        for attempt in range(retries):
            try:
                document = scrape_content(
                    url, self.token, proxy_pool="premium", headless="html", geo="China"
                )
                lowered = document.lower()
                if "<title>405</title>" in lowered:
                    raise RuntimeError(
                        "ChiCTR blocked the Decodo-rendered request"
                    )
                if "滑动验证码" in document or "request has been blocked" in lowered:
                    raise RuntimeError(
                        "ChiCTR blocked the request or requested verification; retry later "
                        "or run from an approved network"
                    )
                return document
            except RuntimeError:
                raise
            except Exception as exc:
                if attempt == retries - 1:
                    raise RuntimeError(f"could not load ChiCTR in Chromium: {exc}") from exc
                time.sleep(2**attempt)
        raise AssertionError("unreachable")


def fetch_trials(start: date, end: date, delay: float, token: str) -> list[dict[str, Any]]:
    client = ChiCTRClient(delay, token)
    try:
        summaries: dict[str, dict[str, Any]] = {}
        for year in range(start.year, end.year + 1):
            page = 1
            total_pages: int | None = None
            while total_pages is None or page <= total_pages:
                url = f"{SEARCH_URL}?{urlencode({'page': page, 'btngo': 'btn', 'createyear': year})}"
                page_trials, found_pages = parse_search_page(client.get(url))
                if total_pages is None:
                    total_pages = found_pages
                if not page_trials:
                    if page == 1:
                        raise RuntimeError("ChiCTR search returned no parseable trials")
                    break
                for trial in page_trials:
                    registered = date.fromisoformat(trial["registrationDate"])
                    if start <= registered <= end:
                        summaries[trial["registrationNumber"]] = trial
                page_dates = [date.fromisoformat(trial["registrationDate"]) for trial in page_trials]
                # ChiCTR lists newest registrations first.  Once a page crosses the
                # requested start date, all later pages are outside the period.
                if page_dates and min(page_dates) < start:
                    break
                page += 1

        trials: list[dict[str, Any]] = []
        for summary in sorted(summaries.values(), key=lambda item: item["registrationDate"]):
            summary["fields"] = parse_detail_page(client.get(summary["detailUrl"]))
            trials.append(summary)
        return trials
    finally:
        client.close()


def upload_to_s3(payload: dict[str, Any], object_name: str) -> str:
    if not object_name or object_name.endswith("/"):
        raise RuntimeError("--s3-key must name a JSON object")
    destination = f"{S3_PREFIX}{object_name.lstrip('/')}"
    try:
        process = subprocess.Popen(
            ["aws", "s3", "cp", "-", destination, "--only-show-errors"],
            stdin=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
    except FileNotFoundError as exc:
        raise RuntimeError("AWS CLI is not installed or is not on PATH") from exc
    assert process.stdin is not None
    try:
        json.dump(payload, process.stdin, ensure_ascii=False, indent=2)
        process.stdin.write("\n")
        process.stdin.close()
    except BrokenPipeError:
        pass
    return_code = process.wait()
    if return_code:
        raise RuntimeError(f"AWS CLI upload failed with exit code {return_code}")
    return destination


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch ChiCTR trials registered during a calendar day, week, or month."
    )
    parser.add_argument("period", choices=("day", "week", "month"))
    parser.add_argument("date", type=parse_date, help="YYYY-MM-DD (or YYYY-MM for month)")
    parser.add_argument("--s3-key", help="S3 object name (default: chictr_PERIOD_START_END.json)")
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="minimum seconds between ChiCTR requests (default: 3)",
    )
    parser.add_argument(
        "--proxy",
        default=os.environ.get("CHICTR_PROXY"),
        help="proxy URL override (or set CHICTR_PROXY)",
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
        return shared_main('chictr', sys.argv[1:])
    args = parse_args()
    if args.delay < 0:
        raise SystemExit("--delay must be zero or greater")
    start, end = period_bounds(args.period, args.date)
    object_name = args.s3_key or f"chictr_{args.period}_{start}_{end}.json"
    try:
        token = load_token(args.proxy_secret_id, os.getenv("AWS_REGION", "us-east-1"))
        trials = fetch_trials(start, end, args.delay, token)
        payload = {
            "registry": "Chinese Clinical Trial Registry (ChiCTR)",
            "source": SEARCH_URL,
            "period": args.period,
            "dateField": "registrationDate",
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "trialCount": len(trials),
            "trials": trials,
        }
        destination = upload_to_s3(payload, object_name)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Uploaded {len(trials):,} ChiCTR trials registered {start} through {end} to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
