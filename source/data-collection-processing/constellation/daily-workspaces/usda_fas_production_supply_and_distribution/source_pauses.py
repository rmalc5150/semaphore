"""Operator-requested capture pauses; retained data and checkpoints are untouched."""
import json
from pathlib import Path

def is_paused(source):
    path = Path(__file__).resolve().parent / 'config/source-pauses.json'
    if not path.exists():
        return False
    return source in json.loads(path.read_text()).get('sources', [])


def unit_pause(unit):
    sources = {'optima-reddit-collection.service': 'reddit', 'optima-reddit-access.service': 'reddit',
               'optima-social-daily.service': 'bluesky_search', 'optima-bluesky-companies.service': 'bluesky_company_posts',
               'optima-github-company-mapping.service': 'github_sdk', 'optima-marketaux-content-backfill.service': 'marketaux'}
    source = sources.get(unit)
    return {'source': source, 'reason': 'Paused at account owner request'} if source and is_paused(source) else None
