"""XML-003: The root element MUST be xbrli:xbrl."""

from __future__ import annotations

from lxml import etree

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl

_XBRLI_XBRL = "{http://www.xbrl.org/2003/instance}xbrl"


@rule_impl("XML-003")
def check_root_element(ctx: ValidationContext) -> None:
    """Check that the root element is xbrli:xbrl.

    Parses raw_bytes with lxml and inspects the root tag. Skips
    silently when parsing fails (XML-001 handles malformed XML).
    """
    try:
        root = etree.fromstring(ctx.raw_bytes)
    except etree.XMLSyntaxError:
        return

    if root.tag == _XBRLI_XBRL:
        return

    ctx.add_finding(
        location=str(ctx.file_path),
        context={"detail": f"Root element is '{root.tag}', expected '{_XBRLI_XBRL}'."},
    )
