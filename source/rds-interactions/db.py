import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import boto3
import pymysql
from pymysql.connections import Connection


AWS_REGION = "us-east-1"
SECRET_ID = "rds!cluster-9c465be2-39f2-4ea3-a060-ba04f3634449"

DB_HOST = "database-1-instance-1.c3uguw62gg4j.us-east-1.rds.amazonaws.com"
DB_PORT = 3306
DB_NAME = "research"

CA_CERTIFICATE = Path(__file__).parent / "certs" / "global-bundle.pem"


def get_connection() -> Connection:
    """Open an encrypted connection to the research database."""

    secrets_client = boto3.client(
        "secretsmanager",
        region_name=AWS_REGION,
    )

    response = secrets_client.get_secret_value(SecretId=SECRET_ID)
    credentials = json.loads(response["SecretString"])

    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=credentials["username"],
        password=credentials["password"],
        database=DB_NAME,
        charset="utf8mb4",
        connect_timeout=10,
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
        ssl_ca=str(CA_CERTIFICATE),
        ssl_verify_cert=True,
        ssl_verify_identity=True,
    )


@contextmanager
def database_connection() -> Iterator[Connection]:
    """Commit successful work, roll back failures, and always close."""

    connection = get_connection()

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()