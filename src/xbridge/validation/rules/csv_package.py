"""CSV-001..CSV-005: Report package structure checks."""

from __future__ import annotations

from zipfile import BadZipFile, ZipFile

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl


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
