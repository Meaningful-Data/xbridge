"""Core data classes for the xbridge validation module."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional


class Severity(Enum):
    """Severity levels for validation findings.

    Matches specification §1.4:
    - ERROR: Violation of a MUST rule. The file is invalid.
    - WARNING: Violation of a SHOULD rule.
    - INFO: Informational observation.
    """

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class RuleDefinition:
    """A validation rule loaded from registry.json.

    Provides access to all registry fields and resolves format-specific
    overrides for severity and message.
    """

    def __init__(
        self,
        code: str,
        message: str,
        severity: Severity,
        xml: bool,
        csv: bool,
        eba: bool,
        post_conversion: bool,
        eba_ref: Optional[str],
        csv_severity: Optional[Severity] = None,
        csv_message: Optional[str] = None,
    ) -> None:
        self.code = code
        self.message = message
        self.severity = severity
        self.xml = xml
        self.csv = csv
        self.eba = eba
        self.post_conversion = post_conversion
        self.eba_ref = eba_ref
        self.csv_severity = csv_severity
        self.csv_message = csv_message

    def effective_severity(self, rule_set: str) -> Severity:
        """Return the severity for the given rule set.

        Returns csv_severity when rule_set is 'csv' and the override
        is set, otherwise returns the base severity.
        """
        if rule_set == "csv" and self.csv_severity is not None:
            return self.csv_severity
        return self.severity

    def effective_message(self, rule_set: str) -> str:
        """Return the message template for the given rule set.

        Returns csv_message when rule_set is 'csv' and the override
        is set, otherwise returns the base message.
        """
        if rule_set == "csv" and self.csv_message is not None:
            return self.csv_message
        return self.message

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RuleDefinition:
        """Construct a RuleDefinition from a registry JSON entry."""
        csv_severity_raw = data.get("csv_severity")
        return cls(
            code=data["code"],
            message=data["message"],
            severity=Severity(data["severity"]),
            xml=data["xml"],
            csv=data["csv"],
            eba=data["eba"],
            post_conversion=data["post_conversion"],
            eba_ref=data.get("eba_ref"),
            csv_severity=Severity(csv_severity_raw) if csv_severity_raw is not None else None,
            csv_message=data.get("csv_message"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a dict matching the registry JSON format."""
        result: Dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "xml": self.xml,
            "csv": self.csv,
            "eba": self.eba,
            "post_conversion": self.post_conversion,
            "eba_ref": self.eba_ref,
        }
        if self.csv_severity is not None:
            result["csv_severity"] = self.csv_severity.value
        if self.csv_message is not None:
            result["csv_message"] = self.csv_message
        return result

    def __repr__(self) -> str:
        return f"RuleDefinition(code={self.code!r}, severity={self.severity.value})"


class ValidationResult:
    """A single validation finding emitted by a rule implementation.

    Fields match specification §1.5.
    """

    def __init__(
        self,
        rule_id: str,
        severity: Severity,
        rule_set: str,
        message: str,
        location: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.rule_id = rule_id
        self.severity = severity
        self.rule_set = rule_set
        self.message = message
        self.location = location
        self.context = context

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a dict for programmatic consumption."""
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "rule_set": self.rule_set,
            "message": self.message,
            "location": self.location,
            "context": self.context,
        }

    def __repr__(self) -> str:
        return f"[{self.severity.value}] {self.rule_id}: {self.message} at {self.location}"
