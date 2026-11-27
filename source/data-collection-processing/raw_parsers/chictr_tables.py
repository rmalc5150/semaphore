"""Pure ChiCTR HTML table parser shared by capture and raw verification."""
from __future__ import annotations
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin
BASE_URL='https://www.chictr.org.cn/'

def clean_text(parts: list[str]) -> str:
    return " ".join("".join(parts).replace("\xa0", " ").split())


class TableParser(HTMLParser):
    """Collect top-level cells from every HTML table row."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[dict[str, Any]]] = []
        self._row: list[dict[str, Any]] | None = None
        self._cell: dict[str, Any] | None = None
        self._cell_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "tr" and self._row is None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            if self._cell is None:
                self._cell = {"text": [], "links": [], "tag": tag}
                self._cell_depth = 1
            else:
                self._cell_depth += 1
        elif tag == "a" and self._cell is not None:
            self._cell["links"].append(
                {"href": attributes.get("href", ""), "title": attributes.get("title", "")}
            )
        elif tag == "br" and self._cell is not None:
            self._cell["text"].append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._cell is not None:
            self._cell_depth -= 1
            if self._cell_depth == 0:
                self._cell["text"] = clean_text(self._cell["text"])
                assert self._row is not None
                self._row.append(self._cell)
                self._cell = None
        elif tag == "tr" and self._row is not None and self._cell is None:
            if self._row:
                self.rows.append(self._row)
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell["text"].append(data)


def parse_detail_page(document: str) -> list[dict[str, Any]]:
    """Return all labelled fields without imposing a brittle fixed schema."""
    parser = TableParser()
    parser.feed(document)
    fields: list[dict[str, Any]] = []
    for row in parser.rows:
        if len(row) < 2:
            continue
        label = row[0]["text"].strip(" ：:")
        value = " | ".join(cell["text"] for cell in row[1:] if cell["text"])
        if label and value and label != value:
            links = [urljoin(BASE_URL, link["href"]) for cell in row[1:] for link in cell["links"]]
            field: dict[str, Any] = {"label": label, "value": value}
            if links:
                field["links"] = links
            fields.append(field)
    return fields



def has_trial_detail(document):
    import re
    fields=parse_detail_page(document)
    return any(re.fullmatch(r'ChiCTR[A-Za-z0-9-]*\d{5,}',f['value'].strip()) for f in fields if 'registration number' in f['label'].lower() or '注册号' in f['label']) and any('date of registration' in f['label'].lower() or '注册时间' in f['label'] for f in fields)
