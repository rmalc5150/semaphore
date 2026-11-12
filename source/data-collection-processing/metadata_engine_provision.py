"""Provision the m7i's constrained Metadata Labelling Engine database login."""
from __future__ import annotations

import json
import os
import secrets
import subprocess

import boto3

from rds_management_access import ca_bundle, settings


SECRET_NAME = "metadata-engine/worker"
USER = "metadata_engine_worker"
ROLE = "constellation-backfill-worker"
POLICY = "metadata-engine-worker-secret"


def mysql(instance, admin, sql):
    env = os.environ.copy()
    env["MYSQL_PWD"] = admin["password"]
    command = ["mysql", "--no-defaults", "--protocol=TCP", "--host=" + instance["Endpoint"]["Address"],
               "--port=" + str(instance["Endpoint"]["Port"]), "--user=" + admin["username"], "--ssl",
               "--ssl-ca=" + str(ca_bundle()), "--ssl-verify-server-cert", "--batch", "--skip-column-names"]
    result = subprocess.run(command, input=sql, text=True, capture_output=True, env=env, timeout=60)
    if result.returncode:
        raise RuntimeError(result.stderr.replace(admin["password"], "[REDACTED]").strip())
    return result.stdout


def main():
    session, instance, admin, _ = settings()
    if mysql(instance, admin, "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name='metadata_engine';").strip() != "1":
        raise RuntimeError("metadata_engine database is missing")
    sm = session.client("secretsmanager")
    try:
        worker_secret = {"username": USER, "host": instance["Endpoint"]["Address"], "port": instance["Endpoint"]["Port"], "database": "metadata_engine", "password": secrets.token_urlsafe(32)}
        result = sm.create_secret(
            Name=SECRET_NAME,
            Description="Constrained m7i MySQL login for Metadata Labelling Engine",
            SecretString=json.dumps(worker_secret),
        )
        arn = result["ARN"]
    except sm.exceptions.ResourceExistsException:
        raise RuntimeError("metadata-engine worker secret already exists; refusing credential rotation")
    secret = worker_secret
    try:
        mysql(instance, admin, "CREATE USER '" + USER + "'@'%' IDENTIFIED BY '" + secret["password"].replace("'", "''") + "' REQUIRE SSL; GRANT SELECT, INSERT, UPDATE ON metadata_engine.* TO '" + USER + "'@'%';")
        policy = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": arn}]}
        session.client("iam").put_role_policy(RoleName=ROLE, PolicyName=POLICY, PolicyDocument=json.dumps(policy))
        grants = mysql(instance, admin, "SHOW GRANTS FOR '" + USER + "'@'%';")
        if "metadata_engine" not in grants or "tracking" in grants or "constellation_operations" in grants:
            raise RuntimeError("unexpected metadata-engine worker grants")
    except Exception:
        # A failed grant must not leave an undisclosed usable credential.
        mysql(instance, admin, "DROP USER IF EXISTS '" + USER + "'@'%';")
        sm.delete_secret(SecretId=arn, ForceDeleteWithoutRecovery=True)
        raise
    print(json.dumps({"secret_arn": arn, "user": USER, "database": "metadata_engine", "grants": grants.splitlines()}, indent=2))


if __name__ == "__main__":
    main()
