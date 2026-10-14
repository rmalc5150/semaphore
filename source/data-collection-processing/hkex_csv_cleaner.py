#!/usr/bin/env python3
"""Remove excluded HKEX stock codes from a generated prices CSV."""

from __future__ import annotations

import argparse
import csv
import io
import subprocess
import sys
from pathlib import Path
from typing import Iterable, TypeVar


DEFAULT_EXCLUSION_URI = (
    "s3://processed-059416028963-us-east-1-an/hkex/"
    "hkex_company_exclusions.csv"
)
T = TypeVar("T")


def normalize_code(value: str) -> str:
    code = value.strip()
    if not code.isdigit() or len(code) > 5:
        raise ValueError(f"invalid HKEX code in exclusion list: {value!r}")
    return code.zfill(5)


def load_excluded_codes(s3_uri: str = DEFAULT_EXCLUSION_URI) -> set[str]:
    """Download an exclusion CSV from S3 and return its normalized stock codes."""
    try:
        result = subprocess.run(
            ["aws", "s3", "cp", s3_uri, "-", "--only-show-errors"],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("AWS CLI is not installed or is not on PATH") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip()
        message = f": {detail}" if detail else ""
        raise RuntimeError(f"could not download exclusion list {s3_uri}{message}") from exc

    reader = csv.DictReader(io.StringIO(result.stdout.lstrip("\ufeff")))
    if not reader.fieldnames or "code" not in reader.fieldnames:
        raise ValueError(f"exclusion list {s3_uri} must contain a 'code' column")
    return {
        normalize_code(row["code"])
        for row in reader
        if row.get("code", "").strip()
    }


def filter_by_code(rows: Iterable[T], excluded_codes: set[str]) -> list[T]:
    """Filter dictionaries or objects having a ``code`` field/attribute."""
    kept: list[T] = []
    for row in rows:
        raw_code = row.get("code", "") if isinstance(row, dict) else getattr(row, "code")
        if normalize_code(str(raw_code)) not in excluded_codes:
            kept.append(row)
    return kept


def clean_csv(input_path: Path, output_path: Path, s3_uri: str = DEFAULT_EXCLUSION_URI) -> tuple[int, int]:
    excluded_codes = load_excluded_codes(s3_uri)
    with input_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or "code" not in reader.fieldnames:
            raise ValueError(f"{input_path} must contain a 'code' column")
        original = list(reader)

    cleaned = filter_by_code(original, excluded_codes)
    with output_path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=reader.fieldnames)
        writer.writeheader()
        writer.writerows(cleaned)
    return len(original), len(cleaned)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Remove S3-listed companies from an HKEX prices CSV.")
    parser.add_argument("input", type=Path, help="input HKEX prices CSV")
    parser.add_argument("--output", type=Path, help="output CSV; default: replace input")
    parser.add_argument("--exclusions", default=DEFAULT_EXCLUSION_URI, help="S3 exclusion-list URI")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output or args.input
    try:
        before, after = clean_csv(args.input, output, args.exclusions)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {after:,} rows to {output}; removed {before - after:,} excluded rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
