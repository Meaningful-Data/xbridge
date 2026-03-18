"""XML-003: The root element MUST be xbrli:xbrl."""

from __future__ import annotations

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl

_XBRLI_XBRL = "{http://www.xbrl.org/2003/instance}xbrl"


@rule_impl("XML-003")
def check_root_element(ctx: ValidationContext) -> None:
    """Check that the root element is xbrli:xbrl.

    Uses the pre-parsed xml_root from the engine. Skips when the root
    is unavailable (XML-001 handles malformed XML).
    """
    if ctx.xml_root is None:
        return

    if ctx.xml_root.tag == _XBRLI_XBRL:
        return

    ctx.add_finding(
        location=str(ctx.file_path),
        context={"detail": f"Root element is '{ctx.xml_root.tag}', expected '{_XBRLI_XBRL}'."},
    )
