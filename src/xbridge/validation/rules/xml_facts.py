"""XML-040..XML-043: Fact structure checks.

All rules use ``ctx.xml_root`` (parsed once by the engine).
A **single-pass** scan of the root's direct children collects data
for all four rules.  The scan result is cached per root so subsequent
rule functions reuse it.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from lxml import etree

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl
from xbridge.validation.rules._helpers import fact_label, is_fact

_XSI_NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"


def _is_valid_decimals(value: str) -> bool:
    """Check if *value* is 'INF' or a valid integer string."""
    if value == "INF":
        return True
    # Must parse as an integer (no decimals, no whitespace quirks).
    try:
        int(value)
    except ValueError:
        return False
    # Reject strings that int() accepts but are not strict integers
    # (e.g., " 2 " — Python's int() strips whitespace).
    return value.strip() == value


# ---------------------------------------------------------------------------
# Scan result & single-pass scanner
# ---------------------------------------------------------------------------
class _ScanResult:
    """Data collected in one pass over root's direct children."""

    __slots__ = (
        "precision_facts",
        "bad_decimals_facts",
        "xsi_nil_facts",
        "empty_string_facts",
    )

    def __init__(self) -> None:
        # XML-040: fact labels with @precision
        self.precision_facts: List[str] = []
        # XML-041: (label, decimals_value)
        self.bad_decimals_facts: List[Tuple[str, str]] = []
        # XML-042: fact labels with @xsi:nil
        self.xsi_nil_facts: List[str] = []
        # XML-043: fact labels of empty string facts
        self.empty_string_facts: List[str] = []


# Single-entry cache keyed by root object reference.
_last_scan: Optional[Tuple[etree._Element, _ScanResult]] = None


def _scan(root: etree._Element) -> _ScanResult:
    """Single-pass scan of root children; cached per *root*."""
    global _last_scan  # noqa: PLW0603
    if _last_scan is not None and _last_scan[0] is root:
        return _last_scan[1]

    r = _ScanResult()

    for child in root:
        if not is_fact(child):
            continue

        label = fact_label(child)

        # XML-040: no @precision
        if child.get("precision") is not None:
            r.precision_facts.append(label)

        # XML-041: valid @decimals
        decimals = child.get("decimals")
        if decimals is not None and not _is_valid_decimals(decimals):
            r.bad_decimals_facts.append((label, decimals))

        # XML-042: no @xsi:nil
        if child.get(_XSI_NIL) is not None:
            r.xsi_nil_facts.append(label)

        # XML-043: no empty string facts (non-numeric only)
        if child.get("unitRef") is None:
            text = (child.text or "").strip()
            if text == "":
                r.empty_string_facts.append(label)

    _last_scan = (root, r)
    return r


# ---------------------------------------------------------------------------
# XML-040  No precision attribute
# ---------------------------------------------------------------------------


@rule_impl("XML-040")
def check_no_precision(ctx: ValidationContext) -> None:
    """The @decimals attribute MUST be used, not @precision."""
    root = ctx.xml_root
    if root is None:
        return
    scan = _scan(root)
    for label in scan.precision_facts:
        ctx.add_finding(
            location=f"fact:{label}",
            context={"detail": f"Fact '{label}' uses @precision instead of @decimals."},
        )


# ---------------------------------------------------------------------------
# XML-041  Valid decimals value
# ---------------------------------------------------------------------------


@rule_impl("XML-041")
def check_decimals_value(ctx: ValidationContext) -> None:
    """The @decimals value MUST be a valid integer or 'INF'."""
    root = ctx.xml_root
    if root is None:
        return
    scan = _scan(root)
    for label, decimals in scan.bad_decimals_facts:
        ctx.add_finding(
            location=f"fact:{label}",
            context={
                "detail": (
                    f"Fact '{label}' has invalid @decimals value "
                    f"'{decimals}' (expected integer or 'INF')."
                )
            },
        )


# ---------------------------------------------------------------------------
# XML-042  No xsi:nil
# ---------------------------------------------------------------------------


@rule_impl("XML-042")
def check_no_xsi_nil(ctx: ValidationContext) -> None:
    """@xsi:nil MUST NOT be used on facts."""
    root = ctx.xml_root
    if root is None:
        return
    scan = _scan(root)
    for label in scan.xsi_nil_facts:
        ctx.add_finding(
            location=f"fact:{label}",
            context={"detail": f"Fact '{label}' uses @xsi:nil."},
        )


# ---------------------------------------------------------------------------
# XML-043  No empty string facts
# ---------------------------------------------------------------------------


@rule_impl("XML-043")
def check_no_empty_string_facts(ctx: ValidationContext) -> None:
    """String-type facts (no unitRef) MUST NOT be empty."""
    root = ctx.xml_root
    if root is None:
        return
    scan = _scan(root)
    for label in scan.empty_string_facts:
        ctx.add_finding(
            location=f"fact:{label}",
            context={"detail": f"String-type fact '{label}' is empty."},
        )
