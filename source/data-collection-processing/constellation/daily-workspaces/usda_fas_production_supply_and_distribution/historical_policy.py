"""Shared historical scope, separate from daily origins and observation dates."""
from datetime import date

from research_contract import ROOT, load_json

POLICY_PATH = ROOT / "config/historical-collection.json"


def historical_start():
    policy = load_json(POLICY_PATH)
    if policy.get("schema_version") != "1.0" or policy.get("start_inclusive") is not True or policy.get("end_exclusive") is not True:
        raise ValueError("invalid historical collection policy")
    return date.fromisoformat(policy["start_date"])


def add_end_option(parser):
    parser.add_argument("--end-date", type=date.fromisoformat,
        help="historical exclusive end; omitted START uses the shared historical start date")


def resolve_dates(parser, args, mode):
    """Preserve explicit windows and daily semantics; require a pinned end."""
    if mode != "historical":
        if args.end_date is not None:
            parser.error("--end-date is only supported for historical collection")
        return
    if args.end is not None and args.end_date is not None:
        parser.error("supply END or --end-date, not both")
    args.start = args.start if args.start is not None else historical_start()
    args.end = args.end if args.end is not None else args.end_date
    if args.end is None:
        parser.error("historical requires END or --end-date; START defaults to the shared historical start")
