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
}, {
    'id': 'alfred-dtwexbgs-pre-first-vintage-reviewed-2026-11-16',
    'source': 'fred_alfred_series_and_vintages', 'adapter': 'additional_fred',
    'parameters': {'series_id': 'DTWEXBGS', 'realtime_start': '2016-01-01',
                   'realtime_end': '2018-12-31',
                   'url': 'https://api.stlouisfed.org/fred/series/observations'},
    'start': '2016-01-01', 'end': '2026-10-26',
    'reason': 'requested_vintage_predates_series_archive', 'reviewed_at': '2026-11-16',
    'evidence_uri': 's3://data-collection-059416028963-us-east-1-an/research-data/source_documents/fred_alfred_series_and_vintages/c1e592c762b177ae54c0196313a17c6c04ec95a601c1718a32ae2e3da902e535',
    'first_available_vintage': '2019-02-04',
    'note': 'Provider vintage catalogue starts February 4, 2019; the pinned realtime interval ends in 2018. Current/backfilled values cannot substitute. Other series and later vintage intervals remain collectible.',
})

DECISIONS += tuple({
    'id':'wto-periodless-'+indicator.lower()+'-2016-reviewed-2026-11-16',
    'source':'wto_timeseries_api','adapter':'additional_wto_timeseries',
    'parameters':{'indicator':indicator,'year':2016,'url':'https://api.wto.org/timeseries/v1/data'},
    'start':'2016-01-01','end':'2017-01-01',
    'reason':'indicator_has_no_historical_time_dimension','reviewed_at':'2026-11-16',
    'evidence_uri':'s3://data-collection-059416028963-us-east-1-an/research-data/source_documents/wto_timeseries_api/'+checksum,
    'note':'Provider explicitly rejects a year because this indicator has no time dimension. Current periodless snapshot remains enabled; it cannot substitute for a 2016 observation.',
} for indicator,checksum in (
    ('TP_B_0380','a41f34222f7f34d146672e72abc15817838c0c72a8d96392301eb944d79466c0'),
    ('TP_B_0180','f11682f54e43e8f758591f73af5b7bb1cef934a78515b1c125a27b1b38ffda1e'),
))


def reviewed_gap(job):
    for decision in DECISIONS:
        if (job.get('source') == decision['source'] and job.get('adapter') == decision['adapter']
            and all(job.get('parameters', {}).get(k) == v for k, v in decision['parameters'].items())
            and decision['start'] <= job['start'] < job['end'] <= decision['end']
            and not job.get('parameters', {}).get('data_start')
            and not job.get('parameters', {}).get('data_end')):
            return dict(decision)
    return None


def reviewed_edinet_expiry(job, provider_status, observed_on=None):
    """Only an actual 404 for an exact day safely beyond the documented archive."""
    from datetime import date,timedelta
    observed=date.fromisoformat(observed_on) if observed_on else date.today()
    try:anniversary=observed.replace(year=observed.year-10)
    except ValueError:anniversary=observed.replace(year=observed.year-10,day=28)
    p=job.get('parameters',{})
    if (job.get('source')!='edinet_filings' or job.get('adapter')!='edinet'
        or job.get('mode')!='historical' or str(provider_status)!='404'
        or p.get('url')!='https://api.edinet-fsa.go.jp/api/v2/documents.json'
        or p.get('date')!=job.get('start')):return None
    start=date.fromisoformat(job['start']);end=date.fromisoformat(job['end'])
    if end-start!=timedelta(days=1) or end>anniversary-timedelta(days=7):return None
    return {'id':'edinet-ten-year-listing-retention-v1','reason':'edinet_listing_expired',
        'reviewed_at':observed.isoformat(),'provider_status':'404',
        'evidence_uri':'https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/download/ESE140206.pdf',
        'contract_section':'3-1-3-3','boundary_grace_days':7,
        'note':'Original list outside the official ten-year rolling archive; not an empty filing day. Previously saved material remains retained. Recover through a separate evidenced archive if available.'}
