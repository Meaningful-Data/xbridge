"""XML-001: The file MUST be well-formed XML."""

from __future__ import annotations

from lxml import etree

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl


@rule_impl("XML-001")
def check_xml_wellformedness(ctx: ValidationContext) -> None:
    """Check that the input file is well-formed XML.

    If the engine already parsed the XML successfully (ctx.xml_root is
    set), the file is well-formed and no work is needed.  Otherwise,
    attempts to parse raw_bytes with lxml to capture the error details.
    """
    if ctx.xml_root is not None:
        return  # Already parsed successfully — well-formed

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
