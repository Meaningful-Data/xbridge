"""Validation context passed to rule implementation functions."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

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
    ) -> None:
        self.rule_set = rule_set
        self.rule_definition = rule_definition
        self.file_path = file_path
        self.raw_bytes = raw_bytes
        self.xml_instance = xml_instance
        self.csv_instance = csv_instance
        self.module = module
        self._findings: List[ValidationResult] = []

    @property
    def findings(self) -> List[ValidationResult]:
        """The accumulated validation findings."""
        return self._findings

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
            )
        )
