"""EBA-GUIDE-001..EBA-GUIDE-007: Guidance checks.

EBA-GUIDE-002, EBA-GUIDE-004 and EBA-GUIDE-007 are shared rules with
both XML and CSV implementations.  The remaining rules (001, 003, 005,
006) are XML-only.

EBA-GUIDE-001, 005, and 006 all need a full tree traversal.  A
**single-pass** scan collects data for all three rules and caches
the result per root.
"""

from __future__ import annotations

import csv
from typing import Any, Dict, List, Optional, Set, Tuple

from lxml import etree

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl
from xbridge.validation.rules._helpers import fact_label, is_fact
from xbridge.validation.rules.csv_data_tables import (
    _basename,
    _decode_utf8,
    _find_table_for_file,
    _iter_data_tables,
    _parse_header,
)
from xbridge.validation.rules.csv_metadata import _parse_report_json

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Well-known namespace URI → canonical prefix mapping.
_CANONICAL_PREFIXES: Dict[str, str] = {
    "http://www.xbrl.org/2003/instance": "xbrli",
    "http://www.xbrl.org/2003/linkbase": "link",
    "http://www.w3.org/1999/xlink": "xlink",
    "http://www.xbrl.org/2003/iso4217": "iso4217",
    "http://xbrl.org/2006/xbrldi": "xbrldi",
    "http://xbrl.org/2005/xbrldt": "xbrldt",
    "http://www.eurofiling.info/xbrl/ext/filing-indicators": "find",
    "http://www.w3.org/2001/XMLSchema-instance": "xsi",
    "http://www.w3.org/2001/XMLSchema": "xsd",
}

# Threshold for "excessive" string length (EBA-GUIDE-004).
_EXCESSIVE_STRING_LENGTH = 10_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _canonical_prefix_for_uri(uri: str) -> Optional[str]:
    """Return the canonical prefix for a namespace URI, or None if unknown."""
    static = _CANONICAL_PREFIXES.get(uri)
    if static is not None:
        return static

    # EBA convention: .../xbrl/.../dict/{segment} → eba_{segment}
    if "eba.europa.eu" in uri:
        cleaned = uri.rstrip("#/")
        if "/" in cleaned:
            segment = cleaned.rsplit("/", 1)[-1]
            if segment:
                return f"eba_{segment}"

    return None


# ---------------------------------------------------------------------------
# Single-pass namespace scan for GUIDE-001, 005, 006
# ---------------------------------------------------------------------------
class _NsScanResult:
    """Data collected in one pass over every element for namespace checks."""

    __slots__ = ("used_uris", "local_decl_elements", "uri_to_prefixes")

    def __init__(self) -> None:
        # GUIDE-001: namespace URIs actually used in tags/attrs/QName values
        self.used_uris: Set[str] = set()
        # GUIDE-005: (tag_label, sorted_prefix_list_str) for non-root local decls
        self.local_decl_elements: List[Tuple[str, str]] = []
        # GUIDE-006: URI → set of prefixes declared anywhere
        self.uri_to_prefixes: Dict[str, Set[str]] = {}


# Single-entry cache keyed by root object reference.
_last_ns_scan: Optional[Tuple[etree._Element, _NsScanResult]] = None


def _ns_scan(root: etree._Element) -> _NsScanResult:
    """Single-pass scan collecting namespace data for GUIDE-001/005/006; cached per *root*."""
    global _last_ns_scan  # noqa: PLW0603
    if _last_ns_scan is not None and _last_ns_scan[0] is root:
        return _last_ns_scan[1]

    r = _NsScanResult()

    # Seed uri_to_prefixes with root-level declarations.
    for prefix, uri in root.nsmap.items():
        if prefix is not None:
            r.uri_to_prefixes.setdefault(uri, set()).add(prefix)

    for elem in root.iter():
        tag = elem.tag
        if not isinstance(tag, str):
            continue

        # --- Collect used URIs (GUIDE-001) ---
        # From element tag.
        if tag.startswith("{"):
            r.used_uris.add(tag[1 : tag.index("}")])

        # From attribute names.
        for attr_name in elem.attrib:
            if isinstance(attr_name, str) and attr_name.startswith("{"):
                r.used_uris.add(attr_name[1 : attr_name.index("}")])

        # From QName references in attribute values and text content.
        nsmap = elem.nsmap
        texts: list[str] = [str(v) for v in elem.attrib.values()]
        if elem.text:
            texts.append(elem.text)
        for val in texts:
            if ":" in val:
                prefix = val.split(":")[0]
                resolved = nsmap.get(prefix)
                if resolved is not None:
                    r.used_uris.add(resolved)

        # --- Check for local namespace declarations (GUIDE-005 / GUIDE-006) ---
        parent = elem.getparent()
        if parent is None:
            continue  # Root element — skip
        parent_nsmap = parent.nsmap
        local_prefixes: list[str] = []
        for ns_prefix, uri in nsmap.items():
            if parent_nsmap.get(ns_prefix) != uri:
                # GUIDE-006: record this prefix→uri binding
                if ns_prefix is not None:
                    r.uri_to_prefixes.setdefault(uri, set()).add(ns_prefix)
                local_prefixes.append(ns_prefix or "(default)")
        if local_prefixes:
            tag_label = etree.QName(tag).localname if tag.startswith("{") else tag
            r.local_decl_elements.append((tag_label, ", ".join(sorted(local_prefixes))))

    _last_ns_scan = (root, r)
    return r


