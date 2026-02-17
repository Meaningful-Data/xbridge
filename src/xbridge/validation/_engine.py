"""Validation engine: rule selection and execution loop."""

from __future__ import annotations

import contextlib
import importlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from lxml import etree

from xbridge.validation._context import ValidationContext
from xbridge.validation._models import RuleDefinition, ValidationResult
from xbridge.validation._registry import get_rule_impl, load_registry

# Paths to taxonomy index and module files (same as converter.py)
_MODULES_FOLDER = Path(__file__).parents[1] / "modules"
_INDEX_FILE = _MODULES_FOLDER / "index.json"

# Supported file extensions → rule_set mapping
_FORMAT_MAP: Dict[str, str] = {
    ".xbrl": "xml",
    ".xml": "xml",
    ".zip": "csv",
}


def select_rules(
    registry: List[RuleDefinition],
    rule_set: str,
    eba: bool,
    post_conversion: bool,
) -> List[RuleDefinition]:
    """Filter registry rules according to the specification §2.1 decision diagram.

    Returns the selected rules preserving registry ordering.
    """
    selected: List[RuleDefinition] = []
    for rule in registry:
        # Format filter
        if rule_set == "xml" and not rule.xml:
            continue
        if rule_set == "csv" and not rule.csv:
            continue
        # EBA gate
        if rule.eba and not eba:
            continue
        # Post-conversion filter (CSV only)
        if rule_set == "csv" and post_conversion and not rule.post_conversion:
            continue
        selected.append(rule)
    return selected


def _detect_format(file_path: Path) -> str:
    """Detect rule_set from file extension (case-insensitive).

    Raises ValueError for unsupported extensions.
    """
    suffix = file_path.suffix.lower()
    rule_set = _FORMAT_MAP.get(suffix)
    if rule_set is None:
        raise ValueError(
            f"Unsupported file extension: {file_path.suffix!r}. Expected .xbrl or .zip."
        )
    return rule_set


def _load_index() -> Dict[str, str]:
    """Load the taxonomy module index."""
    if not _INDEX_FILE.exists():
        return {}
    with open(_INDEX_FILE, encoding="utf-8") as f:
        result: Dict[str, str] = json.load(f)
    return result


def _try_load_module(module_ref: Optional[str]) -> Any:
    """Try to load a taxonomy Module from a module_ref.

    Returns Module or None if loading fails.
    """
    if module_ref is None:
        return None

    index = _load_index()
    if module_ref not in index:
        return None

    module_path = _MODULES_FOLDER / index[module_ref]
    if not module_path.exists():
        return None

    from xbridge.modules import Module

    return Module.from_serialized(module_path)


def _try_parse_xml(file_path: Path, raw_bytes: bytes) -> Any:
    """Try to construct an XmlInstance. Returns instance or None."""
    try:
        from xbridge.instance import XmlInstance

        return XmlInstance(file_path)
    except Exception:
        return None


def _try_parse_csv(
    file_path: Path,
) -> Any:
    """Try to construct a CsvInstance. Returns instance or None."""
    try:
        from xbridge.instance import CsvInstance

        return CsvInstance(file_path)
    except Exception:
        return None


def run_validation(
    file: Union[str, Path],
    eba: bool = False,
    post_conversion: bool = False,
) -> List[ValidationResult]:
    """Run the validation engine on an XBRL instance file.

    This is the main execution loop called by the public validate() API.

    Args:
        file: Path to an .xbrl (XML) or .zip (CSV) file.
        eba: When True, additionally runs EBA-specific rules.
        post_conversion: (CSV only) When True, skips structural and
            format checks guaranteed by xbridge's converter.

    Returns:
        A list of ValidationResult findings.

    Raises:
        ValueError: If the file extension is not supported.
        FileNotFoundError: If the file does not exist.
    """
    file_path = Path(file).resolve()

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # 1. Detect format
    rule_set = _detect_format(file_path)

    # 2. Read raw bytes
    raw_bytes = file_path.read_bytes()

    # 3. Load registry
    registry = load_registry()

    # 4. Filter rules
    selected = select_rules(registry, rule_set, eba, post_conversion)

    # 5. Attempt parsing
    xml_instance = None
    csv_instance = None
    module = None
    xml_root: Optional[etree._Element] = None

    if rule_set == "xml":
        xml_instance = _try_parse_xml(file_path, raw_bytes)
        if xml_instance is not None:
            xml_root = getattr(xml_instance, "root", None)
            module_ref = getattr(xml_instance, "module_ref", None)
            module = _try_load_module(module_ref)
        else:
            # XmlInstance failed but XML may still be parseable.
            # Parse once here so rule functions never need to.
            with contextlib.suppress(etree.XMLSyntaxError):
                xml_root = etree.fromstring(raw_bytes)
    else:
        csv_instance = _try_parse_csv(file_path)
        if csv_instance is not None:
            module_ref = getattr(csv_instance, "module_ref", None)
            module = _try_load_module(module_ref)

    # 6. Import rule implementations to trigger @rule_impl registration
    importlib.import_module("xbridge.validation.rules")

    # 7. Execute each selected rule
    all_findings: List[ValidationResult] = []
    for rule in selected:
        impl = get_rule_impl(rule.code, rule_set)
        if impl is None:
            continue

        ctx = ValidationContext(
            rule_set=rule_set,
            rule_definition=rule,
            file_path=file_path,
            raw_bytes=raw_bytes,
            xml_instance=xml_instance,
            csv_instance=csv_instance,
            module=module,
            xml_root=xml_root,
        )
        impl(ctx)
        all_findings.extend(ctx.findings)

    return all_findings
