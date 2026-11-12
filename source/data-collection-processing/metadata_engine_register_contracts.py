"""Register reviewed compact source contracts in the empty control plane."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from metadata_engine.contracts import load_contract
from rds_management_access import ca_bundle, settings


def quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def main():
    _, instance, admin, _ = settings()
    env = os.environ.copy(); env["MYSQL_PWD"] = admin["password"]
    command = ["mysql", "--no-defaults", "--protocol=TCP", "--host=" + instance["Endpoint"]["Address"], "--port=" + str(instance["Endpoint"]["Port"]), "--user=" + admin["username"], "--ssl", "--ssl-ca=" + str(ca_bundle()), "--ssl-verify-server-cert", "--batch", "--skip-reconnect"]
    directory = Path(__file__).parent / "metadata_engine" / "contracts"
    contracts = [load_contract(path) for path in sorted(directory.glob("*.json"))]
    statements = ["USE metadata_engine", "START TRANSACTION"]
    for contract in contracts:
        body = json.dumps(contract, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(body.encode()).hexdigest()
        key = (quote(contract["source_key"]), quote(contract["contract_version"]))
        statements.append("INSERT INTO source_contracts(source_key,contract_version,adapter,contract_json,contract_sha256,registered_at) VALUES(" + ",".join((*key, quote(contract["adapter"]), "CAST(" + quote(body) + " AS JSON)", quote(digest), "UTC_TIMESTAMP(6)")) + ")")
        raw = contract["raw_requirements"]
        statements.append("INSERT INTO source_raw_requirements(source_key,contract_version,requirement_version,minimum_completeness,required_artifact_kinds,forbidden_shortcuts) VALUES(" + ",".join((*key, quote(raw["version"]), quote(raw["minimum_completeness"]), "CAST(" + quote(json.dumps(raw["required_artifact_kinds"])) + " AS JSON)", "CAST(" + quote(json.dumps(raw["forbidden_shortcuts"])) + " AS JSON)")) + ")")
    statements.append("COMMIT")
    result = subprocess.run(command, input=";\n".join(statements) + ";\n", text=True, capture_output=True, env=env, timeout=90)
    if result.returncode:
        raise RuntimeError(result.stderr.replace(admin["password"], "[REDACTED]").strip())
    print(json.dumps({"registered_contracts": [c["source_key"] for c in contracts], "registered_at": datetime.now(timezone.utc).isoformat()}, indent=2))


if __name__ == "__main__":
    main()
