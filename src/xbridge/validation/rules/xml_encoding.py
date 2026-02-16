"""XML-002: The file MUST use UTF-8 encoding."""

from __future__ import annotations

import re

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl

_ENCODING_RE = re.compile(
    rb"""<\?xml\s[^?]*encoding\s*=\s*['"]([^'"]+)['"]""",
)


@rule_impl("XML-002")
def check_utf8_encoding(ctx: ValidationContext) -> None:
    """Check that the XML declaration encoding is UTF-8.

    Parses the encoding attribute from the raw bytes of the XML
    declaration. Files without an explicit encoding default to UTF-8
    per the XML specification and pass this check.
    """
    match = _ENCODING_RE.search(ctx.raw_bytes[:200])
    if match is None:
        # No encoding attribute found — UTF-8 is the XML default.
        return

    declared = match.group(1).decode("ascii", errors="replace")
    if declared.lower() == "utf-8":
        return

    ctx.add_finding(
        location=f"{ctx.file_path}:1",
        context={"detail": f"Declared encoding is '{declared}', expected 'utf-8'."},
    )
