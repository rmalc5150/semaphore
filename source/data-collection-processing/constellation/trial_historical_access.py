"""Worker-local, non-expiring historical authorization for the trial instance."""
import json
from pathlib import Path

INSTANCE = 'i-08311762628a9830f'
SOURCES = frozenset({'openalex_scholarly_graph', 'imf_portwatch_shipping_activity',
                     'copernicus_era5_era5_land'})
OPENDART = 'south_korea_fss_opendart'
ROOT = Path('/opt/constellation')
POLICY = ROOT / 'trial-historical-policy.json'
OPENDART_OWNER = ROOT / 'trial-specialists/opendart-owner.json'
HOST_ID = Path('/sys/devices/virtual/dmi/id/board_asset_tag')


def owns_opendart(path):
    """Require an exact, identity-bound assignment for OpenDART history."""
    try:
        owner = json.loads(path.read_text())
        return owner == {'instance_id': INSTANCE, 'source': OPENDART, 'mode': 'historical_only'}
    except (OSError, ValueError):
        return False


def configured_for(source):
    try:
        policy = json.loads(POLICY.read_text())
        if (policy.get('instance_id') != INSTANCE or HOST_ID.read_text().strip() != INSTANCE
                or policy.get('mode') != 'no_date_cutoff'
                or set(policy.get('sources', [])) != SOURCES
                or (ROOT / 'batch-paused').exists()):
            return False
    except (AttributeError, OSError, TypeError, ValueError):
        return False
    return owns_opendart(OPENDART_OWNER) if source == OPENDART else source in SOURCES


def allowed(control, source):
    if not POLICY.is_file():
        return control.allowed()
    if not configured_for(source):
        return False
    # Deliberate pauses still apply. The date in the shared queue remains in
    # use on every other host and is not changed by this policy.
    return (control.get('control') or {}).get('enabled') is True
