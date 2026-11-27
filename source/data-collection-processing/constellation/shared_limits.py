"""Cross-host pacing for the reviewed legacy HTTP clients.

Provider-specific daily/weighted budgets remain mandatory; this common layer
does not replace them. Enable only after the SQL table and grants are installed.
"""
import os
import time
from urllib.parse import urlsplit

_CONTROL = None


def provider(url):
    host = (urlsplit(url).hostname or '').lower().removeprefix('www.')
    if not host:
        raise ValueError('HTTP URL requires a hostname')
    for suffix in ('sec.gov','fda.gov','clinicaltrials.gov','ncbi.nlm.nih.gov','hkexnews.hk',
                   'ema.europa.eu','scraper-api.decodo.com','crossref.org'):
        if host == suffix or host.endswith('.' + suffix):
            return suffix
    return host


def admit(url):
    if os.environ.get('CONSTELLATION_SHARED_HTTP_LIMITS') != '1':
        return
    global _CONTROL
    if _CONTROL is None:
        from constellation.control import Control
        _CONTROL = Control()
    name = provider(url)
    interval=5 if name=='oasis.caiso.com' else 95 if name=='api.github.com' else 2 if name=='api.uspto.gov' else 1
    # Conservative aggregate pacing across the t3 and c7i. Each original
    # collector's daily allowance remains enforced separately.
    failures = 0
    while True:
        wait = 0
        try:
            with _CONTROL.db() as cursor:
                cursor.execute('INSERT INTO backfill_http_limits(provider) VALUES(%s) ON DUPLICATE KEY UPDATE provider=VALUES(provider)', (name,))
                cursor.execute('SELECT next_request_at, UNIX_TIMESTAMP(NOW(3)) AS now_epoch FROM backfill_http_limits WHERE provider=%s FOR UPDATE', (name,))
                row = cursor.fetchone()
                wait = max(0, float(row['next_request_at']) - float(row['now_epoch']))
                if not wait:
                    cursor.execute('UPDATE backfill_http_limits SET next_request_at=UNIX_TIMESTAMP(NOW(3))+%s WHERE provider=%s', (interval,name))
        except Exception as exc:
            from pymysql.err import OperationalError
            # Retry the rolled-back admission transaction, never bypass it.
            # Do not turn a short DB lock/connection hiccup into a failed source
            # run; persistent failures still stop this request after 3 attempts.
            if (not isinstance(exc, OperationalError) or not exc.args
                    or exc.args[0] not in {1205,1213,2003,2006,2013}
                    or failures >= 2):
                raise
            failures += 1
            time.sleep(0.5 * 2 ** (failures - 1))
            continue
        if not wait:
            return
        time.sleep(min(wait, 1))
