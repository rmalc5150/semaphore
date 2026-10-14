#!/usr/bin/env python3
"""Collect company mentions from supported social APIs and score sentiment.

Supported live connectors: Reddit (OAuth), Bluesky (public AppView), and
YouTube Data API v3. WeChat and licensed social-listening vendors can be fed
through the normalized JSONL import because WeChat has no general public-post
search API.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


USER_AGENT = "company-social-monitor/1.0 (contact: data-team)"
POSITIVE = {
    "advance", "approval", "approved", "beat", "benefit", "best", "breakthrough",
    "bullish", "excellent", "gain", "good", "great", "growth", "improve",
    "innovation", "outperform", "positive", "promising", "recommend", "success",
    "surge", "win", "获批", "增长", "成功", "突破", "利好", "看好", "优秀",
}
NEGATIVE = {
    "bad", "bearish", "concern", "decline", "delay", "disappointing", "fail",
    "fraud", "investigation", "lawsuit", "loss", "negative", "poor", "recall",
    "risk", "scam", "selloff", "warning", "worse", "失败", "下降", "亏损",
    "风险", "调查", "诉讼", "召回", "利空", "担忧",
}
NEGATORS = {"not", "no", "never", "neither", "hardly", "without", "不", "没", "未", "无"}


@dataclass
class Mention:
    company: str
    platform: str
    post_id: str
    author: str | None
    text: str
    url: str | None
    published_at: str | None
    comments: int
    shares: int
    reactions: int
    sentiment_score: float = 0.0
    sentiment_label: str = "neutral"
    engagement_score: float = 0.0


def request_json(url: str, headers: dict[str, str] | None = None,
                 data: bytes | None = None, retries: int = 3) -> dict[str, Any]:
    request = Request(url, data=data, headers={"User-Agent": USER_AGENT, **(headers or {})})
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=45) as response:
                return json.load(response)
        except HTTPError as exc:
            retryable = exc.code == 429 or exc.code >= 500
            if not retryable or attempt == retries - 1:
                detail = exc.read().decode("utf-8", "replace")[:300]
                raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc
            time.sleep(2 ** attempt)
        except (URLError, TimeoutError) as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"could not fetch {url}: {exc}") from exc
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def sentiment(text: str) -> tuple[float, str]:
    """Small, explainable English/Chinese lexicon scorer in the range [-1, 1]."""
    normalized = text.lower()
    words = re.findall(r"[a-z][a-z'-]*|[\u4e00-\u9fff]", normalized)
    score = 0.0
    hits = 0
    for index, word in enumerate(words):
        value = 1 if word in POSITIVE else -1 if word in NEGATIVE else 0
        if not value:
            continue
        # Keep the baseline predictable: a negator modifies the immediately
        # following sentiment word, not every later word in the sentence.
        if index and words[index - 1] in NEGATORS:
            value *= -1
        score += value
        hits += 1
    # Chinese terms often contain multiple characters and are not word-tokenized.
    for term, value in [(x, 1) for x in POSITIVE if ord(x[0]) > 127] + [(x, -1) for x in NEGATIVE if ord(x[0]) > 127]:
        count = normalized.count(term)
        score += value * count
        hits += count
    result = round(max(-1.0, min(1.0, score / math.sqrt(max(1, hits)))), 4)
    label = "positive" if result >= 0.2 else "negative" if result <= -0.2 else "neutral"
    return result, label


def enrich(item: Mention) -> Mention:
    item.sentiment_score, item.sentiment_label = sentiment(item.text)
    # Comments and shares indicate active propagation; reactions are lighter weight.
    item.engagement_score = round(
        math.log1p(max(0, item.comments) * 2 + max(0, item.shares) * 3 + max(0, item.reactions)), 4
    )
    return item


def reddit_token(client_id: str, client_secret: str) -> str:
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    payload = request_json(
        "https://www.reddit.com/api/v1/access_token",
        {"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
        urlencode({"grant_type": "client_credentials"}).encode(),
    )
    return str(payload["access_token"])


def collect_reddit(company: str, limit: int, token: str) -> list[Mention]:
    query = urlencode({"q": f'"{company}"', "sort": "new", "type": "link", "limit": min(limit, 100), "raw_json": 1})
    data = request_json(f"https://oauth.reddit.com/search?{query}", {"Authorization": f"Bearer {token}"})
    rows = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        created = datetime.fromtimestamp(post.get("created_utc", 0), timezone.utc).isoformat()
        rows.append(enrich(Mention(
            company, "reddit", str(post.get("id", "")), post.get("author"),
            "\n".join(x for x in (post.get("title", ""), post.get("selftext", "")) if x),
            "https://www.reddit.com" + post.get("permalink", ""), created,
            int(post.get("num_comments", 0)), 0, int(post.get("score", 0)),
        )))
    return rows


def collect_bluesky(company: str, limit: int) -> list[Mention]:
    query = urlencode({"q": f'"{company}"', "limit": min(limit, 100), "sort": "latest"})
    data = request_json(f"https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?{query}")
    rows = []
    for post in data.get("posts", []):
        record = post.get("record", {})
        author = post.get("author", {})
        uri = post.get("uri", "")
        rkey = uri.rsplit("/", 1)[-1]
        handle = author.get("handle")
        rows.append(enrich(Mention(
            company, "bluesky", uri, handle, record.get("text", ""),
            f"https://bsky.app/profile/{handle}/post/{rkey}" if handle else None,
            record.get("createdAt") or post.get("indexedAt"), int(post.get("replyCount", 0)),
            int(post.get("repostCount", 0)), int(post.get("likeCount", 0)),
        )))
    return rows


def collect_youtube(company: str, limit: int, api_key: str) -> list[Mention]:
    search = urlencode({"part": "snippet", "q": company, "type": "video", "order": "date",
                        "maxResults": min(limit, 50), "key": api_key})
    found = request_json(f"https://www.googleapis.com/youtube/v3/search?{search}").get("items", [])
    ids = [item.get("id", {}).get("videoId") for item in found]
    if not ids:
        return []
    detail_query = urlencode({"part": "snippet,statistics", "id": ",".join(ids), "key": api_key})
    details = request_json(f"https://www.googleapis.com/youtube/v3/videos?{detail_query}")
    rows = []
    for video in details.get("items", []):
        snippet, stats = video.get("snippet", {}), video.get("statistics", {})
        video_id = video.get("id", "")
        rows.append(enrich(Mention(
            company, "youtube", video_id, snippet.get("channelTitle"),
            "\n".join((snippet.get("title", ""), snippet.get("description", ""))),
            f"https://www.youtube.com/watch?v={video_id}", snippet.get("publishedAt"),
            int(stats.get("commentCount", 0)), 0, int(stats.get("likeCount", 0)),
        )))
    return rows


def load_jsonl(path: Path, companies: list[str]) -> list[Mention]:
    """Load WeChat/vendor exports using the normalized output field names."""
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                text = str(raw.get("text") or raw.get("content") or "")
                matched = raw.get("company") or next((c for c in companies if c.casefold() in text.casefold()), None)
                if not matched:
                    continue
                rows.append(enrich(Mention(
                    str(matched), str(raw.get("platform", path.stem)), str(raw.get("post_id") or raw.get("id") or f"line-{line_number}"),
                    raw.get("author"), text, raw.get("url"), raw.get("published_at") or raw.get("publishedAt"),
                    int(raw.get("comments", 0) or 0), int(raw.get("shares", 0) or 0),
                    int(raw.get("reactions", raw.get("likes", 0)) or 0),
                )))
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                raise ValueError(f"{path}:{line_number}: invalid record: {exc}") from exc
    return rows


def deduplicate(rows: Iterable[Mention]) -> list[Mention]:
    unique: dict[tuple[str, str], Mention] = {}
    for row in rows:
        key = (row.platform.casefold(), row.post_id)
        if key not in unique or row.engagement_score > unique[key].engagement_score:
            unique[key] = row
    return sorted(unique.values(), key=lambda x: (x.company.casefold(), -x.engagement_score, x.platform))


def summary(rows: list[Mention]) -> list[dict[str, Any]]:
    result = []
    for company in sorted({row.company for row in rows}, key=str.casefold):
        group = [row for row in rows if row.company == company]
        weight = sum(max(1.0, row.engagement_score) for row in group)
        weighted = sum(row.sentiment_score * max(1.0, row.engagement_score) for row in group) / weight
        result.append({
            "company": company, "mentions": len(group), "authors": len({r.author for r in group if r.author}),
            "comments": sum(r.comments for r in group), "shares": sum(r.shares for r in group),
            "reactions": sum(r.reactions for r in group), "engagementWeightedSentiment": round(weighted, 4),
            "positive": sum(r.sentiment_label == "positive" for r in group),
            "neutral": sum(r.sentiment_label == "neutral" for r in group),
            "negative": sum(r.sentiment_label == "negative" for r in group),
        })
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("companies", nargs="+", help="company names to search (quote names containing spaces)")
    parser.add_argument("--platforms", default="bluesky", help="comma-separated: reddit,bluesky,youtube")
    parser.add_argument("--import-jsonl", action="append", default=[], type=Path, help="WeChat/vendor normalized JSONL export")
    parser.add_argument("--limit", type=int, default=50, help="maximum results per company and platform")
    parser.add_argument("--output", type=Path, default=Path("social-media-mentions.json"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    platforms = {x.strip().lower() for x in args.platforms.split(",") if x.strip()}
    unsupported = platforms - {"reddit", "bluesky", "youtube"}
    if unsupported:
        raise SystemExit(f"unsupported live platform(s): {', '.join(sorted(unsupported))}; use --import-jsonl")
    rows: list[Mention] = []
    errors: list[dict[str, str]] = []
    token = None
    if "reddit" in platforms:
        client_id, secret = os.getenv("REDDIT_CLIENT_ID"), os.getenv("REDDIT_CLIENT_SECRET")
        if not client_id or not secret:
            raise SystemExit("reddit requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET")
        token = reddit_token(client_id, secret)
    youtube_key = os.getenv("YOUTUBE_API_KEY")
    if "youtube" in platforms and not youtube_key:
        raise SystemExit("youtube requires YOUTUBE_API_KEY")
    collectors = {
        "reddit": lambda company: collect_reddit(company, args.limit, token or ""),
        "bluesky": lambda company: collect_bluesky(company, args.limit),
        "youtube": lambda company: collect_youtube(company, args.limit, youtube_key or ""),
    }
    for company in args.companies:
        for platform in sorted(platforms):
            try:
                rows.extend(collectors[platform](company))
            except Exception as exc:
                errors.append({"company": company, "platform": platform, "error": str(exc)})
                print(f"warning: {platform}/{company}: {exc}", file=sys.stderr)
    for path in args.import_jsonl:
        rows.extend(load_jsonl(path, args.companies))
    final_rows = deduplicate(rows)
    document = {
        "generatedAt": datetime.now(timezone.utc).isoformat(), "companies": args.companies,
        "summary": summary(final_rows), "mentions": [asdict(row) for row in final_rows], "errors": errors,
        "methodology": {"sentiment": "explainable English/Chinese lexicon; validate before decisions",
                        "engagement": "ln(1 + 2*comments + 3*shares + reactions)"},
    }
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(final_rows)} mentions to {args.output}")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
