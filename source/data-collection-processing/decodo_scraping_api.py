#!/usr/bin/env python3
"""Call Decodo Web Scraping API using a token stored in AWS Secrets Manager."""

from __future__ import annotations

import argparse
import base64
import json
import os
from functools import lru_cache
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_URL = "https://scraper-api.decodo.com/v2/scrape"
DEFAULT_SECRET_ID = "proxies"


class ScrapeError(RuntimeError):
    """Safe diagnostics: never include gateway bodies or authentication values."""
    def __init__(self, stage: str, status: int | None = None):
        self.stage, self.status = stage, status
        self.retryable = status in {202, 429, 500, 502, 503, 504} or stage in {"transport", "incomplete_response"}
        super().__init__(f"scrape_{stage}" + (f"_http_{status}" if status is not None else ""))


def parse_token(response: dict[str, Any], secret_id: str = DEFAULT_SECRET_ID) -> str:
    raw = response.get("SecretString")
    if raw is None:
        raw = base64.b64decode(response["SecretBinary"]).decode("utf-8")
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        decoded = raw
    if isinstance(decoded, dict):
        token = (
            decoded.get("decodo-web-scraping")
            or decoded.get("decodo-token")
            or decoded.get("decodo")
        )
        username = decoded.get("decodo-username")
        password = decoded.get("decodo-password")
        if not token and isinstance(username, str) and isinstance(password, str):
            token = base64.b64encode(f"{username}:{password}".encode()).decode()
    else:
        token = decoded
    if not isinstance(token, str) or not token.strip():
        raise ValueError(
            f"secret {secret_id!r} must contain 'decodo-web-scraping'/'decodo-token', or both "
            "'decodo-username' and 'decodo-password'"
        )
    return token.strip()


def load_token(secret_id: str, region: str) -> str:
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 is required; install requirements.txt") from exc
    response = boto3.client("secretsmanager", region_name=region).get_secret_value(
        SecretId=secret_id
    )
    return parse_token(response, secret_id)


@lru_cache(maxsize=8)
def cached_token(secret_id: str = DEFAULT_SECRET_ID, region: str = "us-east-1") -> str:
    return load_token(secret_id, region)


def scrape(
    url: str,
    token: str,
    *,
    geo: str | None = None,
    headless: bool = False,
    timeout: float = 150,
    opener: Callable[..., Any] = urlopen,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"url": url}
    if parameters:
        payload.update(parameters)
    if geo:
        payload["geo"] = geo
    if headless:
        payload["headless"] = "html"
    request = Request(API_URL, data=json.dumps(payload).encode(), method="POST", headers={
        "Accept": "application/json",
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
        "User-Agent": "data-collection-decodo-client/1.0",
    })
    try:
        with opener(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise ScrapeError("gateway", exc.code) from None
    except (URLError, TimeoutError):
        raise ScrapeError("transport") from None
    if not isinstance(result, dict) or not isinstance(result.get("results"), list):
        raise ScrapeError("incomplete_response")
    return result


def scrape_content(url: str, token: str, *, pending_validator: Callable[[str], bool] | None = None,
                   **parameters: Any) -> str:
    """Return target content and validate both Decodo and target-level status."""
    result = scrape(url, token, parameters=parameters)
    rows = result["results"]
    if not rows or not isinstance(rows[0], dict):
        raise ScrapeError("incomplete_response")
    row = rows[0]
    status = row.get("status_code")
    content = row.get("content")
    # Some rendered public registries retain HTTP 202 after producing a full
    # document. Only an explicit source/page validator can accept that response.
    validated_pending = (status == 202 and isinstance(content, str) and
                         pending_validator is not None and pending_validator(content))
    if not isinstance(status, int) or (status == 202 and not validated_pending) or status >= 400:
        if isinstance(status, int):
            raise ScrapeError("target", status)
        raise ScrapeError("incomplete_response")
    if not isinstance(content, str):
        raise ScrapeError("incomplete_response")
    return content


def scrape_url(url: str, **parameters: Any) -> str:
    """Scrape a URL using the standard project secret and AWS region."""
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
    return scrape_content(url, cached_token(DEFAULT_SECRET_ID, region), **parameters)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?", default="https://ip.decodo.com")
    parser.add_argument("--secret-id", default=DEFAULT_SECRET_ID)
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "us-east-1"))
    parser.add_argument("--geo")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()
    result = scrape(args.url, load_token(args.secret_id, args.region), geo=args.geo, headless=args.headless)
    first = result["results"][0] if result["results"] else {}
    print(json.dumps({
        "status_code": first.get("status_code"),
        "content": first.get("content"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
