"""Deploy a content-addressed pilot release to m7i through the t3 controller.

No recurring collection job, table publication, IAM or database mutation.
"""
from __future__ import annotations

import hashlib
import json
import shlex
import tarfile
import tempfile
from pathlib import Path

import boto3
from raw_parsers.release import source_paths as raw_parser_paths

ROOT = Path(__file__).resolve().parent
BUCKET = "data-collection-059416028963-us-east-1-an"
WORKER = "i-06241bd1c4e91c2fc"


def main():
    names = ["test_metadata_engine.py", "test_metadata_sec_documents.py", "metadata_engine_sec_document_pilot.py"]
    names += [str(p.relative_to(ROOT)) for p in sorted((ROOT / "metadata_engine").rglob("*")) if p.is_file() and "__pycache__" not in p.parts]
    names += raw_parser_paths()
    session = boto3.Session(region_name="us-east-1")
    with tempfile.TemporaryDirectory(prefix="metadata-sec-pilot-") as directory:
        package = Path(directory) / "release.tgz"
        with tarfile.open(package, "w:gz") as archive:
            for name in names:
                archive.add(ROOT / name, arcname=name)
        body = package.read_bytes()
    sha = hashlib.sha256(body).hexdigest()
    key = "research-data/constellation-backfill/deployments/metadata-engine/sec-document-" + sha + ".tgz"
    session.client("s3").put_object(Bucket=BUCKET, Key=key, Body=body, ServerSideEncryption="AES256", IfNoneMatch="*")
    release = "/opt/constellation/metadata-engine-releases/" + sha
    commands = ["set -eu", "install -d -o ec2-user -g ec2-user " + release,
                "aws s3 cp " + shlex.quote("s3://" + BUCKET + "/" + key) + " " + release + "/release.tgz --region us-east-1",
                "printf '%s  %s\\n' " + sha + " " + release + "/release.tgz | sha256sum -c -",
                "tar -xzf " + release + "/release.tgz -C " + release,
                "chown -R ec2-user:ec2-user " + release,
                "cd " + release,
                "runuser -u ec2-user -- /opt/constellation/.venv/bin/python -B -m unittest test_metadata_engine test_metadata_sec_documents",
                "runuser -u ec2-user -- /opt/constellation/.venv/bin/python -B metadata_engine_sec_document_pilot.py"]
    command_id = session.client("ssm").send_command(InstanceIds=[WORKER], DocumentName="AWS-RunShellScript", Parameters={"commands": ["\n".join(commands)]}, TimeoutSeconds=180)["Command"]["CommandId"]
    receipt = {"command_id": command_id, "worker_instance_id": WORKER, "package_sha256": sha,
               "release_path": release, "s3_package": "s3://" + BUCKET + "/" + key}
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
