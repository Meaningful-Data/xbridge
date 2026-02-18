"""Validation module for xbridge XBRL instance files.

Public API::

    from xbridge.validation import validate, ValidationResult, Severity

    results = validate("path/to/instance.xbrl", eba=True)
    # results == {"errors": {"XML-001": [...]}, "warnings": {"XML-066": [...]}}
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Union

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity, ValidationResult

__all__ = ["validate", "ValidationResult", "Severity"]


def validate(
    file: Union[str, Path],
    eba: bool = False,
    post_conversion: bool = False,
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """Validate an XBRL instance file.

    Args:
        file: Path to an .xbrl (XML) or .zip (CSV) file.
        eba: When True, additionally runs EBA-specific rules.
        post_conversion: (CSV only) When True, skips structural and
            format checks guaranteed by xbridge's converter, keeping
            only EBA semantic checks. Has no effect for .xbrl files.

    Returns:
        A dictionary with two keys:

        - ``"errors"`` — dict keyed by rule code, each value a list of
          ERROR findings as dicts.
        - ``"warnings"`` — dict keyed by rule code, each value a list of
          WARNING (and INFO) findings as dicts.

        Each dict entry is the ``to_dict()`` representation of a
        :class:`ValidationResult`.
    """
    findings = run_validation(file, eba=eba, post_conversion=post_conversion)

    errors: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    warnings: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for f in findings:
        if f.severity == Severity.ERROR:
            errors[f.rule_id].append(f.to_dict())
        else:
            warnings[f.rule_id].append(f.to_dict())

    return {"errors": dict(errors), "warnings": dict(warnings)}
