"""Inspect or trial the MySQL tracking schema without exposing credentials.

Uses host AWS identity and the RDS-managed secret; password exists only in memory
and in the short-lived mysql child's environment. No credentials are written.
"""
import argparse
import json
import os
import secrets
from pathlib import Path
import subprocess
import sys
import urllib.request

import boto3

ROOT = Path(__file__).resolve().parent
SECRET = 'arn:aws:secretsmanager:us-east-1:059416028963:secret:rds!db-85014375-d9c9-4480-8626-aae2310bface-pyk3Ae'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['inspect', 'check-tables', 'trial', 'install', 'roles', 'verify'], default='inspect')
    args = parser.parse_args()
    session = boto3.Session(region_name='us-east-1')
    instances = session.client('rds').describe_db_instances()['DBInstances']
    matches = [d for d in instances if d.get('MasterUserSecret', {}).get('SecretArn') == SECRET]
    if len(matches) != 1 or matches[0]['Engine'] != 'mysql':
        raise RuntimeError('Expected exactly one MySQL instance for the supplied secret')
    db = matches[0]
    secret = json.loads(session.client('secretsmanager').get_secret_value(SecretId=SECRET)['SecretString'])
    if secret['username'] != 'admin':
        raise RuntimeError('Unexpected secret username')
    ca = ROOT / 'config' / 'rds-us-east-1-ca-bundle.pem'
    if not ca.exists():
        with urllib.request.urlopen('https://truststore.pki.rds.amazonaws.com/us-east-1/us-east-1-bundle.pem', timeout=20) as response:
            ca.write_bytes(response.read())
    env = os.environ.copy()
    env['MYSQL_PWD'] = secret['password']
    command = ['mysql', '--no-defaults', '--protocol=TCP',
               '--host='+db['Endpoint']['Address'], '--port='+str(db['Endpoint']['Port']),
               '--user=admin', '--ssl', '--ssl-ca='+str(ca), '--ssl-verify-server-cert',
               '--connect-timeout=10', '--batch', '--skip-column-names', '--skip-reconnect']

    def execute(sql):
        result = subprocess.run(command, input=sql, text=True, capture_output=True, env=env, timeout=60)
        if result.returncode:
            # Errors may include statement values: redact the password defensively.
            raise RuntimeError(result.stderr.replace(secret['password'], '[REDACTED]').strip())
        return result.stdout.strip()

    info = execute("SELECT VERSION(), @@log_bin, @@log_bin_trust_function_creators, @@require_secure_transport, @@global.time_zone; SHOW SESSION STATUS LIKE 'Ssl_cipher'; SHOW DATABASES;")
    print(json.dumps({'instance':db['DBInstanceIdentifier'], 'engine_version':db['EngineVersion'],
                      'parameter_groups':db['DBParameterGroups'], 'connection_checks':info}, indent=2))
    if args.mode == 'inspect':
        return
    if args.mode == 'verify':
        print(execute((ROOT/'schemas'/'rds-tracking-mysql-smoke.sql').read_text()))
        print(execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='tracking'; SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema='tracking'; SELECT (SELECT COUNT(*) FROM tracking.companies)+(SELECT COUNT(*) FROM tracking.products)+(SELECT COUNT(*) FROM tracking.entity_changes);"))
        print('Verified installed schema; synthetic data and audit writes rolled back.')
        return
    if args.mode == 'roles':
        execute((ROOT/'schemas'/'rds-tracking-mysql-roles.sql').read_text())
        print(execute("SHOW GRANTS FOR 'tracking_reader'; SHOW GRANTS FOR 'tracking_editor';"))
        username = 'tracking_test_'+secrets.token_hex(6)
        password = secrets.token_urlsafe(32)
        execute(f"CREATE USER '{username}'@'%' IDENTIFIED BY '{password}' REQUIRE SSL; GRANT 'tracking_editor' TO '{username}'@'%'; SET DEFAULT ROLE 'tracking_editor' TO '{username}'@'%';")
        try:
            test_env = env.copy()
            test_env['MYSQL_PWD'] = password
            test_command = [arg if arg != '--user=admin' else '--user='+username for arg in command]
            def as_editor(sql, expected_code=None):
                result = subprocess.run(test_command, input=sql, text=True, capture_output=True, env=test_env, timeout=30)
                if expected_code is None:
                    if result.returncode:
                        raise RuntimeError('Restricted editor test failed: '+result.stderr.replace(password, '[REDACTED]'))
                    print(result.stdout.strip())
                elif result.returncode == 0 or f'ERROR {expected_code} ' not in result.stderr:
                    raise RuntimeError('Restricted editor did not fail with the expected access-denied code')
            as_editor("USE tracking; SET SESSION time_zone = '+00:00'; SET @app_actor='role-test', @app_change_reason='Synthetic rollback-only permission check'; START TRANSACTION; INSERT INTO companies(company_id,canonical_name,evidence,observed_at) VALUES('cmp_00000000-0000-4000-8000-000000000003','Role test',JSON_ARRAY(JSON_OBJECT('source','test','reference','synthetic')),CURRENT_TIMESTAMP(6)); SELECT COUNT(*) FROM entity_changes WHERE changed_by='role-test'; ROLLBACK;")
            as_editor("INSERT INTO tracking.entity_changes(table_name,row_key,operation,changed_by,change_reason) VALUES('products','test','INSERT','test','unauthorized');",1142)
            as_editor("CREATE TABLE tracking.unauthorized_test(id INT);",1142)
            print('PASS: restricted editor can write through audit triggers but cannot alter audit history or create tables.')
        finally:
            execute(f"DROP USER '{username}'@'%';")
        return
    if db['EngineVersion'].split('.')[:2] != ['8', '4']:
        raise RuntimeError('Migration validated for MySQL 8.4 only')
    prerequisites = execute('SELECT IF(@@log_bin = 0 OR @@log_bin_trust_function_creators = 1, 1, 0);')
    if prerequisites != '1' and args.mode != 'check-tables':
        raise RuntimeError('RDS parameter prerequisite: log_bin_trust_function_creators must be enabled before creating triggers')
    target = 'tracking_ddl_trial_20261014' if args.mode == 'check-tables' else ('tracking_trial_20261014' if args.mode == 'trial' else 'tracking')
    exists = execute("SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = '"+target+"';")
    if exists != '0':
        raise RuntimeError('Target database already exists; refusing to overwrite or resume blindly')
    sql = (ROOT/'schemas'/'rds-tracking-mysql.sql').read_text()
    if args.mode == 'check-tables':
        sql = sql.split('DELIMITER $$')[0]
    if args.mode in ('trial', 'check-tables'):
        sql = sql.replace('CREATE DATABASE tracking ', 'CREATE DATABASE '+target+' ')
        sql = sql.replace('USE tracking;', 'USE '+target+';').replace('tracking.entity_changes', target+'.entity_changes')
    execute(sql)
    print('Installed migration into '+target)
    if args.mode == 'check-tables':
        setup = f"USE {target}; SET SESSION time_zone = '+00:00'; START TRANSACTION; "
        company = "INSERT INTO companies (company_id, canonical_name, evidence, observed_at) VALUES ('cmp_00000000-0000-4000-8000-000000000001', 'Synthetic Company', JSON_ARRAY(JSON_OBJECT('source','schema_test','reference','synthetic')), CURRENT_TIMESTAMP(6)); "
        product = "INSERT INTO products (product_id, canonical_name, product_type, sector_id, evidence, observed_at) VALUES ('prd_00000000-0000-4000-8000-000000000001', 'Synthetic Product', 'product', 'robotics', JSON_ARRAY(JSON_OBJECT('source','schema_test','reference','synthetic')), CURRENT_TIMESTAMP(6)); "
        execute(setup+company+product+"ROLLBACK;")
        failures = [
            ('empty evidence', 3819, "UPDATE products SET evidence = JSON_ARRAY();"),
            ('invalid priority', 3819, "UPDATE products SET prediction_priority = 6;"),
            ('invalid stable ID', 3819, "INSERT INTO companies (company_id, canonical_name, evidence, observed_at) VALUES ('bad-id','Invalid',JSON_ARRAY('test'),CURRENT_TIMESTAMP(6));"),
            ('missing company FK', 1452, "INSERT INTO product_companies (product_id,company_id,role,evidence,observed_at) VALUES ('prd_00000000-0000-4000-8000-000000000001','cmp_00000000-0000-4000-8000-000000000099','owner',JSON_ARRAY('test'),CURRENT_TIMESTAMP(6));"),
        ]
        for label, code, statement in failures:
            try:
                execute(setup+company+product+statement+' ROLLBACK;')
            except RuntimeError as error:
                if f'ERROR {code} ' not in str(error):
                    raise
                print('PASS: rejected '+label)
            else:
                raise RuntimeError('Constraint check did not reject '+label)
        print(execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '"+target+"'; SELECT COUNT(*) FROM information_schema.referential_constraints WHERE constraint_schema = '"+target+"'; SELECT (SELECT COUNT(*) FROM "+target+".companies)+(SELECT COUNT(*) FROM "+target+".products);"))
        print('Table-only trial passed; audit triggers remain uninstalled pending the RDS parameter prerequisite.')
        return
    smoke = (ROOT/'schemas'/'rds-tracking-mysql-smoke.sql').read_text().replace('USE tracking;', 'USE '+target+';')
    print(execute(smoke))
    print(execute("SELECT COUNT(*) AS tables_count FROM information_schema.tables WHERE table_schema = '"+target+"'; SELECT COUNT(*) AS triggers_count FROM information_schema.triggers WHERE trigger_schema = '"+target+"';"))
    print('Synthetic smoke data rolled back; no company/product seed data loaded.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Avoid full tracebacks containing local secrets or response objects.
        print(type(error).__name__+': '+str(error), file=sys.stderr)
        sys.exit(1)
