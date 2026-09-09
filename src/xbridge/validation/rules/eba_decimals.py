"""EBA-DEC-001..EBA-DEC-004: Decimals accuracy checks.

Shared rules (XML + CSV).

XML side inspects per-fact ``@decimals`` attributes.
CSV side reads the global decimals parameters from ``parameters.csv``
(``decimalsMonetary``, ``decimalsPercentage``, ``decimalsInteger``,
``decimalsDecimal``).

The checks rely on the taxonomy Module to classify each metric as
monetary, percentage, integer, or decimal.  When no Module is
available a unit-based fallback is used (iso4217:* → monetary,
xbrli:pure → percentage).

Infinite precision is spelled ``INF`` in xBRL-XML and ``#none`` in
xBRL-CSV.  Both are recognised (see ``is_infinite_decimals``) so these
rules behave identically whichever format the report arrives in.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl
from xbridge.validation.rules._helpers import PURE_VALUES, is_infinite_decimals
from xbridge.validation.rules.csv_parameters import _parse_parameters

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Metric-type constants (values of Variable._attributes)
# ---------------------------------------------------------------------------
_TYPE_MONETARY = "$decimalsMonetary"
_TYPE_PERCENTAGE = "$decimalsPercentage"
_TYPE_INTEGER = "$decimalsInteger"
_TYPE_DECIMAL = "$decimalsDecimal"

# Unit-measure prefix used as fallback when no Module is available.
_ISO4217_PREFIX = "iso4217:"

# Frameworks whose monetary-decimals threshold is -6 instead of -4.
# Detected by inspecting the Module URL for these path segments.
_RELAXED_FW_SEGMENTS = frozenset({"/fws/fp/", "/fws/esg/", "/fws/pillar3/", "/fws/rem/"})

_DEFAULT_MONETARY_THRESHOLD = -4
_RELAXED_MONETARY_THRESHOLD = -6

# EBA-DEC-004: any decimals value above this is considered unrealistically high.
_MAX_REALISTIC_DECIMALS = 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Single-entry cache for the metric type map: (module_ref, map).
_last_type_map: Optional[Tuple[Any, Dict[str, str]]] = None


def _build_metric_type_map(ctx: ValidationContext) -> Dict[str, str]:
    """Build a ``{metric_qname: type_string}`` lookup from the Module.

    Keys are the full prefix form stored in the module
    (e.g. ``eba_met:qAZH``) — matching what :attr:`Fact.metric_qname`
    produces after namespace normalisation.

    Falls back to an empty dict if no Module is loaded.
    The result is cached per module object so the three DEC rules
    that call this share a single computation.
    """
    global _last_type_map  # noqa: PLW0603
    module = ctx.module
    if module is None:
        return {}

    if _last_type_map is not None and _last_type_map[0] is module:
        return _last_type_map[1]

    result: Dict[str, str] = {}
    for table in module.tables:
        for variable in table.variables:
            concept = variable.dimensions.get("concept")
            attr = variable._attributes
            if concept and attr:
                result[concept] = attr

    _last_type_map = (module, result)
    return result


def _lookup_metric_type(
    fact: Any,
    type_map: Dict[str, str],
    units: Dict[str, str],
    module_present: bool,
) -> Optional[str]:
    """Resolve the metric-type classification for a fact.

    Lookup order:
      1. ``fact.metric_qname`` in the module's type_map (prefix form).
      2. Unit-based inference (``iso4217:*`` → monetary; ``xbrli:pure`` →
         percentage).  Used when no module is loaded, or when the metric
         is not in the module at all.

    A debug log is emitted when the module *is* loaded but the metric
    could not be found in the type_map — this signals a data-quality or
    taxonomy-mismatch issue that is worth surfacing in diagnostics.
    """
    qname = getattr(fact, "metric_qname", None) or fact.metric
    if qname is not None:
        metric_type = type_map.get(qname)
        if metric_type is not None:
            return metric_type

    # Fall back to unit-based inference.
    inferred = _infer_type_from_unit(units.get(fact.unit, ""))
    if module_present and inferred is not None:
        _logger.debug(
            "EBA-DEC: metric %r not found in module type_map (size=%d); "
            "falling back to unit-based inference → %s",
            qname or fact.metric,
            len(type_map),
            inferred,
        )
    return inferred


def _monetary_threshold(ctx: ValidationContext) -> int:
    """Return the minimum acceptable ``@decimals`` for monetary facts.

    Returns ``-6`` for FP, ESG, Pillar 3, and REM modules; ``-4`` otherwise.
    """
    module = ctx.module
    if module is not None:
        url = getattr(module, "url", None) or ""
        for seg in _RELAXED_FW_SEGMENTS:
            if seg in url:
                return _RELAXED_MONETARY_THRESHOLD
    return _DEFAULT_MONETARY_THRESHOLD


def _parse_decimals(raw: Optional[str]) -> Optional[int]:
    """Parse a ``@decimals`` attribute or decimals parameter value.

    Returns ``None`` for non-numeric facts (no decimals attribute) and for
    either spelling of infinity (``INF`` / ``#none``), which is handled
    separately by :func:`is_infinite_decimals`.
    """
    if raw is None:
        return None
    raw = raw.strip()
    if is_infinite_decimals(raw):
        return None  # handled separately
    try:
        return int(raw)
    except ValueError:
        return None


def _infer_type_from_unit(unit_measure: str) -> Optional[str]:
    """Fallback type inference from the unit measure string."""
    if unit_measure[:8].lower() == _ISO4217_PREFIX[:8]:
        return _TYPE_MONETARY
    if unit_measure in PURE_VALUES:
        return _TYPE_PERCENTAGE
    return None


# ---------------------------------------------------------------------------
# EBA-DEC-001  Monetary facts: @decimals >= threshold
# ---------------------------------------------------------------------------


@rule_impl("EBA-DEC-001", format="xml")
def check_monetary_decimals_xml(ctx: ValidationContext) -> None:
    """Monetary facts: @decimals MUST be >= -4 (or -6 for FP/ESG/P3/REM)."""
    inst = ctx.xml_instance
    if inst is None:
        return
    facts = inst.facts
    units = inst.units
    if facts is None or units is None:
        return

    type_map = _build_metric_type_map(ctx)
    threshold = _monetary_threshold(ctx)
    module_present = ctx.module is not None

    for fact in facts:
        if fact.unit is None or fact.decimals is None:
            continue

        metric = fact.metric_qname or fact.metric or "?"
        metric_type = _lookup_metric_type(fact, type_map, units, module_present)
        if metric_type != _TYPE_MONETARY:
            continue

        dec = _parse_decimals(fact.decimals)
        if dec is not None and dec < threshold:
            ctx.add_finding(
                location=f"fact:{metric}:context:{fact.context}",
                context={
                    "detail": (
                        f"Fact '{metric}' has @decimals={fact.decimals} "
                        f"which is below the minimum threshold of {threshold}."
                    )
                },
            )


# ---------------------------------------------------------------------------
# EBA-DEC-002  Percentage facts: @decimals >= 4
# ---------------------------------------------------------------------------


@rule_impl("EBA-DEC-002", format="xml")
def check_percentage_decimals_xml(ctx: ValidationContext) -> None:
    """Percentage facts: @decimals MUST be >= 4."""
    inst = ctx.xml_instance
    if inst is None:
        return
    facts = inst.facts
    units = inst.units
    if facts is None or units is None:
        return

    type_map = _build_metric_type_map(ctx)
    module_present = ctx.module is not None

    for fact in facts:
        if fact.unit is None or fact.decimals is None:
            continue

        metric = fact.metric_qname or fact.metric or "?"
        metric_type = _lookup_metric_type(fact, type_map, units, module_present)
        if metric_type != _TYPE_PERCENTAGE:
            continue

        dec = _parse_decimals(fact.decimals)
        if dec is not None and dec < 4:
            ctx.add_finding(
                location=f"fact:{metric}:context:{fact.context}",
                context={
                    "detail": (
                        f"Fact '{metric}' has @decimals={fact.decimals} "
                        f"which is below the minimum of 4 for percentage facts."
                    )
                },
            )


# ---------------------------------------------------------------------------
# EBA-DEC-003  Integer facts: @decimals MUST be 0
# ---------------------------------------------------------------------------


@rule_impl("EBA-DEC-003", format="xml")
def check_integer_decimals_xml(ctx: ValidationContext) -> None:
    """Integer facts: @decimals MUST be 0."""
    inst = ctx.xml_instance
    if inst is None:
        return
    facts = inst.facts
    units = inst.units
    if facts is None or units is None:
        return

    type_map = _build_metric_type_map(ctx)
    # EBA-DEC-003 relies exclusively on the module-derived type_map:
    # there is no reliable unit-based heuristic for integer classification.
    # Without a module the rule is effectively a no-op, which matches the
    # original behaviour.

    for fact in facts:
        if fact.unit is None or fact.decimals is None:
            continue

        metric = fact.metric_qname or fact.metric or "?"
        qname = fact.metric_qname or fact.metric
        metric_type = type_map.get(qname) if qname is not None else None
        if metric_type != _TYPE_INTEGER:
            continue

        # Infinite precision is not 0
        if is_infinite_decimals(fact.decimals):
            ctx.add_finding(
                location=f"fact:{metric}:context:{fact.context}",
                context={
                    "detail": (
                        f"Fact '{metric}' has @decimals={fact.decimals} (infinite precision) "
                        f"but integer facts MUST use @decimals=0."
                    )
                },
            )
            continue

        dec = _parse_decimals(fact.decimals)
        if dec is not None and dec != 0:
            ctx.add_finding(
                location=f"fact:{metric}:context:{fact.context}",
                context={
                    "detail": (
                        f"Fact '{metric}' has @decimals={fact.decimals} "
                        f"but integer facts MUST use @decimals=0."
                    )
                },
            )


# ---------------------------------------------------------------------------
# EBA-DEC-004  Unrealistically high decimals
# ---------------------------------------------------------------------------


@rule_impl("EBA-DEC-004", format="xml")
def check_realistic_decimals_xml(ctx: ValidationContext) -> None:
    """Decimals SHOULD be a realistic indication of accuracy."""
    inst = ctx.xml_instance
    if inst is None:
        return
    facts = inst.facts
    if facts is None:
        return

    for fact in facts:
        if fact.decimals is None:
            continue

        metric = fact.metric_qname or fact.metric or "?"

        if is_infinite_decimals(fact.decimals):
            ctx.add_finding(
                location=f"fact:{metric}:context:{fact.context}",
                context={
                    "detail": (
                        f"Fact '{metric}' uses @decimals={fact.decimals} (infinite precision) "
                        f"which is not a realistic indication of accuracy."
                    )
                },
            )
            continue

        dec = _parse_decimals(fact.decimals)
        if dec is not None and dec > _MAX_REALISTIC_DECIMALS:
            ctx.add_finding(
                location=f"fact:{metric}:context:{fact.context}",
                context={
                    "detail": (
                        f"Fact '{metric}' has @decimals={fact.decimals} "
                        f"which exceeds {_MAX_REALISTIC_DECIMALS} and is not a "
                        f"realistic indication of accuracy."
                    )
                },
            )


# ---------------------------------------------------------------------------
# CSV implementations
# ---------------------------------------------------------------------------

_PARAMETERS_CSV = "reports/parameters.csv"

# Maps parameter name → human-readable label for error messages.
_PARAM_LABELS = {
    "decimalsMonetary": "monetary",
    "decimalsPercentage": "percentage",
    "decimalsInteger": "integer",
    "decimalsDecimal": "decimal",
}


@rule_impl("EBA-DEC-001", format="csv")
def check_monetary_decimals_csv(ctx: ValidationContext) -> None:
    """Monetary decimals parameter MUST be >= threshold."""
    params = _parse_parameters(ctx)
    if params is None:
        return
    raw = params.get("decimalsMonetary")
    if raw is None:
        return  # CSV-025 handles missing params.

    threshold = _monetary_threshold(ctx)
    dec = _parse_decimals(raw)
    if dec is not None and dec < threshold:
        ctx.add_finding(
            location=_PARAMETERS_CSV,
            context={
                "detail": (f"decimalsMonetary={raw} is below the minimum threshold of {threshold}.")
            },
        )


@rule_impl("EBA-DEC-002", format="csv")
def check_percentage_decimals_csv(ctx: ValidationContext) -> None:
    """Percentage decimals parameter MUST be >= 4."""
    params = _parse_parameters(ctx)
    if params is None:
        return
    raw = params.get("decimalsPercentage")
    if raw is None:
        return

    dec = _parse_decimals(raw)
    if dec is not None and dec < 4:
        ctx.add_finding(
            location=_PARAMETERS_CSV,
            context={
                "detail": (
                    f"decimalsPercentage={raw} is below the minimum of 4 for percentage facts."
                )
            },
        )


@rule_impl("EBA-DEC-003", format="csv")
def check_integer_decimals_csv(ctx: ValidationContext) -> None:
    """Integer decimals parameter MUST be 0."""
    params = _parse_parameters(ctx)
    if params is None:
        return
    raw = params.get("decimalsInteger")
    if raw is None:
        return

    if is_infinite_decimals(raw):
        ctx.add_finding(
            location=_PARAMETERS_CSV,
            context={
                "detail": (
                    f"decimalsInteger={raw} (infinite precision) "
                    f"but integer facts MUST use decimals=0."
                )
            },
        )
        return

    dec = _parse_decimals(raw)
    if dec is not None and dec != 0:
        ctx.add_finding(
            location=_PARAMETERS_CSV,
            context={"detail": (f"decimalsInteger={raw} but integer facts MUST use decimals=0.")},
        )


@rule_impl("EBA-DEC-004", format="csv")
def check_realistic_decimals_csv(ctx: ValidationContext) -> None:
    """Decimals parameters SHOULD be realistic."""
    params = _parse_parameters(ctx)
    if params is None:
        return

    for param_name, _label in _PARAM_LABELS.items():
        raw = params.get(param_name)
        if raw is None:
            continue

        if is_infinite_decimals(raw):
            ctx.add_finding(
                location=_PARAMETERS_CSV,
                context={
                    "detail": (
                        f"{param_name}={raw} (infinite precision) "
                        f"is not a realistic indication of accuracy."
                    )
                },
            )
            continue

        dec = _parse_decimals(raw)
        if dec is not None and dec > _MAX_REALISTIC_DECIMALS:
            ctx.add_finding(
                location=_PARAMETERS_CSV,
                context={
                    "detail": (
                        f"{param_name}={raw} exceeds {_MAX_REALISTIC_DECIMALS} "
                        f"and is not a realistic indication of accuracy."
                    )
                },
            )