# ---------------------------------------------------------------------------
# EBA-GUIDE-001: Unused namespace prefixes
# ---------------------------------------------------------------------------


@rule_impl("EBA-GUIDE-001")
def check_unused_namespace_prefixes(ctx: ValidationContext) -> None:
    """Flag namespace prefixes declared on the root that are never used."""
    root = ctx.xml_root
    if root is None:
        return

    scan = _ns_scan(root)
    declared = root.nsmap

    unused = []
    for prefix, uri in declared.items():
        if prefix is None:
            continue  # Default namespace — skip
        if prefix in ("xml", "xsi"):
            continue  # Standard XML namespaces — always implicitly available
        if uri not in scan.used_uris:
            unused.append(prefix)

    if unused:
        unused.sort()
        ctx.add_finding(
            location="root",
            context={"detail": f"unused prefixes: {', '.join(unused)}"},
        )


# ---------------------------------------------------------------------------
# EBA-GUIDE-002: Canonical namespace prefixes
# ---------------------------------------------------------------------------


@rule_impl("EBA-GUIDE-002", format="xml")
def check_canonical_prefixes(ctx: ValidationContext) -> None:
    """Flag prefixes that don't match canonical conventions."""
    root = ctx.xml_root
    if root is None:
        return

    mismatches = []
    for prefix, uri in root.nsmap.items():
        if prefix is None:
            continue
        canonical = _canonical_prefix_for_uri(uri)
        if canonical is not None and prefix != canonical:
            mismatches.append(f"{prefix} (expected {canonical})")

    if mismatches:
        mismatches.sort()
        ctx.add_finding(
            location="root",
            context={"detail": f"non-canonical prefixes: {', '.join(mismatches)}"},
        )


# ---------------------------------------------------------------------------
# EBA-GUIDE-003: Unused @id on facts
# ---------------------------------------------------------------------------


@rule_impl("EBA-GUIDE-003")
def check_unused_fact_ids(ctx: ValidationContext) -> None:
    """Flag fact elements that have an @id attribute."""
    root = ctx.xml_root
    if root is None:
        return

    flagged = []
    for child in root:
        if not is_fact(child):
            continue
        fact_id = child.get("id")
        if fact_id is not None:
            flagged.append(f"{fact_label(child)} id={fact_id}")

    if flagged:
        n = len(flagged)
        examples = ", ".join(flagged[:5])
        detail = f"{n} fact(s) with @id: {examples}"
        if n > 5:
            detail += f" (and {n - 5} more)"
        ctx.add_finding(location="facts", context={"detail": detail})


# ---------------------------------------------------------------------------
# EBA-GUIDE-004: Excessive string length
# ---------------------------------------------------------------------------


@rule_impl("EBA-GUIDE-004", format="xml")
def check_excessive_string_length(ctx: ValidationContext) -> None:
    """Flag string facts whose values exceed the length threshold."""
    inst = ctx.xml_instance
    if inst is None or inst.facts is None:
        return

    for fact in inst.facts:
        if fact.unit is not None:
            continue  # Numeric fact
        if fact.value is None:
            continue
        length = len(fact.value)
        if length > _EXCESSIVE_STRING_LENGTH:
            label = fact_label(fact.fact_xml)
            ctx.add_finding(
                location=f"fact:{label}",
                context={
                    "detail": (
                        f"string value is {length:,} characters "
                        f"(threshold: {_EXCESSIVE_STRING_LENGTH:,})"
                    )
                },
            )


# ---------------------------------------------------------------------------
# EBA-GUIDE-005: Namespace declarations on non-root elements
# ---------------------------------------------------------------------------


