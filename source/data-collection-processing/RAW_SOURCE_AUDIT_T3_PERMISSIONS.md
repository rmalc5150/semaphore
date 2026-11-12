# Raw-source audit: t3-to-m7i permission boundary

Apply these statements to the existing instance roles only after replacing the
two role/instance ARNs where indicated. They are a least-privilege starting
point for the read-only audit runner; they do not authorize collection, queue,
database, Secrets Manager, deletion, or schedule changes.

## t3 controller role

The t3 controller needs to package the validator, invoke the m7i through SSM,
and read the resulting receipt. It must not read collected raw objects.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "WriteImmutableAuditDeployment",
      "Effect": "Allow",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/status/raw-source-audit/deployments/*",
      "Condition": {"StringEquals": {"s3:x-amz-server-side-encryption": "AES256"}}
    },
    {
      "Sid": "ReadAuditReceiptsOnly",
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/status/raw-source-audit/payload-validation/*"
    },
    {
      "Sid": "RunAuditOnlyOnWorker",
      "Effect": "Allow",
      "Action": ["ssm:SendCommand", "ssm:GetCommandInvocation"],
      "Resource": [
        "arn:aws:ec2:us-east-1:059416028963:instance/i-06241bd1c4e91c2fc",
        "arn:aws:ssm:us-east-1::document/AWS-RunShellScript"
      ]
    }
  ]
}
```

Depending on the account's existing SSM resource-tag conditions, the EC2
instance resource may instead need the managed-instance ARN that the current
controller deployment policy already uses. Preserve those existing conditions.

## m7i worker role

The m7i role needs direct reads of objects named by trusted, committed final
manifests, plus a write-only audit-receipt prefix. No `ListBucket`, delete, or
source/provider permission is needed for this payload pass.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadCommittedArtifactsForAudit",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:GetObjectAttributes"],
      "Resource": "arn:aws:s3:::data-collection-059416028963-us-east-1-an/research-data/*"
    },
    {
      "Sid": "WriteAuditReceiptOnly",
      "Effect": "Allow",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/status/raw-source-audit/payload-validation/*",
      "Condition": {"StringEquals": {"s3:x-amz-server-side-encryption": "AES256"}}
    }
  ]
}
```

`s3:HeadObject` is authorized by `s3:GetObject`. Keep the bucket's existing
SSE/KMS policy requirements; if the bucket uses a customer-managed KMS key,
add only `kms:Decrypt` for m7i and `kms:Encrypt` for the receipt-writing role
on that existing key, constrained with the bucket encryption context.

## Run sequence

On the t3 controller, run:

```bash
python3 constellation/status/deploy_raw_source_audit.py
```

The command is bounded to one referenced batch per catalog entry, skips objects
over 5 MiB, covers all 158 entries (emitting `no_committed_manifest` when none
exists), and uploads only a JSON receipt. It does not call providers or alter
collection state.
