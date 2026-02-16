"""XML-001: The file MUST be well-formed XML."""

from __future__ import annotations

from lxml import etree

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl


@rule_impl("XML-001")
def check_xml_wellformedness(ctx: ValidationContext) -> None:
    """Check that the input file is well-formed XML.

    Attempts to parse raw_bytes with lxml. On XMLSyntaxError the rule
    emits an ERROR finding with the parser's diagnostic message.
    """
    try:
        etree.fromstring(ctx.raw_bytes)
    except etree.XMLSyntaxError as e:
        lineno = getattr(e, "lineno", None)
        offset = getattr(e, "offset", None)
        if lineno is not None and offset is not None:
            location = f"{ctx.file_path}:{lineno}:{offset}"
        elif lineno is not None:
            location = f"{ctx.file_path}:{lineno}"
        else:
            location = str(ctx.file_path)

        ctx.add_finding(
            location=location,
            context={"detail": str(e)},
        )
