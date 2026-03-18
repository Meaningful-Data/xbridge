"""Validation context passed to rule implementation functions."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from zipfile import BadZipFile, ZipFile

from lxml import etree

from xbridge.validation._models import RuleDefinition, ValidationResult

if TYPE_CHECKING:
    from xbridge.instance import CsvInstance, XmlInstance
    from xbridge.modules import Module


class _DefaultFormatDict(dict):  # type: ignore[type-arg]
    """A dict subclass that returns '{key}' for missing keys.

    Used with str.format_map() to render message templates gracefully
    when context does not contain all placeholder keys.
    """

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class ValidationContext:
    """Carries all data a rule implementation needs and collects findings.

    Passed to every rule function. Provides read-only access to the
    input data and the `add_finding()` method to report validation results.
    """

    def __init__(
        self,
        rule_set: str,
        rule_definition: RuleDefinition,
        file_path: Path,
        raw_bytes: bytes,
        xml_instance: Optional[XmlInstance] = None,
        csv_instance: Optional[CsvInstance] = None,
        module: Optional[Module] = None,
        xml_root: Optional[etree._Element] = None,
        zip_path: Optional[Path] = None,
        shared_cache: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.rule_set = rule_set
        self.rule_definition = rule_definition
        self.file_path = file_path
        self.raw_bytes = raw_bytes
        self.xml_instance = xml_instance
        self.csv_instance = csv_instance
        self.module = module
        self.xml_root = xml_root
        self.zip_path = zip_path
        self.shared_cache: Dict[str, Any] = shared_cache if shared_cache is not None else {}
        self._findings: List[ValidationResult] = []

    @property
    def findings(self) -> List[ValidationResult]:
        """The accumulated validation findings."""
        return self._findings

    @property
    def zip_root_prefix(self) -> str:
        """Root folder prefix inside the ZIP (e.g. ``'FolderName/'``).

        EBA submission ZIPs always nest contents under a single root folder
        whose name matches the ZIP file stem.  This property detects that
        prefix so rule implementations can resolve logical paths like
        ``reports/report.json`` to their actual ZIP entry names.

        Returns an empty string for flat ZIPs (no root folder).
        """
        cached = self.shared_cache.get("zip_root_prefix")
        if cached is not None:
            return cached
        result = self._detect_root_prefix()
        self.shared_cache["zip_root_prefix"] = result
        return result

    def _detect_root_prefix(self) -> str:
        zip_to_check = self.zip_path or (
            self.file_path if self.file_path.suffix.lower() == ".zip" else None
        )
        if zip_to_check is None:
            return ""
        try:
            with ZipFile(zip_to_check) as zf:
                entries = zf.namelist()
        except (BadZipFile, FileNotFoundError):
            return ""
        if not entries:
            return ""
        first_components: set[str] = set()
        for entry in entries:
            parts = entry.split("/")
            if len(parts) <= 1:
                return ""  # File at root level — no common prefix
            first_components.add(parts[0])
        if len(first_components) == 1:
            return first_components.pop() + "/"
        return ""

    def resolve_zip_entry(self, logical_path: str) -> str:
        """Prepend the ZIP root folder prefix to a logical path.

        For flat ZIPs this is a no-op; for rooted ZIPs it prepends the
        root folder name (e.g. ``'FolderName/reports/report.json'``).
        """
        return self.zip_root_prefix + logical_path

    def add_finding(
        self,
        location: str,
        context: Optional[Dict[str, Any]] = None,
        rule_code: Optional[str] = None,
    ) -> None:
        """Report a validation finding.

        The message template from the rule definition is rendered with
        placeholders filled from the context dict.

        Args:
            location: XPath or file:row:col locator.
            context: Optional key-value bag for template placeholders
                     and diagnostic data.
            rule_code: Override code (for rules that emit findings
                       for sub-rules). Defaults to the current
                       rule_definition.code.
        """
        code = rule_code if rule_code is not None else self.rule_definition.code
        template = self.rule_definition.effective_message(self.rule_set)
        severity = self.rule_definition.effective_severity(self.rule_set)

        if context is not None:
            message = template.format_map(_DefaultFormatDict(context))
        else:
            message = template

        self._findings.append(
            ValidationResult(
                rule_id=code,
                severity=severity,
                rule_set=self.rule_set,
                message=message,
                location=location,
                context=context,
                eba=self.rule_definition.eba,
            )
        )
