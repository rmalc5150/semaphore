"""Install the additive reviewed-source failure queues; safe to rerun."""
import json
from pathlib import Path

from metadata_engine_provision import mysql
from rds_management_access import settings

ROOT=Path(__file__).resolve().parent


def main():
    sql='\n'.join(line for line in (ROOT/'schemas/rds-metadata-engine-verified-source-queues.sql').read_text().splitlines() if not line.lstrip().startswith('--'))
    _,instance,admin,_=settings()
    mysql(instance,admin,sql)
    print(json.dumps({'installed':['source_date_failures','pipeline_failures']}))


if __name__=='__main__':main()
