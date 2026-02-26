"""CSV-010..CSV-016: Metadata file (report.json) checks."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from zipfile import BadZipFile, ZipFile

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl

_REPORT_JSON = "reports/report.json"
_EXPECTED_CSV_DOC_TYPE = "https://xbrl.org/2021/xbrl-csv"
_INDEX_FILE = Path(__file__).parents[2] / "modules" / "index.json"

# Matches a prefixed name like "eba_dim:BAS" — prefix is the part before ':'
_PREFIX_RE = re.compile(r"^([A-Za-z_][\w.-]*):(.+)$")


# ── Shared helpers ───────────────────────────────────────────────────


def _read_report_json_raw(ctx: ValidationContext) -> Optional[bytes]:
    """Read reports/report.json bytes from the ZIP.  Returns None if unavailable."""
    try:
        with ZipFile(ctx.file_path) as zf:
            if _REPORT_JSON not in zf.namelist():
                return None
            return zf.read(_REPORT_JSON)
    except BadZipFile:
        return None


def _parse_report_json(ctx: ValidationContext) -> Optional[Dict[str, Any]]:
    """Parse reports/report.json.  Returns None if unavailable or invalid JSON."""
    raw = _read_report_json_raw(ctx)
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _load_known_entry_points() -> Set[str]:
    """Load the set of known entry point URLs from the module index."""
    if not _INDEX_FILE.exists():
        return set()
    with open(_INDEX_FILE, encoding="utf-8") as f:
        data: Dict[str, str] = json.load(f)
    return set(data.keys())


def _normalize_extends_url(url: str) -> str:
    """Normalize an extends URL to match the taxonomy index format.

    Mirrors the logic in CsvInstance.parse():
    - Replace .json suffix with .xsd
    - Ensure http:// prefix
    """
    result = url
    if result.endswith(".json"):
        result = result[:-5] + ".xsd"
    if not (result.startswith("http://") or result.startswith("https://")):
        result = "http://" + result.lstrip("/")
    return result


# ── CSV-010 ──────────────────────────────────────────────────────────


@rule_impl("CSV-010")
def check_report_json_valid(ctx: ValidationContext) -> None:
    """report.json MUST be valid JSON."""
    raw = _read_report_json_raw(ctx)
    if raw is None:
        return  # CSV-004 handles missing report.json

    try:
        json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        ctx.add_finding(
            location=_REPORT_JSON,
            context={"detail": str(exc)},
        )


# ── CSV-011 ──────────────────────────────────────────────────────────


@rule_impl("CSV-011")
def check_document_type(ctx: ValidationContext) -> None:
    """documentInfo.documentType MUST be the xBRL-CSV URL."""
    data = _parse_report_json(ctx)
    if data is None:
        return  # CSV-010 handles invalid JSON

    doc_info = data.get("documentInfo")
    if not isinstance(doc_info, dict):
        ctx.add_finding(
            location=_REPORT_JSON,
            context={"detail": "documentInfo is missing or not an object"},
        )
        return

    doc_type = doc_info.get("documentType")
    if doc_type != _EXPECTED_CSV_DOC_TYPE:
        ctx.add_finding(
            location=_REPORT_JSON,
            context={
                "detail": f"found {doc_type!r}, expected {_EXPECTED_CSV_DOC_TYPE!r}",
            },
        )


# ── CSV-012 ──────────────────────────────────────────────────────────


@rule_impl("CSV-012")
def check_extends_single_entry(ctx: ValidationContext) -> None:
    """documentInfo.extends MUST contain exactly one entry point URL."""
    data = _parse_report_json(ctx)
    if data is None:
        return

    doc_info = data.get("documentInfo")
    if not isinstance(doc_info, dict):
        return  # CSV-011 handles

    extends = doc_info.get("extends")
    if not isinstance(extends, list):
        ctx.add_finding(
            location=_REPORT_JSON,
            context={"detail": f"extends is {type(extends).__name__}, expected a list"},
        )
        return

    if len(extends) != 1:
        ctx.add_finding(
            location=_REPORT_JSON,
            context={"detail": f"extends contains {len(extends)} entries, expected exactly 1"},
        )


# ── CSV-013 ──────────────────────────────────────────────────────────


@rule_impl("CSV-013")
def check_extends_known_entry_point(ctx: ValidationContext) -> None:
    """The extends URL MUST resolve to a published entry point."""
    data = _parse_report_json(ctx)
    if data is None:
        return

    doc_info = data.get("documentInfo")
    if not isinstance(doc_info, dict):
        return

    extends = doc_info.get("extends")
    if not isinstance(extends, list) or len(extends) != 1:
        return  # CSV-012 handles

    url = extends[0]
    if not isinstance(url, str):
        ctx.add_finding(
            location=_REPORT_JSON,
            context={"detail": f"extends entry is {type(url).__name__}, expected a string"},
        )
        return

    normalized = _normalize_extends_url(url)
    known = _load_known_entry_points()
    if normalized not in known:
        ctx.add_finding(
            location=_REPORT_JSON,
            context={"detail": f"'{url}' is not a known entry point URL"},
        )


# ── CSV-014 ──────────────────────────────────────────────────────────


def _find_duplicate_keys(raw: bytes) -> List[Tuple[str, str]]:
    """Scan JSON bytes for duplicate keys.  Returns list of (path, key) tuples."""
    duplicates: List[Tuple[str, str]] = []
    path_stack: List[str] = []

    def pairs_hook(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
        seen: Set[str] = set()
        current_path = ".".join(path_stack) if path_stack else "<root>"
        for key, _value in pairs:
            if key in seen:
                duplicates.append((current_path, key))
            seen.add(key)
        return dict(pairs)

    # We need to track nesting. The pairs_hook is called bottom-up,
    # so we cannot easily track path with it alone.  A simpler approach:
    # just detect duplicates at any level and report the key name.
    json.loads(raw, object_pairs_hook=pairs_hook)
    return duplicates


@rule_impl("CSV-014")
def check_json_constraints(ctx: ValidationContext) -> None:
    """JSON representation constraints: no duplicate keys, correct types."""
    raw = _read_report_json_raw(ctx)
    if raw is None:
        return

    # Check for duplicate keys
    try:
        duplicates = _find_duplicate_keys(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return  # CSV-010 handles

    for _path, key in duplicates:
        ctx.add_finding(
            location=_REPORT_JSON,
            context={"detail": f"duplicate key: {key!r}"},
        )

    # Check structural types
    data = _parse_report_json(ctx)
    if data is None:
        return

    doc_info = data.get("documentInfo")
    if doc_info is not None and not isinstance(doc_info, dict):
        ctx.add_finding(
            location=_REPORT_JSON,
            context={"detail": "documentInfo must be an object"},
        )

    if isinstance(doc_info, dict):
        ns = doc_info.get("namespaces")
        if ns is not None and not isinstance(ns, dict):
            ctx.add_finding(
                location=_REPORT_JSON,
                context={"detail": "documentInfo.namespaces must be an object"},
            )
        extends = doc_info.get("extends")
        if extends is not None and not isinstance(extends, list):
            ctx.add_finding(
                location=_REPORT_JSON,
                context={"detail": "documentInfo.extends must be an array"},
            )

    tables = data.get("tables")
    if tables is not None and not isinstance(tables, dict):
        ctx.add_finding(
            location=_REPORT_JSON,
            context={"detail": "tables must be an object"},
        )


# ── CSV-015 ──────────────────────────────────────────────────────────


def _collect_prefixes_from_value(value: str) -> Set[str]:
    """Extract namespace prefixes from a colon-separated value."""
    m = _PREFIX_RE.match(value)
    if m:
        return {m.group(1)}
    return set()


def _collect_prefixes_in_tables(tables: Dict[str, Any]) -> Set[str]:
    """Scan table definitions for prefixed names in column definitions."""
    prefixes: Set[str] = set()
    for table in tables.values():
        if not isinstance(table, dict):
            continue
        columns = table.get("columns", {})
        if not isinstance(columns, dict):
            continue
        for col_name, col_def in columns.items():
            # Column name itself may be prefixed
            prefixes |= _collect_prefixes_from_value(col_name)
            if isinstance(col_def, dict):
                # Dimension values may contain prefixes
                dims = col_def.get("dimensions", {})
                if isinstance(dims, dict):
                    for dim_key, dim_val in dims.items():
                        prefixes |= _collect_prefixes_from_value(dim_key)
                        if isinstance(dim_val, str):
                            prefixes |= _collect_prefixes_from_value(dim_val)
                # propertyGroups may reference prefixed names
                prop_groups = col_def.get("propertyGroups", {})
                if isinstance(prop_groups, dict):
                    for pg_val in prop_groups.values():
                        if isinstance(pg_val, str):
                            prefixes |= _collect_prefixes_from_value(pg_val)

    return prefixes


def _collect_prefixes_in_template_columns(
    templates: Dict[str, Any],
) -> Set[str]:
    """Scan tableTemplates for prefixed names."""
    prefixes: Set[str] = set()
    for tmpl in templates.values():
        if not isinstance(tmpl, dict):
            continue
        columns = tmpl.get("columns", {})
        if not isinstance(columns, dict):
            continue
        for col_name, col_def in columns.items():
            prefixes |= _collect_prefixes_from_value(col_name)
            if isinstance(col_def, dict):
                dims = col_def.get("dimensions", {})
                if isinstance(dims, dict):
                    for dim_key, dim_val in dims.items():
                        prefixes |= _collect_prefixes_from_value(dim_key)
                        if isinstance(dim_val, str):
                            prefixes |= _collect_prefixes_from_value(dim_val)
    return prefixes


@rule_impl("CSV-015")
def check_namespace_prefixes_declared(ctx: ValidationContext) -> None:
    """All namespace prefixes used MUST be declared in documentInfo.namespaces."""
    data = _parse_report_json(ctx)
    if data is None:
        return

    doc_info = data.get("documentInfo")
    if not isinstance(doc_info, dict):
        return

    namespaces = doc_info.get("namespaces", {})
    if not isinstance(namespaces, dict):
        return  # CSV-014 handles type errors

    declared: Set[str] = set(namespaces.keys())

    # Collect prefixes used in tables and tableTemplates
    used: Set[str] = set()
    tables = data.get("tables", {})
    if isinstance(tables, dict):
        used |= _collect_prefixes_in_tables(tables)

    templates = data.get("tableTemplates", {})
    if isinstance(templates, dict):
        used |= _collect_prefixes_in_template_columns(templates)

    undeclared = used - declared
    for prefix in sorted(undeclared):
        ctx.add_finding(
            location=_REPORT_JSON,
            context={"detail": f"undeclared namespace prefix: {prefix!r}"},
        )


# ── CSV-016 ──────────────────────────────────────────────────────────


def _is_absolute_uri(uri: str) -> bool:
    """Check whether a URI is absolute (has a scheme)."""
    return uri.startswith("http://") or uri.startswith("https://")


@rule_impl("CSV-016")
def check_uri_aliases(ctx: ValidationContext) -> None:
    """All URI aliases MUST resolve to valid absolute URIs."""
    data = _parse_report_json(ctx)
    if data is None:
        return

    doc_info = data.get("documentInfo")
    if not isinstance(doc_info, dict):
        return

    namespaces = doc_info.get("namespaces", {})
    if isinstance(namespaces, dict):
        for prefix, uri in namespaces.items():
            if isinstance(uri, str) and not _is_absolute_uri(uri):
                ctx.add_finding(
                    location=_REPORT_JSON,
                    context={
                        "detail": f"namespace {prefix!r} maps to non-absolute URI: {uri!r}",
                    },
                )

    extends = doc_info.get("extends", [])
    if isinstance(extends, list):
        for entry in extends:
            if isinstance(entry, str) and not _is_absolute_uri(entry):
                ctx.add_finding(
                    location=_REPORT_JSON,
                    context={
                        "detail": f"extends entry is not an absolute URI: {entry!r}",
                    },
                )
