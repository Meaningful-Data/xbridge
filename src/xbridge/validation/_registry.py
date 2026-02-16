"""Rule registry for the xbridge validation module.

Links registry.json entries to Python implementation functions via a
decorator pattern. Provides loading, registration, and lookup facilities.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from xbridge.validation._models import RuleDefinition

# Module-level registry mapping (code, format) → implementation function.
# Populated at import time by @rule_impl decorators in rules/*.py files.
_impl_registry: Dict[Tuple[str, Optional[str]], Callable[..., Any]] = {}


def rule_impl(
    code: str, format: Optional[str] = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a function as the implementation for a rule.

    Args:
        code: The rule code (e.g. "XML-001", "EBA-ENTITY-001").
        format: Optional format qualifier — "xml" or "csv".
                Required for shared rules that need different
                implementations per format.
                Omit for format-specific rules (XML-*, CSV-*).

    Raises:
        ValueError: If the same (code, format) key is already registered.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        key = (code, format)
        if key in _impl_registry:
            raise ValueError(
                f"Duplicate rule implementation for {key}: "
                f"{_impl_registry[key].__name__} already registered"
            )
        _impl_registry[key] = func
        return func

    return decorator


def get_rule_impl(code: str, format: str) -> Optional[Callable[..., Any]]:
    """Look up the implementation function for a rule.

    Resolution order:
      1. Format-specific: (code, format) — e.g. ("EBA-ENTITY-001", "xml")
      2. Generic: (code, None) — e.g. ("XML-001", None)

    Returns None if no implementation is registered.
    """
    return _impl_registry.get((code, format)) or _impl_registry.get((code, None))


def load_registry() -> List[RuleDefinition]:
    """Load and parse registry.json into a list of RuleDefinition objects.

    Reads from the registry.json file in the same package directory.
    Loaded fresh on each call (not cached) so tests can substitute
    modified registries.
    """
    registry_path = Path(__file__).parent / "registry.json"
    with open(registry_path, encoding="utf-8") as f:
        data: List[Dict[str, Any]] = json.load(f)
    return [RuleDefinition.from_dict(entry) for entry in data]


def _clear_registry() -> None:
    """Clear the internal implementation registry.

    Used in test teardown to avoid decorator registrations leaking
    between tests.
    """
    _impl_registry.clear()
