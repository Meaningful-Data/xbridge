"""CSV-001..CSV-005: Report package structure checks."""

from __future__ import annotations

import json
from typing import Optional, Set
from zipfile import BadZipFile, ZipFile

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl

_REPORT_PACKAGE_JSON = "META-INF/reportPackage.json"
_REPORT_JSON = "reports/report.json"
_EXPECTED_DOC_TYPE = "https://xbrl.org/report-package/2023"


def _open_zip(ctx: ValidationContext) -> Optional[ZipFile]:
    """Try to open the file as a ZIP.  Returns None for invalid ZIPs."""
    try:
        return ZipFile(ctx.file_path)
    except BadZipFile:
        return None


# ── CSV-001 ──────────────────────────────────────────────────────────


@rule_impl("CSV-001")
def check_valid_zip(ctx: ValidationContext) -> None:
    """The report package MUST be a valid ZIP archive."""
    try:
        with ZipFile(ctx.file_path):
            pass
    except BadZipFile as exc:
        ctx.add_finding(
            location=ctx.file_path.name,
            context={"detail": str(exc)},
        )


# ── CSV-002 ──────────────────────────────────────────────────────────


@rule_impl("CSV-002")
def check_report_package_json_exists(ctx: ValidationContext) -> None:
    """The ZIP MUST contain META-INF/reportPackage.json."""
    zf = _open_zip(ctx)
    if zf is None:
        return  # CSV-001 handles bad ZIPs
    with zf:
        if _REPORT_PACKAGE_JSON not in zf.namelist():
            ctx.add_finding(
                location=ctx.file_path.name,
                context={"detail": "META-INF/reportPackage.json not found in ZIP"},
            )


# ── CSV-003 ──────────────────────────────────────────────────────────


@rule_impl("CSV-003")
def check_report_package_document_type(ctx: ValidationContext) -> None:
    """reportPackage.json documentType MUST be the XBRL report-package URL."""
    zf = _open_zip(ctx)
    if zf is None:
        return
    with zf:
        if _REPORT_PACKAGE_JSON not in zf.namelist():
            return  # CSV-002 handles missing file

        raw = zf.read(_REPORT_PACKAGE_JSON)

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        ctx.add_finding(
            location=_REPORT_PACKAGE_JSON,
            context={"detail": f"invalid JSON: {exc}"},
        )
        return

    doc_type = data.get("documentType")
    if doc_type != _EXPECTED_DOC_TYPE:
        ctx.add_finding(
            location=_REPORT_PACKAGE_JSON,
            context={
                "detail": f"found {doc_type!r}, expected {_EXPECTED_DOC_TYPE!r}",
            },
        )


# ── CSV-004 ──────────────────────────────────────────────────────────


@rule_impl("CSV-004")
def check_report_json_exists(ctx: ValidationContext) -> None:
    """The ZIP MUST contain exactly one reports/report.json."""
    zf = _open_zip(ctx)
    if zf is None:
        return
    with zf:
        entries = zf.namelist()

    matches = [e for e in entries if e == _REPORT_JSON]
    if len(matches) == 0:
        ctx.add_finding(
            location=ctx.file_path.name,
            context={"detail": "reports/report.json not found in ZIP"},
        )
    elif len(matches) > 1:
        ctx.add_finding(
            location=ctx.file_path.name,
            context={
                "detail": f"found {len(matches)} reports/report.json entries",
            },
        )


# ── CSV-005 ──────────────────────────────────────────────────────────


def _declared_table_files(zf: ZipFile) -> Set[str]:
    """Read report.json and return the set of declared table file paths."""
    if _REPORT_JSON not in zf.namelist():
        return set()
    try:
        data = json.loads(zf.read(_REPORT_JSON))
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
        return set()
    tables = data.get("tables", {})
    if not isinstance(tables, dict):
        return set()
    paths: Set[str] = set()
    for table in tables.values():
        url = table.get("url") if isinstance(table, dict) else None
        if url:
            paths.add(f"reports/{url}")
    return paths


@rule_impl("CSV-005")
def check_no_extraneous_files(ctx: ValidationContext) -> None:
    """The ZIP MUST NOT contain files outside the report package structure."""
    zf = _open_zip(ctx)
    if zf is None:
        return
    with zf:
        entries = zf.namelist()
        table_files = _declared_table_files(zf)

    allowed: Set[str] = {
        _REPORT_PACKAGE_JSON,
        _REPORT_JSON,
        "reports/parameters.csv",
        "reports/FilingIndicators.csv",
    } | table_files

    for entry in entries:
        # Skip directory entries (trailing slash)
        if entry.endswith("/"):
            continue
        if entry not in allowed:
            ctx.add_finding(
                location=entry,
                context={"detail": f"extraneous file: {entry}"},
            )
