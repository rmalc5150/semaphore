#!/usr/bin/env python3
"""Shared SEC/HKEX disclosure collection and event classification utilities."""

from __future__ import annotations

import html
import base64
import json
import os
import re
import subprocess
import time
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from decodo_scraping_api import scrape_url

S3_ROOT = "s3://processed-059416028963-us-east-1-an/corporate-disclosures/"
SEC_AGENT = os.environ.get("SEC_USER_AGENT", "AN Data Collection contact@example.com")
HKEX_SEARCH = "https://www1.hkexnews.hk/search/titlesearch.xhtml"


def get(url: str, data: bytes | None = None, agent: str = SEC_AGENT, retries: int = 3) -> bytes:
    if url.startswith("https://www1.hkexnews.hk/"):
        parameters: dict[str, Any] = {"proxy_pool": "premium", "headless": "html"}
        if data is not None:
            parameters.update({"http_method": "POST", "payload": base64.b64encode(data).decode()})
        return scrape_url(url, **parameters).encode("utf-8")
    request = Request(url, data=data, headers={"User-Agent": agent, "Accept": "*/*",
                                              **({"Content-Type": "application/x-www-form-urlencoded"} if data else {})})
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=90) as response: return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            if attempt == retries - 1: raise RuntimeError(f"request failed for {url}: {exc}") from exc
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def upload(payload: dict[str, Any], destination: str) -> str:
    process = subprocess.Popen(["aws", "s3", "cp", "-", destination, "--only-show-errors"],
                               stdin=subprocess.PIPE, text=True, encoding="utf-8")
    assert process.stdin is not None
    json.dump(payload, process.stdin, ensure_ascii=False, indent=2); process.stdin.write("\n"); process.stdin.close()
    if process.wait(): raise RuntimeError("AWS CLI upload failed")
    return destination


def read_s3(source: str) -> dict[str, Any]:
    result = subprocess.run(["aws", "s3", "cp", source, "-", "--only-show-errors"],
                            stdout=subprocess.PIPE, text=True)
    if result.returncode: raise RuntimeError(f"could not read prerequisite {source}")
    return json.loads(result.stdout)


def quarters(start: date, end: date):
    current = (start.year, (start.month - 1) // 3 + 1)
    last = (end.year, (end.month - 1) // 3 + 1)
    while current <= last:
        yield current
        current = (current[0] + (current[1] == 4), current[1] % 4 + 1)


def sec_filings(start: date, end: date) -> list[dict[str, str]]:
    records = []
    for year, quarter in quarters(start, end):
        url = f"https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{quarter}/master.idx"
        text = get(url).decode("latin-1", errors="replace")
        body = text.split("-----", 1)[-1]
        for line in body.splitlines():
            parts = line.split("|")
            if len(parts) != 5: continue
            cik, company, form, filed, filename = parts
            try: filed_date = date.fromisoformat(filed)
            except ValueError: continue
            if start <= filed_date <= end:
                records.append({"filingDate": filed, "cik": cik, "companyName": company, "form": form,
                                "filename": filename, "filingUrl": "https://www.sec.gov/Archives/" + filename})
    return sorted(records, key=lambda x: (x["filingDate"], x["cik"], x["form"], x["filename"]))


class HKEXParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(); self.rows: list[dict[str, str]] = []; self.row = None; self.field = None; self.buf = []
    def handle_starttag(self, tag, attrs):
        values = dict(attrs); classes = values.get("class", "")
        if tag == "tr": self.row = {}
        if self.row is None: return
        if tag == "td":
            self.field = ("releaseTime" if "release-time" in classes else "stockCode" if "stock-short-code" in classes
                          else "stockName" if "stock-short-name" in classes else None); self.buf = []
        elif tag == "div" and "headline" in classes: self.field = "headline"; self.buf = []
        elif tag == "a" and ".pdf" in values.get("href", "").lower():
            self.row["documentUrl"] = urljoin(HKEX_SEARCH, values["href"]); self.field = "title"; self.buf = []
    def handle_data(self, data):
        if self.row is not None and self.field: self.buf.append(data)
    def handle_endtag(self, tag):
        if self.row is None: return
        if tag in ("td", "div", "a") and self.field:
            value = " ".join(" ".join(self.buf).split())
            value = re.sub(r"^(Release Time:|Stock Code:|Stock Short Name:|Document:)\s*", "", value)
            if value: self.row[self.field] = html.unescape(value)
            self.field = None; self.buf = []
        if tag == "tr":
            if self.row.get("documentUrl"): self.rows.append(self.row)
            self.row = None


def hkex_filings(start: date, end: date) -> list[dict[str, str]]:
    all_rows: dict[str, dict[str, str]] = {}
    day = start
    while day <= end:
        for page in range(1, 101):
            params = {"lang": "EN", "market": "SEHK", "category": "0", "from": day.strftime("%Y%m%d"),
                      "to": day.strftime("%Y%m%d"), "sortDir": "0", "sortByOptions": "DateTime", "page": str(page)}
            parser = HKEXParser(); parser.feed(get(HKEX_SEARCH, urlencode(params).encode(), "Mozilla/5.0 hkex-filings/1.0").decode("utf-8", "replace"))
            before = len(all_rows)
            for row in parser.rows:
                try:
                    row["releaseTime"] = datetime.strptime(row.get("releaseTime", ""), "%d/%m/%Y %H:%M").isoformat(timespec="minutes")
                except ValueError:
                    pass
                all_rows[row["documentUrl"]] = row
            if not parser.rows or len(all_rows) == before: break
        day += timedelta(days=1)
    return sorted(all_rows.values(), key=lambda x: (x.get("releaseTime", ""), x.get("stockCode", ""), x["documentUrl"]))


EVENT_RULES = {
    "press-releases": {"keywords": ("press release", "results announcement", "annual results", "interim results",
                                      "business update", "corporate update"), "sec_forms": ("8-K", "6-K")},
    "licensing-agreements": {"keywords": ("licensing agreement", "licence agreement", "license agreement",
                                           "collaboration agreement", "exclusive license", "strategic collaboration"),
                               "sec_forms": ()},
    "ma-announcements": {"keywords": ("merger", "acquisition", "takeover", "scheme of arrangement", "tender offer",
                                       "very substantial acquisition", "disposal", "sale of subsidiary"),
                          "sec_forms": ("S-4", "S-4/A", "425", "SC 13D", "SC 13D/A", "DEFM14A")},
}


def classify(category: str, sec: list[dict[str, Any]], hkex: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rule = EVENT_RULES[category]; events = []
    for record in hkex:
        haystack = (record.get("headline", "") + " " + record.get("title", "")).lower()
        matches = [word for word in rule["keywords"] if word in haystack]
        if matches:
            events.append({"eventDate": record.get("releaseTime", "")[:10], "source": "HKEX",
                           "classification": category, "confidence": "HIGH", "matchedTerms": matches, "record": record})
    for record in sec:
        if record.get("form", "").upper() in rule["sec_forms"]:
            confidence = "MEDIUM" if category == "ma-announcements" else "LOW"
            events.append({"eventDate": record["filingDate"], "source": "SEC", "classification": category,
                           "confidence": confidence, "matchedTerms": ["form:" + record["form"]], "record": record})
    return sorted(events, key=lambda x: (x["eventDate"], x["source"], str(x["record"])))
