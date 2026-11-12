"""Plan daily historical partitions. Registration is explicit; never resumes work."""
import argparse
from datetime import date, timedelta
import json

from constellation.control import Control
from constellation.sources import PROVIDERS, VERSION, validate_spec


def partitions(source, start, end):
    while start < end:
        spec = {'source_key': source, 'dataset': PROVIDERS[source]['dataset'], 'geography': 'global',
            'start': start.isoformat(), 'end': (start + timedelta(days=1)).isoformat(),
            'edition': 'current_retrieval', 'extractor_version': VERSION, 'parameters': {}}
        validate_spec(spec)
        yield spec
        start += timedelta(days=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=sorted(PROVIDERS), required=True)
    parser.add_argument('--start', type=date.fromisoformat, default=date(2016, 1, 1))
    parser.add_argument('--end', type=date.fromisoformat, required=True, help='Exclusive end, no later than current UTC date')
    parser.add_argument('--register', action='store_true')
    args = parser.parse_args()
    specs = list(partitions(args.source, args.start, args.end))
    if not specs:
        parser.error('Start must precede end')
    if args.register:
        control = Control()
        if control.allowed():
            parser.error('Pause collection before registering a bulk plan')
        for spec in specs:
            control.register(spec)
    print(json.dumps({'source_key': args.source, 'start': args.start.isoformat(), 'end_exclusive': args.end.isoformat(),
        'partitions': len(specs), 'registered': args.register, 'collection_resumed': False}))


if __name__ == '__main__':
    main()
