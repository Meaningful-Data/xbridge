"""EBA-DATE-001: Instance reference date must fall within the module applicability range.

The EBA taxonomy declares, for each module, the reference dates it applies to. These are
stored in the converted module JSON as ``from`` (first applicable reference date) and ``to``
(last applicable reference date, or ``null`` for an open-ended range), and exposed on the
:class:`~xbridge.modules.Module` object as ``from_date`` / ``to_date``.

This rule flags, as an ERROR, an instance whose reference date falls outside that range.
The range is inclusive on both ends: ``from <= reference_date <= to``.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl
from xbridge.validation.rules.csv_parameters import _parse_parameters

# xs:date: YYYY-MM-DD. ISO dates in this format compare correctly with string ordering.
_XS_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _module_range(ctx: ValidationContext) -> Optional[Tuple[Optional[str], Optional[str]]]:
    """Return the module's (from_date, to_date), or None when unavailable."""
    module = ctx.module
    if module is None:
        return None
    return getattr(module, "from_date", None), getattr(module, "to_date", None)


def _check_in_range(ctx: ValidationContext, reference_date: Optional[str], location: str) -> None:
    """Emit a finding when ``reference_date`` falls outside the module range.

    Silently returns when the information needed to decide is missing: no module, no
    applicability ``from`` date, or no/invalid reference date (those are reported by other
    rules). Comparison is inclusive: ``from <= reference_date <= to``.
    """
    module_range = _module_range(ctx)
    if module_range is None:
        return
    from_date, to_date = module_range
    if from_date is None:
        # Module carries no applicability information (e.g. legacy module) — nothing to check.
        return

    if not reference_date or not _XS_DATE_RE.match(reference_date):
        # Missing or malformed reference date is handled by EBA-NAME-050 / CSV-024.
        return

    if reference_date < from_date or (to_date is not None and reference_date > to_date):
        upper = to_date if to_date is not None else "open"
        ctx.add_finding(
            location=location,
            context={
                "detail": (
                    f"reference date {reference_date} is outside the module's "
                    f"applicability range [{from_date}, {upper}]"
                )
            },
        )


@rule_impl("EBA-DATE-001", "xml")
def check_reference_date_in_range_xml(ctx: ValidationContext) -> None:
    """XML: compare the instance period (reference date) against the module range."""
    instance = ctx.xml_instance
    if instance is None:
        return
    reference_date = getattr(instance, "period", None)
    _check_in_range(ctx, reference_date, location="xbrli:context/xbrli:period/xbrli:instant")


@rule_impl("EBA-DATE-001", "csv")
def check_reference_date_in_range_csv(ctx: ValidationContext) -> None:
    """CSV: compare the ``refPeriod`` parameter against the module range."""
    params = _parse_parameters(ctx)
    if not params:
        return
    reference_date = params.get("refPeriod", "").strip()
    _check_in_range(ctx, reference_date, location="reports/parameters.csv")
