"""Run only the controller's public daily service with checkpoint request metrics."""
import json
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile
import time

from metadata_engine.s3_metrics import MeteredS3

IDLE_STATE = Path(__file__).resolve().parents[1]/'state'/'public-daily-idle.json'


def idle_state():
    try:
        state = json.loads(IDLE_STATE.read_text())
        return max(0, int(state['idle_runs'])), min(time.time()+300, float(state['poll_after']))
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        return 0, 0


def save_idle_state(previous, results):
    if results is None:
        return
    idle_runs = 0 if any(row.get('attempts') or row.get('error') for row in results) else min(previous+1, 6)
    delay = 0 if idle_runs < 3 else min(300, 60 * 2**(idle_runs-3))
    try:
        with NamedTemporaryFile('w', dir=IDLE_STATE.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump({'idle_runs':idle_runs,'poll_after':time.time()+delay}, handle)
        temporary.replace(IDLE_STATE)
    except OSError as error:
        print(json.dumps({'stage':'public_daily_idle_state', 'error':type(error).__name__}),flush=True)


class CaptureS3(MeteredS3):
    def __init__(self, client, state_prefix):
        super().__init__(client)
        self.state_prefix = state_prefix
        self.checkpoint_gets = 0
        self.checkpoint_puts = 0
        self.puts_returning_etag = 0

    def get_object(self, **kwargs):
        if kwargs['Key'].startswith(self.state_prefix):
            self.checkpoint_gets += 1
        return super().__getattr__('get_object')(**kwargs)

    def put_object(self, **kwargs):
        response = super().__getattr__('put_object')(**kwargs)
        if kwargs['Key'].startswith(self.state_prefix):
            self.checkpoint_puts += 1
            if response.get('ETag'):
                self.puts_returning_etag += 1
        return response


def main():
    mode = sys.argv.pop(1)
    if mode in ('baseline', 'candidate', 'production'):
        import public_source_capture as capture
    else:
        raise ValueError('Unknown canary mode')
    prior, poll_after = idle_state() if mode == 'production' else (0, 0)
    if time.time() < poll_after:
        print(json.dumps({'stage':'public_daily_idle_backoff','poll_after':poll_after}),flush=True)
        return
    from constellation import public_daily

    clients = []
    original_control = public_daily.Control

    def control():
        instance = original_control()
        instance.s3 = CaptureS3(instance.s3, capture.PREFIX+'/states/daily/')
        clients.append(instance.s3)
        return instance

    public_daily.Control = control
    try:
        results = public_daily.main(batch_receipts=mode == 'production')
        if mode == 'production':
            save_idle_state(prior, results)
    finally:
        public_daily.Control = original_control
        for client in clients:
            print(json.dumps({'stage':'public_daily_s3_canary', 'mode':mode,
                              's3_requests':client.counts(), 'checkpoint_gets':client.checkpoint_gets,
                              'checkpoint_puts':client.checkpoint_puts,
                              'puts_returning_etag':client.puts_returning_etag}), flush=True)


if __name__ == '__main__':
    main()
