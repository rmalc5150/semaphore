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
    fields = parse_detail_page(document)
    values = {}
    for field in fields:
        value = clean(field["value"])
        if value not in MISSING:
            values.setdefault(clean(field["label"]), []).append(value)
    require(any(registration == v for v in values.get("登记号", [])), "nmpa_detail_identity_mismatch")
    root = html.fromstring(document)
    status_detail = next((clean(node.tail) for node in root.xpath('//div[contains(@class,"sDPTit2")]')
                          if clean(''.join(node.itertext())).endswith('试验状态') and clean(node.tail)), None)
    tables = []
    investigators = []
    sites = []
    aliases = []
    endpoints = []
    for table in root.xpath("//table"):
        rows = [[clean(" ".join(cell.itertext())) for cell in row.xpath("./th|./td")]
                for row in table.xpath("./tr|./tbody/tr")]
        if not rows:
            continue
        header = rows[0]
        if "机构名称" in header and "主要研究者" in header:
            for cells in rows[1:]:
                if len(cells) == len(header):
                    source = dict(zip(header, cells))
                    sites.append({"institution": source.get("机构名称"), "investigator": source.get("主要研究者"),
                                  "country": source.get("国家或地区"), "province": source.get("省（州）"), "city": source.get("城市")})
        if "姓名" in header:
            person = {}
            for cells in rows:
                for key, target in (("姓名", "name"), ("单位名称", "institution"), ("职称", "title")):
                    if key in cells and cells.index(key) + 1 < len(cells):
                        person[target] = cells[cells.index(key) + 1]
            if person.get("name"):
                investigators.append(person)
        if "指标" in header and "评价时间" in header:
            labels = table.xpath('ancestor::tr[1]/th[1]')
            role = clean(' '.join(labels[0].itertext())) if labels else None
            endpoints.append({"source_role": role, "source_header": header[1:] if header[0] == "序号" else header,
                              "rows": [r[1:] if header[0] == "序号" else r for r in rows[1:] if len(r) == len(header)]})
        # Keep non-contact tabular evidence for study interpretation. Original
        # HTML and all legacy labeled fields remain separately available.
        if any(k in header for k in ("机构名称", "指标", "版本号")):
            tables.append({"header": header, "rows": rows[1:]})
    names = list(dict.fromkeys(v for key in ("申请人名称", "申办者名称", "申办者") for v in values.get(key, [])
                              if not re.fullmatch(r"[\d\s|,，]+", v)))
    for label in ("药物名称", "试验药"):
        for value in values.get(label, []):
            aliases.extend(clean(v) for v in re.findall(
                r"(?:中文通用名|英文通用名|商品名称|曾用名)[:：]\s*(.*?)(?=中文通用名|英文通用名|商品名称|剂型|规格|用法|用药|$)", value))
    milestones = []
    from datetime import date
    for label, kind in DATES.items():
        for value in values.get(label, []):
            for stamp in re.findall(r"20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}", value):
                parts = re.split(r"[-/.]", stamp)
                try:
                    stamp = date(*map(int, parts)).isoformat()
                except ValueError:
                    continue
                fact = {"kind": kind, "date": stamp, "source_label": label, "source_value": value}
                if fact not in milestones:
                    milestones.append(fact)
    result = {key: next(iter(values.get(label, [])), None) for key, label in LABELS.items()}
    if result.get('drug_name') and '曾用名:' in result['drug_name']:
        current, former = result['drug_name'].split('曾用名:', 1)
        result['drug_name'] = current.strip()
        if former.strip() and former.strip() not in MISSING:
            aliases.append(former.strip())
    result.update(version=VERSION, registration_number=registration,
        status=status_detail or next(iter(values.get("试验状态", [])), None), sponsors=names,
        recruitment_status=next((s for s in ('尚未招募','招募完成','暂停招募','停止招募','招募中') if s in (status_detail or '')), None),
        professional_title=next(iter(values.get('试验专业题目', [])), None),
        public_title=next(iter(values.get('试验通俗题目', [])), None),
        drug_aliases=sorted(set(v for v in aliases if v and v not in MISSING)),
        related_registration_ids=sorted(set(re.findall(r"CTR20\d{6,}", " ".join(values.get("相关登记号", []))))),
        investigators=investigators, sites=sites, endpoints=endpoints, source_tables=tables, milestones=milestones,
        company_relationships=[{"name": n, "role": "listed_trial_applicant_or_sponsor", "identity_status": "source_name_only"} for n in names])
    result["missing_core_fields"] = [k for k in ("drug_name", "status", "sponsors", "phase") if not result.get(k)]
    return result


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
