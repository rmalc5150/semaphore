"""Run the OpenAlex snapshot capture on the Arm historical worker."""
import json
from pathlib import Path
import subprocess
import sys
import time

from constellation.trial_historical_access import configured_for

ROOT = Path(__file__).resolve().parents[1]
WORKER = Path('/opt/constellation')
STATE = WORKER / 'tmp/openalex-trial-tasks.json'
SOURCE = 'openalex_scholarly_graph'


def main():
    if not (WORKER / 'openalex-trial-snapshot-ready').is_file() or not configured_for(SOURCE):
        return 0
    state = json.loads(STATE.read_text()) if STATE.is_file() else {}
    if time.time() - state.get('openalex_snapshot', 0) < 1800:
        return 0
    try:
        command = [sys.executable, '-B', '-m', 'constellation.research_feeds',
                   SOURCE, 'historical', '--budget', '1']
        return subprocess.run(command, cwd=ROOT, timeout=900).returncode
    finally:
        state['openalex_snapshot'] = time.time()
        temporary = STATE.with_suffix('.tmp')
        temporary.write_text(json.dumps(state))
        temporary.replace(STATE)


if __name__ == '__main__':
    raise SystemExit(main())
