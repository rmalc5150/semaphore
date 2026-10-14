#!/usr/bin/env python3
"""News entry point: shared historical/daily modes, plus legacy ticker triplets."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FINLIGHT_URL = "https://api.finlight.me/v2/articles"
MARKETAUX_URL = "https://api.marketaux.com/v1/news/all"
S3_BUCKET = "company-specific-data-059416028963-us-east-1-an"


def safe_url(request: Request) -> str:
    """Return an error-safe URL without query parameters (which may contain credentials)."""
    return request.full_url.split("?", 1)[0]


def normalize_tickers(values: list[str]) -> list[str]:
    """Normalize comma-separated/repeated ticker arguments and remove duplicates."""
    result: list[str] = []
    for value in values:
        for ticker in value.split(","):
            ticker = ticker.strip().upper()
            if ticker and ticker not in result:
                result.append(ticker)
    if not result:
        raise ValueError("at least one ticker is required")
    return result


def parse_companies(values: list[str]) -> list[dict[str, str]]:
    """Parse repeated COMPANY EXCHANGE TICKER positional triplets."""
    if not values or len(values) % 3:
        raise ValueError("provide one or more COMPANY EXCHANGE TICKER triplets")
    companies = []
    for index in range(0, len(values), 3):
        company, exchange, ticker = (value.strip() for value in values[index:index + 3])
        if not company or not exchange or not ticker:
            raise ValueError("company, exchange, and ticker cannot be empty")
        companies.append({"company": company, "exchange": exchange.upper(), "ticker": ticker.upper()})
    return companies


def company_folder(company: str) -> str:
    """Create a stable, S3-safe folder name while keeping the company recognizable."""
    folder = re.sub(r"[^A-Za-z0-9._-]+", "-", company.strip()).strip(".-")
    if not folder:
        raise ValueError(f"company name {company!r} does not produce a valid S3 folder")
    return folder


def load_api_keys(secret_id: str, region: str) -> tuple[str, str]:
    """Read the finlight and Marketaux keys from one JSON AWS secret."""
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - deployment dependency
        raise RuntimeError("boto3 is required; install data-collection-processing/requirements.txt") from exc

    response = boto3.client("secretsmanager", region_name=region).get_secret_value(SecretId=secret_id)
    return parse_api_keys(response, secret_id)


def parse_api_keys(response: dict[str, Any], secret_id: str = "secret") -> tuple[str, str]:
    """Extract the two expected keys from a Secrets Manager response."""
    raw = response.get("SecretString")
    if raw is None:
        raw = base64.b64decode(response["SecretBinary"]).decode("utf-8")
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"secret {secret_id!r} must contain a JSON key/value object") from exc
    if not isinstance(decoded, dict):
        raise ValueError(f"secret {secret_id!r} must contain a JSON key/value object")
    required = ("finlight-api-key", "marketaux-api-key")
    missing = [field for field in required if not isinstance(decoded.get(field), str) or not decoded[field].strip()]
    if missing:
        raise ValueError(f"secret {secret_id!r} is missing: {', '.join(missing)}")
    return decoded[required[0]].strip(), decoded[required[1]].strip()


def request_json(
    request: Request, timeout: float = 30, attempts: int = 3, opener: Callable[..., Any] = urlopen
) -> dict[str, Any]:
    """Send an HTTP request, retrying throttling and transient server failures."""
    for attempt in range(attempts):
        try:
            with opener(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise RuntimeError("provider returned a non-object JSON response")
                return payload
        except HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")[:500]
            if exc.code not in {429, 500, 502, 503, 504} or attempt == attempts - 1:
                raise RuntimeError(f"{safe_url(request)}: HTTP {exc.code}: {message}") from exc
            retry_after = exc.headers.get("Retry-After")
            time.sleep(float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt)
        except URLError as exc:
            if attempt == attempts - 1:
                raise RuntimeError(f"{safe_url(request)}: {exc.reason}") from exc
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def fetch_finlight(
    api_key: str, tickers: list[str], start: datetime, end: datetime, limit: int
) -> list[dict[str, Any]]:
    articles: list[dict[str, Any]] = []
    page = 1
    while len(articles) < limit:
        page_size = min(100, limit - len(articles))
        body = json.dumps({
            "tickers": tickers,
            "from": start.isoformat(),
            "to": end.isoformat(),
            "language": "en",
            "order": "DESC",
            "pageSize": page_size,
            "page": page,
        }).encode("utf-8")
        request = Request(FINLIGHT_URL, data=body, method="POST", headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-API-KEY": api_key,
            "User-Agent": "ticker-news-collector/1.0",
        })
        batch = request_json(request).get("articles", [])
        if not isinstance(batch, list):
            raise RuntimeError("finlight response field 'articles' is not a list")
        articles.extend({"provider": "finlight", **item} for item in batch if isinstance(item, dict))
        if len(batch) < page_size:
            break
        page += 1
    return articles[:limit]


def fetch_marketaux(
    api_token: str, tickers: list[str], start: datetime, end: datetime, limit: int
) -> list[dict[str, Any]]:
    articles: list[dict[str, Any]] = []
    page = 1
    while len(articles) < limit:
        page_size = min(100, limit - len(articles))
        query = urlencode({
            "api_token": api_token,
            "symbols": ",".join(tickers),
            "filter_entities": "true",
            "language": "en",
            "published_after": start.strftime("%Y-%m-%dT%H:%M:%S"),
            "published_before": end.strftime("%Y-%m-%dT%H:%M:%S"),
            "limit": page_size,
            "page": page,
        })
        request = Request(
            f"{MARKETAUX_URL}?{query}",
            headers={"Accept": "application/json", "User-Agent": "ticker-news-collector/1.0"},
        )
        payload = request_json(request)
        batch = payload.get("data", [])
        if not isinstance(batch, list):
            raise RuntimeError("Marketaux response field 'data' is not a list")
        articles.extend({"provider": "marketaux", **item} for item in batch if isinstance(item, dict))
        returned = payload.get("meta", {}).get("returned", len(batch))
        if returned < page_size or not batch:
            break
        page += 1
    return articles[:limit]


def upload_company_news(
    payload: dict[str, Any], bucket: str = S3_BUCKET, s3_client: Any | None = None
) -> str:
    """Upload a company's news payload below its company-specific S3 folder."""
    if s3_client is None:
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - deployment dependency
            raise RuntimeError("boto3 is required; install data-collection-processing/requirements.txt") from exc
        s3_client = boto3.client("s3", region_name="us-east-1")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    exchange = company_folder(str(payload["exchange"]).upper())
    key = f"{company_folder(payload['company'])}/news/{exchange}/{stamp}.json"
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )
    return f"s3://{bucket}/{key}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "companies", nargs="+", metavar="COMPANY/EXCHANGE/TICKER",
        help='one or more triplets, e.g. "HUTCHMED" HKEX 13',
    )
    parser.add_argument("--days", type=int, default=7, help="lookback window (default: 7)")
    parser.add_argument("--limit", type=int, default=100, help="maximum articles per provider")
    parser.add_argument(
        "--region", default=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
    )
    parser.add_argument("--secret-id", default=os.getenv("API_KEYS_SECRET_ID", "newKeys"))
    parser.add_argument("--bucket", default=S3_BUCKET)
    args = parser.parse_args()
    if args.days < 1 or args.limit < 1:
        parser.error("--days and --limit must be positive")

    try:
        companies = parse_companies(args.companies)
    except ValueError as exc:
        parser.error(str(exc))
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)
    finlight_key, marketaux_key = load_api_keys(args.secret_id, args.region)
    for item in companies:
        ticker = item["ticker"]
        finlight = fetch_finlight(finlight_key, [ticker], start, end, args.limit)
        marketaux = fetch_marketaux(marketaux_key, [ticker], start, end, args.limit)
        payload = {
            **item,
            "window_start": start.isoformat(),
            "window_end": end.isoformat(),
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "counts": {"finlight": len(finlight), "marketaux": len(marketaux)},
            "articles": finlight + marketaux,
        }
        location = upload_company_news(payload, args.bucket)
        print(f"Uploaded {len(payload['articles'])} articles for {item['company']} to {location}")
    return 0


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] in {"historical", "daily"}:
        from news_collection import main as shared_main
        raise SystemExit(shared_main())
    raise SystemExit(main())
