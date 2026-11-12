"""Verify the m7i can use only its constrained metadata-engine credential."""
from __future__ import annotations

import json
from pathlib import Path

import boto3
import pymysql

SECRET = "metadata-engine/worker"


def main():
    secret = json.loads(boto3.client("secretsmanager", region_name="us-east-1").get_secret_value(SecretId=SECRET)["SecretString"])
    ca = Path(__file__).parent / "config" / "rds-us-east-1-ca-bundle.pem"
    connection = pymysql.connect(host=secret["host"], port=int(secret["port"]), user=secret["username"],
                                 password=secret["password"], database=secret["database"], connect_timeout=15,
                                 ssl={"ca": str(ca), "check_hostname": True})
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM source_contracts")
            count = cursor.fetchone()[0]
    finally:
        connection.close()
    print("metadata_engine_contracts=" + str(count))


if __name__ == "__main__":
    main()
