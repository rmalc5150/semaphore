"""Install the fresh Metadata Labelling Engine MySQL control plane once.

The migration is forward-only and refuses an existing ``metadata_engine``
database.  It leaves constellation_operations untouched.
"""
from __future__ import annotations

import os
import subprocess

from rds_management_access import ROOT, ca_bundle, settings


def main():
    _, instance, secret, _ = settings()
    env = os.environ.copy()
    env["MYSQL_PWD"] = secret["password"]
    command = [
        "mysql", "--no-defaults", "--protocol=TCP", "--host=" + instance["Endpoint"]["Address"],
        "--port=" + str(instance["Endpoint"]["Port"]), "--user=" + secret["username"], "--ssl",
        "--ssl-ca=" + str(ca_bundle()), "--ssl-verify-server-cert", "--connect-timeout=15",
        "--batch", "--skip-reconnect",
    ]
    check = subprocess.run(command, input="SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name='metadata_engine';", text=True, capture_output=True, env=env, timeout=60)
    if check.returncode:
        raise RuntimeError(check.stderr.replace(secret["password"], "[REDACTED]").strip())
    if check.stdout.strip() not in {"0", "COUNT(*)\n0"}:
        raise RuntimeError("metadata_engine already exists; refusing to overwrite")
    sql = (ROOT / "schemas" / "rds-metadata-engine-mysql.sql").read_text()
    result = subprocess.run(command, input=sql, text=True, capture_output=True, env=env, timeout=180)
    if result.returncode:
        raise RuntimeError(result.stderr.replace(secret["password"], "[REDACTED]").strip())
    verify = subprocess.run(command, input="SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='metadata_engine';", text=True, capture_output=True, env=env, timeout=60)
    if verify.returncode:
        raise RuntimeError(verify.stderr.replace(secret["password"], "[REDACTED]").strip())
    print("metadata_engine tables=" + verify.stdout.strip().splitlines()[-1])


if __name__ == "__main__":
    main()
