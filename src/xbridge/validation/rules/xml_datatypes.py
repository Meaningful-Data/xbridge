"""XML-073..XML-074: Fact values against the data type of their concept.

XML-073: Fact values MUST be valid for the item type of their concept
         (monetary, decimal, percent, integer, boolean, date, QName, ...).
XML-074: Enumeration fact values MUST be allowed values for their concept.

Item types come from the bundled ``metric_types.json`` (see
:mod:`xbridge.validation.rules._datatypes`).  Allowed enumeration values come
from the Module.  A fact cannot be matched to a single datapoint without its
full context, so XML-074 accepts any value allowed for the concept in some
datapoint of the module, and skips concepts that have a datapoint without a
list of allowed values.

The XML is scanned **once** for both rules; the result is kept in
``ctx.shared_cache``.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from lxml import etree

from xbridge.instance import _normalize_metric_value
from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl
from xbridge.validation.rules._datatypes import (
    ENUMERATION_TYPE,
    invalid_value_reason,
    load_metric_types,
    normalize_enumeration_value,
    split_qname,
)
from xbridge.validation.rules._helpers import is_fact

_XSI_NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"
_CACHE_KEY = "xml_datatype_scan"

# (concept, context id, reported value, explanation)
_Finding = Tuple[str, str, str, str]


class _ScanResult:
    """Findings collected in one pass over the facts."""

    __slots__ = ("invalid_values", "disallowed_values")

    def __init__(self) -> None:
        self.invalid_values: List[_Finding] = []
        self.disallowed_values: List[_Finding] = []


def _allowed_values_by_concept(ctx: ValidationContext) -> Dict[str, Optional[FrozenSet[str]]]:
    """Return ``{concept: allowed values}`` from the Module.

    The value is ``None`` when some datapoint of the concept has no list of
    allowed values, meaning the concept cannot be checked.
    """
    module = ctx.module
    if module is None:
        return {}
    allowed: Dict[str, Optional[Set[str]]] = {}
    for table in module.tables:
        for variable in table.variables:
            concept = variable.dimensions.get("concept")
            if concept is None:
                continue
            values = variable._allowed_values
            if not values:
                allowed[concept] = None
            elif concept not in allowed:
                allowed[concept] = set(values)
            else:
                existing = allowed[concept]
                if existing is not None:
                    existing.update(values)
        if table.architecture == "headers":
            # Headers-architecture columns carry no allowed values.
            for col in table.columns or []:
                dims = col.get("dimensions")
                if isinstance(dims, dict) and dims.get("concept"):
                    allowed[dims["concept"]] = None
    return {k: frozenset(v) if v is not None else None for k, v in allowed.items()}


def _scan(ctx: ValidationContext, root: etree._Element) -> _ScanResult:
    cached = ctx.shared_cache.get(_CACHE_KEY)
    if cached is not None and cached[0] is root:
        result: _ScanResult = cached[1]
        return result

    result = _ScanResult()
    metric_types = load_metric_types()
    allowed_by_concept = _allowed_values_by_concept(ctx)

    for fact in root:
        if not is_fact(fact) or fact.get(_XSI_NIL) in ("true", "1"):
            continue
        concept = _normalize_metric_value(str(fact.tag), fact.nsmap)
        item_type = metric_types.get(concept) if concept else None
        if concept is None or item_type is None:
            continue

        raw = fact.text or ""
        context_id = fact.get("contextRef", "?")
        expected = invalid_value_reason(item_type, raw)
        if expected is not None:
            result.invalid_values.append(
                (concept, context_id, raw, f"is not {expected} as required by {item_type}")
            )
            continue
        if item_type != ENUMERATION_TYPE:
            continue

        qname = split_qname(raw)
        if qname is None:
            continue
        prefix, localname = qname
        namespace = fact.nsmap.get(prefix)
        if namespace is None:
            result.invalid_values.append(
                (concept, context_id, raw, f"uses the undeclared namespace prefix '{prefix}'")
            )
            continue
        allowed = allowed_by_concept.get(concept)
        value = normalize_enumeration_value(namespace, localname)
        if allowed and value not in allowed:
            result.disallowed_values.append(
                (concept, context_id, raw, "is not an allowed value for this concept")
            )

    ctx.shared_cache[_CACHE_KEY] = (root, result)
    return result


def _report(ctx: ValidationContext, findings: List[_Finding]) -> None:
    for concept, context_id, raw, explanation in findings:
        ctx.add_finding(
            location=f"fact:{concept}:context:{context_id}",
            context={
                "detail": (
                    f"Fact '{concept}' in context '{context_id}' has value {raw!r}, "
                    f"which {explanation}."
                )
            },
        )


# ---------------------------------------------------------------------------
# XML-073  Fact values valid for the concept's item type
# ---------------------------------------------------------------------------


@rule_impl("XML-073")
def check_fact_value_types(ctx: ValidationContext) -> None:
    """Fact values MUST be valid for the data type of their concept."""
    root = ctx.xml_root
    if root is None:
        return
    _report(ctx, _scan(ctx, root).invalid_values)


# ---------------------------------------------------------------------------
# XML-074  Enumeration values allowed for the concept
# ---------------------------------------------------------------------------


@rule_impl("XML-074")
def check_enumeration_values(ctx: ValidationContext) -> None:
    """Enumeration fact values MUST be allowed values for their concept."""
    root = ctx.xml_root
    if root is None or ctx.module is None:
        return
    _report(ctx, _scan(ctx, root).disallowed_values)
