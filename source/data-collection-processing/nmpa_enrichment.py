"""Structured NMPA source facts and conservative, evidence-dated trial changes."""
import re
import unicodedata
from lxml import html
from nmpa_drug_trials import parse_detail_page
from research_contract import digest
from regulatory_collection import SourceIssue, require

VERSION = "nmpa-structured-changes-v1"
MISSING = {"", "暂未填写此信息", "企业选择不公示", "NA", "N/A", "无"}
LABELS = {"drug_name": "药物名称", "indication": "适应症", "phase": "试验分期",
          "design": "设计类型", "randomisation": "随机化", "masking": "盲法",
          "scope": "试验范围", "protocol_number": "试验方案编号", "protocol_version": "方案最新版本号",
          "target_enrolment": "目标入组人数", "actual_enrolment": "实际入组总人数"}
DATES = {"首次公示信息日期": "FIRST_PUBLIC_DISCLOSURE", "首次公示日期": "FIRST_PUBLIC_DISCLOSURE",
         "第一例受试者签署知情同意书日期": "FIRST_INFORMED_CONSENT",
         "第一例受试者入组日期": "FIRST_PARTICIPANT_ENROLLED", "试验完成日期": "TRIAL_COMPLETED",
         "试验终止日期": "TRIAL_TERMINATED"}


def clean(value):
    return " ".join(unicodedata.normalize("NFKC", value or "").split())


def canonical(value):
    if isinstance(value, str):
        return re.sub(r"\s+", "", clean(value))
    if isinstance(value, list):
        return sorted((canonical(v) for v in value), key=lambda v: str(v))
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in sorted(value.items())}
    return value


def structured_detail(document, registration):
    from metadata_engine.nmpa_tables import structured_detail as parse, DetailError
    try:return parse(document,registration)
    except DetailError as error:raise SourceIssue(str(error))from None


def valid_detail(document, registration):
    try:
        if any(t in document.lower() for t in ("验证码", "request has been blocked")):
            return False
        result = structured_detail(document, registration)
        labels = {clean(f['label']) for f in parse_detail_page(document)}
        return bool(result.get('drug_name') and result.get('status') and '试验分期' in labels
            and '申请人名称' in labels and '试验状态信息' in document
            and any(m["kind"] == "FIRST_PUBLIC_DISCLOSURE" for m in result["milestones"]))
    except (SourceIssue, ValueError):
        return False


def significant(snapshot):
    keys = [*LABELS, "status", "recruitment_status", "sponsors", "drug_aliases", "related_registration_ids", "sites", "endpoints"]
    result = {k: canonical(snapshot.get(k)) for k in keys if snapshot.get(k) not in (None, [], "")}
    if "status" in result:
        result["status"] = re.sub(r"[()（）\-—·]", "", result["status"])
    return result


def changes(previous, current):
    before, after = significant(previous), significant(current)
    # Filling previously absent detail is enrichment, not a phase/site change.
    return {key: {"before": previous[key], "after": current[key]} for key in before.keys() & after.keys()
            if before[key] != after[key]}


def inventory_snapshot(payload):
    cells = payload.get("search_result_columns", [])
    return {"registration_number": payload["registration_number"], "status": cells[2] if len(cells) > 2 else None,
            "drug_name": cells[3] if len(cells) > 3 else None, "indication": cells[4] if len(cells) > 4 else None}


def event_facts(registration, previous, current, previous_at, observed_at):
    events = []
    if previous is None:
        events.append({"id": registration + ":first_observed", "action": "FIRST_OBSERVED",
                       "date_basis": "first_observed_not_trial_start", "date": observed_at})
    else:
        delta = changes(previous, current)
        if delta:
            events.append({"id": registration + ":change:" + digest([previous_at, observed_at, delta]),
                "action": "TRIAL_CHANGE_OBSERVED", "changes": delta, "date": observed_at,
                "date_basis": "observed_change_not_actual_change_date",
                "observation_interval": {"after": previous_at, "on_or_before": observed_at}})
    for milestone in current.get("milestones", []):
        events.append({"id": registration + ":milestone:" + milestone["kind"] + ":" + milestone["date"],
                       "action": milestone["kind"], "date": milestone["date"], "date_basis": "explicit_source_date", "source_fact": milestone})
    return events
