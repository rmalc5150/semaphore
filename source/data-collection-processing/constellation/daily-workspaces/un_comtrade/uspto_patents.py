#!/usr/bin/env python3
"""Collect USPTO ODP application responses using an AWS Secrets Manager API key."""

import argparse
import json
import os
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen

import boto3

DEFAULT_SECRET_ID = "arn:aws:secretsmanager:us-east-1:059416028963:secret:USPTO-CwTvy4"
BASE_URL = "https://api.uspto.gov/api/v1/patent/applications"


def parse_api_key(secret):
    """Accept a plain key or a Secrets Manager JSON key/value object."""
    try:
        value = json.loads(secret)
    except json.JSONDecodeError:
        value = secret
    if isinstance(value, dict):
        fields = {re.sub(r"[^a-z0-9]", "", k.lower()): v for k, v in value.items()}
        value = next((fields[k] for k in ("usptoapikey", "xapikey", "apikey", "uspto", "key") if k in fields), None)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("USPTO secret must contain a nonempty key, either plain text or JSON with an API_KEY field")
    return value.strip()


def load_api_key(secret_id=DEFAULT_SECRET_ID, region=None):
    if region is None:
        region = secret_id.split(":")[3] if secret_id.startswith("arn:") else "us-east-1"
    response = boto3.client("secretsmanager", region_name=region).get_secret_value(SecretId=secret_id)
    secret = response.get("SecretString")
    if secret is None:
        raise ValueError("USPTO secret must use SecretString")
    return parse_api_key(secret)


def application_number(value):
    number = value.replace("/", "").replace(",", "").strip()
    if not re.fullmatch(r"[0-9]{8}", number):
        raise argparse.ArgumentTypeError("Use an eight-digit US application number, e.g. 16123456 or 16/123,456")
    return number


def fetch_application(number, api_key):
    number = application_number(number)
    request = Request(f"{BASE_URL}/{number}", headers={"X-API-KEY": api_key, "Accept": "application/json"})
    with urlopen(request, timeout=60) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("applications", nargs="+", type=application_number)
    parser.add_argument("--secret-id", default=os.getenv("USPTO_SECRET_ID", DEFAULT_SECRET_ID))
    parser.add_argument("--region", default=None, help="AWS region; defaults to the secret ARN's region")
    parser.add_argument("--output", required=True, help="Raw ODP responses as JSONL (not a normalized event snapshot)")
    args = parser.parse_args()
    api_key = load_api_key(args.secret_id, args.region)
    records = []
    for index, number in enumerate(dict.fromkeys(args.applications)):
        if index:
            time.sleep(1)
        records.append(fetch_application(number, api_key))
    with Path(args.output).open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps({"applications": len(records), "output": args.output}))


if __name__ == "__main__":
    main()
