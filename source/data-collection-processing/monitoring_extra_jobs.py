"""Monitoring policies for independently scheduled source lanes."""
def extend(config):
    config.setdefault('daily_health_required',True)
    jobs=config['jobs']
    jobs.setdefault('optima-committed-athena.service', {
        'serialized':False,'queue_timeout_seconds':0,'execution_timeout_seconds':7200,
        'max_start_gap_seconds':10800,'stale_progress_seconds':10800,
        'progress_keys':['athena-committed/latest-report.json']})
    for name, serialized, daily in [
        ('authenticated-daily',False,False),('authenticated-historical',False,False),
        ('specialist-daily',True,True),('specialist-historical',True,False),
        ('specialist-publication',False,False),('reddit-collection',False,False),
        ('search-capture',True,True),('social-daily',True,True),
        ('chictr-daily',True,True),('core-historical',True,False),
        ('patents-prosecution',False,False),('patents-prosecution-publication',False,False),
        ('daily-health-audit',False,True)]:
        unit='optima-'+name+'.service'
        jobs.setdefault(unit,{'serialized':serialized,'queue_timeout_seconds':21600 if serialized else 0,
            'execution_timeout_seconds':7200,'max_start_gap_seconds':129600 if daily else 43200,
            'stale_progress_seconds':129600 if daily else 43200})
        if name in {'authenticated-daily','authenticated-historical','specialist-daily',
                    'specialist-historical','social-daily','chictr-daily','core-historical'}:
            jobs[unit]['checkpoint_progress'] = True
    jobs['optima-search-capture.service']['timer']='optima-search-capture.timer'
    jobs['optima-search-capture.service']['max_start_gap_seconds']=8*86400
    jobs['optima-search-capture.service']['stale_progress_seconds']=9*86400
    jobs['optima-specialist-publication.service']['publication_owners']=['specialists']
    jobs['optima-specialist-publication.service']['max_start_gap_seconds']=7200
    jobs['optima-patents-prosecution.service']['checkpoint_progress']=True
    # Capture now shares the S3 runtime workspace even without the heavy-job
    # lock. Apply the same queue grace as other shared-workspace collectors.
    jobs['optima-patents-prosecution.service']['queue_timeout_seconds']=21600
    jobs['optima-patents-prosecution-publication.service']['publication_owners']=['patent_office_actions','patent_petition_decisions']
    jobs['optima-patents-prosecution.service']['max_start_gap_seconds']=10800
    jobs['optima-patents-prosecution-publication.service']['max_start_gap_seconds']=7200
    from constellation.m7_capture_plan import UNITS
    for unit,worker in UNITS.items():
        entry=jobs.setdefault(unit,{'serialized':False,'execution_timeout_seconds':900,
            'max_start_gap_seconds':43200,'stale_progress_seconds':43200})
        entry.update(queue_timeout_seconds=21600,execution_worker_unit=worker,checkpoint_progress=True)
    for unit in ('optima-people-collection.service','optima-authenticated-daily.service'):
        if unit in jobs:jobs[unit]['queue_timeout_seconds']=21600
    return config
