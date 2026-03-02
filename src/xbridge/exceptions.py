"""Custom exception types for the xbridge package."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


class SchemaRefValueError(ValueError):
    """Raised when schemaRef validation fails in an XBRL instance."""

    def __init__(self, error_message: str, offending_value: Optional[Any] = None) -> None:
        super().__init__(error_message)
        self.offending_value = offending_value


class DecimalValueError(ValueError):
    """Raised when decimals metadata contains unsupported values."""

    def __init__(self, error_message: str, offending_value: Optional[Any] = None) -> None:
        super().__init__(error_message)
        self.offending_value = offending_value


class FilingIndicatorValueError(ValueError):
    """Raised when filing indicator validation fails."""

    def __init__(self, error_message: str, offending_value: Optional[Any] = None) -> None:
        super().__init__(error_message)
        self.offending_value = offending_value


class ValidationError(ValueError):
    """Raised when the validate-convert-validate pipeline encounters errors.

    Attributes:
        results: The validation results dictionary with ``"errors"`` and
            ``"warnings"`` keys.
        path: When set, the conversion succeeded but *post*-conversion
            validation found errors.  The value is the path to the
            generated CSV ZIP archive.  ``None`` means the error was
            raised during *pre*-conversion validation.
    """

    def __init__(
        self,
        results: dict[str, Any],
        path: Optional[Path] = None,
    ) -> None:
        error_count = sum(len(v) for v in results.get("errors", {}).values())
        phase = "Post-conversion" if path is not None else "Pre-conversion"
        super().__init__(f"{phase} validation failed with {error_count} error(s)")
        self.results = results
        self.path = path


class XbridgeWarning(Warning):
    """Base warning for the xbridge library."""


class IdentifierPrefixWarning(XbridgeWarning):
    """Unknown identifier prefix; defaulting to 'rs'."""


class FilingIndicatorWarning(XbridgeWarning):
    """Facts orphaned by filing indicators; some are excluded."""
