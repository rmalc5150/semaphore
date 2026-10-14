#!/usr/bin/env python3
"""Fetch IBKR historical news for an HKEX stock and write JSON to S3."""

from __future__ import annotations

import argparse
import json
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3

try:
    from ibapi.client import EClient
    from ibapi.contract import Contract
    from ibapi.wrapper import EWrapper
except ImportError as exc:  # pragma: no cover - depends on IBKR's separately installed SDK
    raise SystemExit(
        "IBKR's official Python API is not installed. Install it from the TWS API "
        "download (source/pythonclient), then retry."
    ) from exc


def normalize_symbol(value: str) -> str:
    value = value.strip()
    if not value.isdigit() or len(value) > 5:
        raise ValueError("HKEX symbol must contain 1-5 digits (for example 700 or 00700)")
    return value.zfill(5)


def ibkr_symbol(value: str) -> str:
    """IBKR normally represents HKEX stock 00700 as symbol 700."""
    return str(int(normalize_symbol(value)))


def clean_article_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()


class NewsApp(EWrapper, EClient):
    def __init__(self) -> None:
        EClient.__init__(self, self)
        self.ready = threading.Event()
        self.contract_done = threading.Event()
        self.providers_done = threading.Event()
        self.headlines_done = threading.Event()
        self.articles_done = threading.Event()
        self.contracts: list[Any] = []
        self.providers: list[Any] = []
        self.headlines: list[dict[str, Any]] = []
        self.articles: dict[int, dict[str, Any]] = {}
        self.errors: list[tuple[int, int, str]] = []
        self._expected_articles = 0

    def nextValidId(self, orderId: int) -> None:  # noqa: N802
        self.ready.set()

    def contractDetails(self, reqId: int, details: Any) -> None:  # noqa: N802
        self.contracts.append(details)

    def contractDetailsEnd(self, reqId: int) -> None:  # noqa: N802
        self.contract_done.set()

    def newsProviders(self, providers: list[Any]) -> None:  # noqa: N802
        self.providers = list(providers)
        self.providers_done.set()

    def historicalNews(  # noqa: N802
        self, reqId: int, timestamp: str, providerCode: str, articleId: str, headline: str
    ) -> None:
        self.headlines.append({
            "published_at": timestamp,
            "provider_code": providerCode,
            "article_id": articleId,
            "headline": headline,
        })

    def historicalNewsEnd(self, reqId: int, hasMore: bool) -> None:  # noqa: N802
        self.headlines_done.set()

    def newsArticle(self, reqId: int, articleType: int, articleText: str) -> None:  # noqa: N802
        self.articles[reqId] = {
            "article_type": articleType,
            "body": clean_article_text(articleText) if articleType == 0 else articleText,
        }
        if len(self.articles) >= self._expected_articles:
            self.articles_done.set()

    def error(self, reqId: int, errorCode: int, errorString: str, *args: Any) -> None:
        # Common status notifications are informational, not request failures.
        if errorCode not in {2104, 2106, 2107, 2108, 2158}:
            self.errors.append((reqId, errorCode, errorString))


def wait_for(event: threading.Event, seconds: int, operation: str, app: NewsApp) -> None:
    if not event.wait(seconds):
        details = f"; IBKR errors: {app.errors}" if app.errors else ""
        raise TimeoutError(f"timed out while waiting for {operation}{details}")


def fetch_news(config: dict[str, Any], symbol: str, days: int, limit: int) -> dict[str, Any]:
    app = NewsApp()
    app.connect(config.get("ib_host", "127.0.0.1"), int(config["ib_port"]), int(config.get("client_id", 91)))
    thread = threading.Thread(target=app.run, daemon=True)
    thread.start()
    try:
        wait_for(app.ready, 15, "IBKR connection", app)
        contract = Contract()
        contract.symbol = ibkr_symbol(symbol)
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.primaryExchange = "SEHK"
        contract.currency = "HKD"
        app.reqContractDetails(100, contract)
        wait_for(app.contract_done, 20, "HKEX contract resolution", app)
        matches = [d for d in app.contracts if getattr(d.contract, "primaryExchange", "") in {"SEHK", "HKFE"}]
        if not matches:
            raise RuntimeError(f"IBKR did not resolve HKEX stock {normalize_symbol(symbol)}")
        resolved = matches[0].contract

        app.reqNewsProviders()
        wait_for(app.providers_done, 15, "news providers", app)
        available = {p.code for p in app.providers}
        requested = config.get("news_provider_codes") or sorted(available)
        provider_codes = [code for code in requested if code in available]
        if not provider_codes:
            raise RuntimeError("no entitled IBKR news providers are available for this account")

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        app.reqHistoricalNews(
            200, resolved.conId, "+".join(provider_codes),
            start.strftime("%Y%m%d %H:%M:%S UTC"), end.strftime("%Y%m%d %H:%M:%S UTC"),
            limit, [],
        )
        wait_for(app.headlines_done, 30, "historical news", app)
        app._expected_articles = len(app.headlines)
        if app.headlines:
            for index, item in enumerate(app.headlines):
                app.reqNewsArticle(1000 + index, item["provider_code"], item["article_id"], [])
                time.sleep(0.05)
            wait_for(app.articles_done, 45, "news article bodies", app)
            for index, item in enumerate(app.headlines):
                item.update(app.articles.get(1000 + index, {"article_type": None, "body": None}))

        return {
            "source": "Interactive Brokers TWS API",
            "exchange": "HKEX",
            "symbol": normalize_symbol(symbol),
            "ibkr_conid": resolved.conId,
            "provider_codes": provider_codes,
            "window_start": start.isoformat(),
            "window_end": end.isoformat(),
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "article_count": len(app.headlines),
            "articles": app.headlines,
        }
    finally:
        app.disconnect()
        thread.join(timeout=2)


def load_config(secret_id: str, region: str | None) -> dict[str, Any]:
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_id)
    return json.loads(response["SecretString"])


def upload(payload: dict[str, Any], config: dict[str, Any]) -> str:
    bucket = config["s3_bucket"]
    prefix = config.get("s3_processed_prefix", "processed/ibkr-news").strip("/")
    stamp = datetime.now(timezone.utc).strftime("%Y/%m/%d/%Y%m%dT%H%M%SZ")
    key = f"{prefix}/exchange=HKEX/symbol={payload['symbol']}/{stamp}.json"
    boto3.client("s3").put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json",
        ServerSideEncryption=config.get("s3_encryption", "AES256"),
    )
    return f"s3://{bucket}/{key}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbol", help="HKEX numeric symbol, e.g. 700 or 00700")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--secret-id", default="prod/data-collection/ibkr-news")
    parser.add_argument("--region", default=None)
    args = parser.parse_args()
    if args.days < 1 or not 1 <= args.limit <= 300:
        parser.error("--days must be positive and --limit must be between 1 and 300")
    config = load_config(args.secret_id, args.region)
    payload = fetch_news(config, args.symbol, args.days, args.limit)
    print(f"Uploaded {payload['article_count']} articles to {upload(payload, config)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