@rule_impl("EBA-GUIDE-005")
def check_namespace_declarations_on_root(ctx: ValidationContext) -> None:
    """Flag elements that introduce namespace declarations below the root."""
    root = ctx.xml_root
    if root is None:
        return

    scan = _ns_scan(root)
    offending = scan.local_decl_elements

    if offending:
        n = len(offending)
        examples = "; ".join(f"{tag} declares {pfx}" for tag, pfx in offending[:5])
        detail = f"{n} element(s) with local namespace declarations: {examples}"
        if n > 5:
            detail += f" (and {n - 5} more)"
        ctx.add_finding(location="document", context={"detail": detail})


# ---------------------------------------------------------------------------
# EBA-GUIDE-006: Multiple prefixes for the same namespace
# ---------------------------------------------------------------------------


@rule_impl("EBA-GUIDE-006")
def check_multiple_prefixes_same_namespace(ctx: ValidationContext) -> None:
    """Flag namespaces that are bound to more than one prefix."""
    root = ctx.xml_root
    if root is None:
        return

    scan = _ns_scan(root)

    duplicates = []
    for uri, prefixes in sorted(scan.uri_to_prefixes.items()):
        if len(prefixes) > 1:
            sorted_pfx = ", ".join(sorted(prefixes))
            duplicates.append(f"{sorted_pfx} \u2192 {uri}")

    if duplicates:
        ctx.add_finding(
            location="document",
            context={"detail": (f"multiple prefixes for same namespace: {'; '.join(duplicates)}")},
        )


# ---------------------------------------------------------------------------
# EBA-GUIDE-007: Leading/trailing whitespace
# ---------------------------------------------------------------------------


@rule_impl("EBA-GUIDE-007", format="xml")
def check_leading_trailing_whitespace(ctx: ValidationContext) -> None:
    """Flag string facts and dimension values with leading/trailing whitespace."""
    inst = ctx.xml_instance
    if inst is None:
        return

    issues: list[str] = []

    # Check string facts.
    if inst.facts:
        for fact in inst.facts:
            if fact.unit is not None:
                continue  # Numeric
            val = fact.value
            if val is None:
                continue
            if val != val.strip():
                label = fact_label(fact.fact_xml)
                issues.append(f"fact {label}")

    # Check dimension values in contexts.
    if inst.contexts:
        for ctx_id, context in inst.contexts.items():
            if context.scenario is None:
                continue
            for dim_key, dim_val in context.scenario.dimensions.items():
                if dim_val != dim_val.strip():
                    issues.append(f"context {ctx_id} dimension {dim_key}")

    if issues:
        n = len(issues)
        examples = "; ".join(issues[:5])
        detail = f"{n} value(s) with leading/trailing whitespace: {examples}"
        if n > 5:
            detail += f" (and {n - 5} more)"
        ctx.add_finding(location="document", context={"detail": detail})


# ===========================================================================
# CSV implementations
# ===========================================================================

_STANDARD_COLS = frozenset({"datapoint", "factValue", "unit"})


def _build_variable_lookup(ctx: ValidationContext) -> Dict[str, Any]:
    """Build a ``{variable_code: Variable}`` lookup from the Module."""
    module = ctx.module
    if module is None:
        return {}
    result: Dict[str, Any] = {}
    for table in module.tables:
        for variable in table.variables:
            if variable.code:
                result[variable.code] = variable
    return result


# ---------------------------------------------------------------------------
# EBA-GUIDE-002 CSV: Canonical namespace prefixes
# ---------------------------------------------------------------------------


@rule_impl("EBA-GUIDE-002", format="csv")
def check_canonical_prefixes_csv(ctx: ValidationContext) -> None:
    """Flag non-canonical namespace prefixes in report.json."""
    data = _parse_report_json(ctx)
    if data is None:
        return

    doc_info = data.get("documentInfo")
    if not isinstance(doc_info, dict):
        return
    namespaces = doc_info.get("namespaces")
    if not isinstance(namespaces, dict):
        return

    mismatches = []
    for prefix, uri in namespaces.items():
        if not isinstance(prefix, str) or not isinstance(uri, str):
            continue
        canonical = _canonical_prefix_for_uri(uri)
        if canonical is not None and prefix != canonical:
            mismatches.append(f"{prefix} (expected {canonical})")

    if mismatches:
        mismatches.sort()
        ctx.add_finding(
            location="reports/report.json",
            context={"detail": f"non-canonical prefixes: {', '.join(mismatches)}"},
        )


