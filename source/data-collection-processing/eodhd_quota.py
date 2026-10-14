"""One durable weighted quota and rolling request limiter for all local EODHD jobs."""
from datetime import datetime,timezone
import json
from pathlib import Path
import sqlite3
import time
from regulatory_collection import SourceIssue


def cost_group(path):
    endpoint=path.split('/',1)[0]
    if endpoint=='user':return 0,'inventory'
    if endpoint=='fundamentals':return 10,'profiles'
    if endpoint in {'eod','div','splits'}:return 1,'market'
    if endpoint in {'exchanges-list','exchange-symbol-list','exchange-details'}:return 1,'inventory'
    raise SourceIssue('eodhd_unbudgeted_endpoint')


class SharedQuota:
    def __init__(self,path,config,clock=time.time,sleeper=time.sleep):
        self.path,self.config,self.clock,self.sleep=str(path),config,clock,sleeper
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS usage (day TEXT PRIMARY KEY, used INTEGER NOT NULL, groups_json TEXT NOT NULL, ceiling INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS requests (stamp REAL NOT NULL)')
    def connect(self):
        db=sqlite3.connect(self.path,timeout=30,isolation_level=None);db.execute('PRAGMA busy_timeout=30000');return db
    def day(self):return datetime.fromtimestamp(self.clock(),timezone.utc).date().isoformat()
    def sync(self,account):
        today=self.day();reported=account.get('apiRequestsDate');used=account.get('apiRequests');limit=account.get('dailyRateLimit')
        if type(used)!=int or type(limit)!=int or not isinstance(reported,str) or reported>today:
            raise SourceIssue('eodhd_usage_unavailable',True)
        # EODHD resets on the first paid request: yesterday's usage is not today's.
        if reported<today:used=0
        ceiling=min(self.config['daily_call_ceiling'],limit-2000)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT used,groups_json FROM usage WHERE day=?',(today,)).fetchone()
            if row:
                db.execute('UPDATE usage SET used=?,ceiling=? WHERE day=?',(max(used,row[0]),ceiling,today))
            else:
                # At first rollout conservatively attribute all earlier consumption
                # to profiles, previously the only scheduled EODHD consumer.
                groups={'profiles':used,'market':0,'inventory':0}
                db.execute('INSERT INTO usage VALUES (?,?,?,?)',(today,used,json.dumps(groups),ceiling))
            db.commit()
    def reserve(self,path):
        cost,group=cost_group(path)
        while True:
            stamp=self.clock();day=self.day();wait=0
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('DELETE FROM requests WHERE stamp<=?',(stamp-60,))
                count,oldest=db.execute('SELECT count(*),min(stamp) FROM requests').fetchone()
                if count>=self.config['requests_per_minute']:
                    wait=max(0.01,oldest+60-stamp+0.01);db.rollback()
                else:
                    if cost:
                        row=db.execute('SELECT used,groups_json,ceiling FROM usage WHERE day=?',(day,)).fetchone()
                        if not row:raise SourceIssue('eodhd_quota_refresh_required',True)
                        used,raw,ceiling=row;groups=json.loads(raw)
                        if used+cost>ceiling or groups.get(group,0)+cost>self.config['daily_group_caps'][group]:
                            raise SourceIssue('eodhd_shared_quota_reached',True)
                        groups[group]=groups.get(group,0)+cost
                        db.execute('UPDATE usage SET used=?,groups_json=? WHERE day=?',(used+cost,json.dumps(groups),day))
                    db.execute('INSERT INTO requests VALUES (?)',(stamp,));db.commit();return
            self.sleep(min(wait,60))
    def status(self):
        with self.connect() as db:
            row=db.execute('SELECT used,groups_json,ceiling FROM usage WHERE day=?',(self.day(),)).fetchone()
        return {'day':self.day(),'reserved_calls':row[0],'groups':json.loads(row[1]),'ceiling':row[2]} if row else {'day':self.day(),'status':'uninitialized'}
