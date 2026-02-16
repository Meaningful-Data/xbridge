"""XML-010 / XML-012: Schema reference (schemaRef) checks."""

from __future__ import annotations

import json
from pathlib import Path

from lxml import etree

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl

_LINK_SCHEMA_REF = "{http://www.xbrl.org/2003/linkbase}schemaRef"
_XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
_INDEX_FILE = Path(__file__).parents[2] / "modules" / "index.json"


def _get_schema_refs(raw_bytes: bytes) -> list[etree._Element] | None:
    """Parse XML and return schemaRef elements, or None if XML is malformed."""
    try:
        root = etree.fromstring(raw_bytes)
    except etree.XMLSyntaxError:
        return None
    return [child for child in root if child.tag == _LINK_SCHEMA_REF]


def _load_known_entry_points() -> set[str]:
    """Load the set of known entry point URLs from the module index."""
    if not _INDEX_FILE.exists():
        return set()
    with open(_INDEX_FILE, encoding="utf-8") as f:
        data: dict[str, str] = json.load(f)
    return set(data.keys())


@rule_impl("XML-010")
def check_single_schema_ref(ctx: ValidationContext) -> None:
    """Check that exactly one link:schemaRef element is present."""
    schema_refs = _get_schema_refs(ctx.raw_bytes)
    if schema_refs is None:
        return  # Malformed XML — XML-001 handles it

    count = len(schema_refs)
    if count == 1:
        return

    if count == 0:
        ctx.add_finding(
            location=str(ctx.file_path),
            context={"detail": "No link:schemaRef element found."},
        )
    else:
        ctx.add_finding(
            location=str(ctx.file_path),
            context={"detail": (f"Expected exactly 1 link:schemaRef, found {count}.")},
        )


@rule_impl("XML-012")
def check_schema_ref_entry_point(ctx: ValidationContext) -> None:
    """Check that the schemaRef href resolves to a known entry point URL."""
    schema_refs = _get_schema_refs(ctx.raw_bytes)
    if schema_refs is None:
        return  # Malformed XML — XML-001 handles it

    if len(schema_refs) != 1:
        return  # XML-010 handles missing/multiple

    href = schema_refs[0].get(_XLINK_HREF)
    if href is None:
        ctx.add_finding(
            location=str(ctx.file_path),
            context={"detail": "link:schemaRef has no xlink:href attribute."},
        )
        return

    known = _load_known_entry_points()
    if href not in known:
        ctx.add_finding(
            location=str(ctx.file_path),
            context={"detail": (f"schemaRef href '{href}' is not a known entry point URL.")},
        )
