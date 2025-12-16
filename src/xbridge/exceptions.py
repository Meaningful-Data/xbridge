"""Custom exception types for the xbridge package."""

from __future__ import annotations

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


class XbridgeWarning(Warning):
    """Base warning for the xbridge library."""


class IdentifierPrefixWarning(XbridgeWarning):
    """Unknown identifier prefix; defaulting to 'rs'."""


class FilingIndicatorWarning(XbridgeWarning):
    """Facts orphaned by filing indicators; some are excluded."""
