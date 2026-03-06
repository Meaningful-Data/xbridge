"""Validation module for xbridge XBRL instance files.

Public API::

    from xbridge.validation import validate, ValidationResult, Severity

    results = validate("path/to/instance.xbrl", eba=True)
    # results == {
    #     "XBRL": {"errors": {"XML-001": [...]}, "warnings": {}},
    #     "EBA":  {"errors": {}, "warnings": {"EBA-CUR-003": [...]}},
    # }
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Union

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity, ValidationResult

__all__ = ["validate", "ValidationResult", "Severity"]

_SectionDict = Dict[str, Dict[str, List[Dict[str, Any]]]]


def _empty_section() -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """Return an empty ``{"errors": {}, "warnings": {}}`` section."""
    return {"errors": {}, "warnings": {}}


def validate(
    file: Union[str, Path],
    eba: bool = False,
    post_conversion: bool = False,
) -> Dict[str, _SectionDict]:
    """Validate an XBRL instance file.

    Args:
        file: Path to an .xbrl (XML) or .zip (CSV) file.
        eba: When True, additionally runs EBA-specific rules.
        post_conversion: (CSV only) When True, skips structural and
            format checks guaranteed by xbridge's converter, keeping
            only EBA semantic checks. Has no effect for .xbrl files.

    Returns:
        A dictionary keyed by validation scope:

        - ``"XBRL"`` — always present; results from XBRL-standard rules.
        - ``"EBA"`` — only present when *eba* is True; results from
          EBA-specific rules.

        Each section contains:

        - ``"errors"`` — dict keyed by rule code, each value a list of
          ERROR findings as dicts.
        - ``"warnings"`` — dict keyed by rule code, each value a list of
          WARNING (and INFO) findings as dicts.

        Each dict entry is the ``to_dict()`` representation of a
        :class:`ValidationResult`.
    """
    findings = run_validation(file, eba=eba, post_conversion=post_conversion)

    xbrl_errors: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    xbrl_warnings: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    eba_errors: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    eba_warnings: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for f in findings:
        if f.eba:
            target_errors, target_warnings = eba_errors, eba_warnings
        else:
            target_errors, target_warnings = xbrl_errors, xbrl_warnings

        if f.severity == Severity.ERROR:
            target_errors[f.rule_id].append(f.to_dict())
        else:
            target_warnings[f.rule_id].append(f.to_dict())

    result: Dict[str, _SectionDict] = {
        "XBRL": {"errors": dict(xbrl_errors), "warnings": dict(xbrl_warnings)},
    }
    if eba:
        result["EBA"] = {"errors": dict(eba_errors), "warnings": dict(eba_warnings)}
    return result
