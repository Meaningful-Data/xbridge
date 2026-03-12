"""Validation engine: rule selection and execution loop."""

from __future__ import annotations

import contextlib
import importlib
import json
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, Dict, List, Optional, Tuple, Union
from zipfile import BadZipFile, ZipFile

from lxml import etree

from xbridge.validation._context import ValidationContext
from xbridge.validation._models import RuleDefinition, ValidationResult
from xbridge.validation._registry import get_rule_impl, load_registry

# Paths to taxonomy index and module files (same as converter.py)
_MODULES_FOLDER = Path(__file__).parents[1] / "modules"
_INDEX_FILE = _MODULES_FOLDER / "index.json"


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


def _detect_zip_format(zip_path: Path) -> str:
    """Inspect a ZIP file to determine whether it contains CSV or XML.

    Returns ``"csv"`` or ``"xml"``.

    Raises:
        ValueError: If the ZIP content is not a recognized XBRL format.
    """
    with ZipFile(zip_path) as zf:
        entries = zf.namelist()

    # CSV signature: reports/report.json at any nesting level.
    if any(e == "reports/report.json" or e.endswith("/reports/report.json") for e in entries):
        return "csv"

    # XML signature: exactly one .xbrl file (at root level of the archive).
    xbrl_files = [e for e in entries if e.lower().endswith((".xbrl", ".xml")) and "/" not in e]
    if len(xbrl_files) == 1:
        return "xml"
    if len(xbrl_files) > 1:
        raise ValueError(
            f"ZIP contains {len(xbrl_files)} XBRL files; expected exactly one: {zip_path.name}"
        )

    raise ValueError(
        f"ZIP does not contain a recognized XBRL instance or CSV report package: {zip_path.name}"
    )


def _extract_xml_from_zip(zip_path: Path) -> Tuple[Path, Path]:
    """Extract a ZIP containing a single .xbrl file.

    Returns:
        A tuple of (temp_dir, extracted_xbrl_path).
    """
    temp_dir = Path(mkdtemp())
    with ZipFile(zip_path) as zf:
        zf.extractall(temp_dir)

    xbrl_files = [
        p for p in temp_dir.iterdir() if p.is_file() and p.suffix.lower() in (".xbrl", ".xml")
    ]
    if len(xbrl_files) != 1:
        raise ValueError(f"Expected exactly one XBRL file in ZIP, found {len(xbrl_files)}")
    return temp_dir, xbrl_files[0]


def _detect_format(file_path: Path) -> str:
    """Detect rule_set from file extension and, for ZIPs, content inspection.

    Raises ValueError for unsupported extensions or unrecognized ZIP contents.
    """
    suffix = file_path.suffix.lower()
    if suffix in (".xbrl", ".xml"):
        return "xml"
    if suffix == ".zip":
        return _detect_zip_format(file_path)
    raise ValueError(
        f"Unsupported file extension: {file_path.suffix!r}. Expected .xbrl, .xml or .zip."
    )


_cached_index: Optional[Dict[str, str]] = None


def _load_index() -> Dict[str, str]:
    """Load the taxonomy module index (cached after first call)."""
    global _cached_index  # noqa: PLW0603
    if _cached_index is not None:
        return _cached_index
    if not _INDEX_FILE.exists():
        _cached_index = {}
        return _cached_index
    with open(_INDEX_FILE, encoding="utf-8") as f:
        _cached_index = json.load(f)
    return _cached_index


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


def _try_extract_module_ref(root: etree._Element) -> Optional[str]:
    """Extract schemaRef href from an XML root element.

    Fallback for when XmlInstance parsing fails but the raw XML is parseable.
    Returns the href string or None.
    """
    xlink_href = "{http://www.w3.org/1999/xlink}href"
    for child in root:
        if child.prefix == "link":
            href = child.get(xlink_href)
            if href is not None:
                return href
    return None


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
        file: Path to an .xbrl/.xml (XML) or .zip (CSV or XML-in-ZIP) file.
        eba: When True, additionally runs EBA-specific rules.
        post_conversion: (CSV only) When True, skips structural and
            format checks guaranteed by xbridge's converter.

    Returns:
        A list of ValidationResult findings.

    Raises:
        ValueError: If the file extension is not supported or the ZIP
            content is unrecognized.
        FileNotFoundError: If the file does not exist.
    """
    file_path = Path(file).resolve()

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # 1. Detect format (inspects ZIP content when needed)
    try:
        rule_set = _detect_format(file_path)
    except BadZipFile:
        # Invalid ZIP — fall through to CSV rules so CSV-001 can report it.
        rule_set = "csv"
    except ValueError:
        if file_path.suffix.lower() == ".zip":
            # Valid ZIP but unrecognized content — run CSV structural rules
            # so CSV-002/CSV-004 can report what is missing.
            rule_set = "csv"
        else:
            raise

    # 2. Determine if input is a ZIP and resolve the actual XBRL file
    zip_path: Optional[Path] = None
    effective_path = file_path  # Path to the actual content to validate

    if file_path.suffix.lower() == ".zip":
        zip_path = file_path
        if rule_set == "xml":
            # XML-in-ZIP: extract and use the inner .xbrl file
            _temp_dir, effective_path = _extract_xml_from_zip(file_path)

    # 3. Read raw bytes from the effective content file
    #    For CSV ZIPs the raw bytes of the outer ZIP are never used by any
    #    rule — every rule opens the ZIP itself.  Skip the expensive read.
    raw_bytes = b"" if rule_set == "csv" else effective_path.read_bytes()

    # 4. Load registry and filter rules
    registry = load_registry()
    selected = select_rules(registry, rule_set, eba, post_conversion)

    # 5. Attempt parsing
    xml_instance = None
    csv_instance = None
    module = None
    xml_root: Optional[etree._Element] = None

    if rule_set == "xml":
        xml_instance = _try_parse_xml(effective_path, raw_bytes)
        if xml_instance is not None:
            xml_root = getattr(xml_instance, "root", None)
            module_ref = getattr(xml_instance, "module_ref", None)
            module = _try_load_module(module_ref)
        else:
            # XmlInstance failed but XML may still be parseable.
            # Parse once here so rule functions never need to.
            with contextlib.suppress(etree.XMLSyntaxError):
                xml_root = etree.fromstring(raw_bytes)
            # Try to extract module_ref from xml_root so taxonomy-based
            # rules (XML-070/071/072) can still run when only parsing failed.
            if xml_root is not None:
                module_ref = _try_extract_module_ref(xml_root)
                module = _try_load_module(module_ref)
    else:
        csv_instance = _try_parse_csv(file_path)
        if csv_instance is not None:
            module_ref = getattr(csv_instance, "module_ref", None)
            module = _try_load_module(module_ref)

    # 6. Import rule implementations to trigger @rule_impl registration
    importlib.import_module("xbridge.validation.rules")

    # 7. Execute each selected rule
    shared_cache: Dict[str, Any] = {}
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
            zip_path=zip_path,
            shared_cache=shared_cache,
        )
        impl(ctx)
        all_findings.extend(ctx.findings)

    return all_findings
