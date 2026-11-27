"""Compatibility imports for the shared nmpa tables parser."""
from raw_parsers.nmpa_tables import (
    TableParser as TableParser,
    DetailError as DetailError,
    require as require,
    digest as digest,
    clean as clean,
    parse_detail_page as parse_detail_page,
    structured_detail as structured_detail,
    BASE_URL as BASE_URL,
    VERSION as VERSION,
    MISSING as MISSING,
    LABELS as LABELS,
    DATES as DATES,
)
