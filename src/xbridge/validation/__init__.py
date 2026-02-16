"""Validation module for xbridge XBRL instance files.

Public API::

    from xbridge.validation import validate, ValidationResult, Severity

    results = validate("path/to/instance.xbrl", eba=True)
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Union

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity, ValidationResult

__all__ = ["validate", "ValidationResult", "Severity"]


def validate(
    file: Union[str, Path],
    eba: bool = False,
    post_conversion: bool = False,
) -> List[ValidationResult]:
    """Validate an XBRL instance file.

    Args:
        file: Path to an .xbrl (XML) or .zip (CSV) file.
        eba: When True, additionally runs EBA-specific rules.
        post_conversion: (CSV only) When True, skips structural and
            format checks guaranteed by xbridge's converter, keeping
            only EBA semantic checks. Has no effect for .xbrl files.

    Returns:
        A list of ValidationResult findings, ordered by rule execution
        sequence. An empty list means no issues were found.
    """
    return run_validation(file, eba=eba, post_conversion=post_conversion)
