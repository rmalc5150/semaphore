"""Monitoring policies for independently scheduled source lanes."""
def extend(config):
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
        ('chictr-daily',True,True),('core-historical',True,False)]:
        unit='optima-'+name+'.service'
        jobs.setdefault(unit,{'serialized':serialized,'queue_timeout_seconds':21600 if serialized else 0,
            'execution_timeout_seconds':7200,'max_start_gap_seconds':129600 if daily else 43200,
            'stale_progress_seconds':129600 if daily else 43200})
        if name in {'authenticated-daily','authenticated-historical','specialist-daily',
                    'specialist-historical','social-daily','chictr-daily','core-historical'}:
            jobs[unit]['checkpoint_progress'] = True
    jobs['optima-search-capture.service']['timer']='optima-search-daily.timer'
    jobs['optima-specialist-publication.service']['publication_owners']=['specialists']
    jobs['optima-specialist-publication.service']['max_start_gap_seconds']=7200
    return config