# ---------------------------------------------------------------------------
# EBA-GUIDE-004 CSV: Excessive string length
# ---------------------------------------------------------------------------


@rule_impl("EBA-GUIDE-004", format="csv")
def check_excessive_string_length_csv(ctx: ValidationContext) -> None:
    """Flag string fact values in CSV data tables that exceed the length threshold."""
    module = ctx.module
    if module is None:
        return

    var_lookup = _build_variable_lookup(ctx)
    if not var_lookup:
        return

    for entry, raw in _iter_data_tables(ctx):
        text = _decode_utf8(raw)
        if text is None:
            continue
        header = _parse_header(text)
        if header is None:
            continue

        name = _basename(entry)
        table = _find_table_for_file(ctx, name)
        if table is None or table.architecture != "datapoints":
            continue

        dp_idx: Optional[int] = None
        fv_idx: Optional[int] = None
        for i, h in enumerate(header):
            if h == "datapoint":
                dp_idx = i
            elif h == "factValue":
                fv_idx = i

        if dp_idx is None or fv_idx is None:
            continue

        lines = text.splitlines()
        reader = csv.reader(lines[1:])
        for row_num, row in enumerate(reader, start=2):
            if not any(row):
                continue
            if dp_idx >= len(row) or fv_idx >= len(row):
                continue

            dp_code = row[dp_idx]
            variable = var_lookup.get(dp_code)
            if variable is None:
                continue
            if variable.dimensions.get("unit"):
                continue  # numeric fact

            value = row[fv_idx]
            length = len(value)
            if length > _EXCESSIVE_STRING_LENGTH:
                ctx.add_finding(
                    location=entry,
                    context={
                        "detail": (
                            f"{name} row {row_num}: string value is "
                            f"{length:,} characters "
                            f"(threshold: {_EXCESSIVE_STRING_LENGTH:,})"
                        )
                    },
                )


# ---------------------------------------------------------------------------
# EBA-GUIDE-007 CSV: Leading/trailing whitespace
# ---------------------------------------------------------------------------


def _collect_whitespace_issues(
    ctx: ValidationContext,
    var_lookup: Dict[str, Any],
) -> List[str]:
    """Scan CSV data tables for values with leading/trailing whitespace."""
    issues: List[str] = []

    for entry, raw in _iter_data_tables(ctx):
        text = _decode_utf8(raw)
        if text is None:
            continue
        header = _parse_header(text)
        if header is None:
            continue

        name = _basename(entry)
        table = _find_table_for_file(ctx, name)
        if table is None or table.architecture != "datapoints":
            continue

        dp_idx: Optional[int] = None
        fv_idx: Optional[int] = None
        dim_col_indices: List[Tuple[int, str]] = []
        for i, h in enumerate(header):
            if h == "datapoint":
                dp_idx = i
            elif h == "factValue":
                fv_idx = i
            elif h not in _STANDARD_COLS:
                dim_col_indices.append((i, h))

        if dp_idx is None:
            continue

        lines = text.splitlines()
        reader = csv.reader(lines[1:])
        for row_num, row in enumerate(reader, start=2):
            if not any(row):
                continue
            if dp_idx >= len(row):
                continue

            dp_code = row[dp_idx]
            variable = var_lookup.get(dp_code)

            # Check string fact values.
            is_string = (
                fv_idx is not None
                and fv_idx < len(row)
                and variable is not None
                and not variable.dimensions.get("unit")
            )
            if is_string:
                val = row[fv_idx]  # type: ignore[index]
                if val and val != val.strip():
                    issues.append(f"{name} row {row_num} factValue")

            # Check dimension column values.
            for col_idx, col_name in dim_col_indices:
                if col_idx < len(row):
                    val = row[col_idx]
                    if val and val != val.strip():
                        issues.append(f"{name} row {row_num} {col_name}")

    return issues


@rule_impl("EBA-GUIDE-007", format="csv")
def check_leading_trailing_whitespace_csv(ctx: ValidationContext) -> None:
    """Flag string fact values and dimension values with leading/trailing whitespace."""
    module = ctx.module
    if module is None:
        return

    var_lookup = _build_variable_lookup(ctx)
    if not var_lookup:
        return

    issues = _collect_whitespace_issues(ctx, var_lookup)

    if issues:
        n = len(issues)
        examples = "; ".join(issues[:5])
        detail = f"{n} value(s) with leading/trailing whitespace: {examples}"
        if n > 5:
            detail += f" (and {n - 5} more)"
        ctx.add_finding(location="document", context={"detail": detail})
