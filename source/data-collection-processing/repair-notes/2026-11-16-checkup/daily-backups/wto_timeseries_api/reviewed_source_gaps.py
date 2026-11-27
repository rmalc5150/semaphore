"""Narrow, evidenced unavailability decisions; never blanket-ignore HTTP errors."""
DECISIONS = ({
    'id': 'medrxiv-prelaunch-2019-06-reviewed-2026-10-30',
    'source': 'biorxiv_medrxiv_preprints',
    'adapter': 'additional_biorxiv',
    'parameters': {'repository': 'medrxiv'},
    'start': '2016-01-01', 'end': '2019-06-01',
    'reason': 'source_not_operating', 'reviewed_at': '2026-10-30',
    'evidence_uri': 'https://www.cshl.edu/cshl-and-plos-partner-to-host-papers-on-medrxiv/',
    'note': 'Provider confirms June 2019 launch. Conservatively exclude only full windows ending before June; June remains eligible. Not applicable to bioRxiv.',
},)


def reviewed_gap(job):
    for decision in DECISIONS:
        if (job.get('source') == decision['source'] and job.get('adapter') == decision['adapter']
            and all(job.get('parameters', {}).get(k) == v for k, v in decision['parameters'].items())
            and decision['start'] <= job['start'] < job['end'] <= decision['end']
            and not job.get('parameters', {}).get('data_start')
            and not job.get('parameters', {}).get('data_end')):
            return dict(decision)
    return None
