"""Fact value checks against the XBRL item type of each concept.

Shared by the XML (XML-073, XML-074) and CSV (CSV-063, CSV-064) rules.

The item type of every EBA metric is read from ``modules/metric_types.json``,
which the taxonomy loader generates from the ``dict/met/**/met.xsd`` schemas
of the taxonomy package.  Keys use the metric prefix convention of the module
JSON files (``eba_met:mi53``, ``eba_met_4.2:qAZH``).

Values are checked against the lexical space of the XML Schema type each item
type derives from.  Types whose whiteSpace facet is ``collapse`` (numbers,
dates, booleans, QNames) are stripped before checking, so leading or trailing
whitespace is accepted, as a schema validator would do.  Facts whose concept or
item type is not known are not checked.
"""

from __future__ import annotations

import calendar
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from xbridge.instance import _derive_metric_prefix

METRIC_TYPES_PATH = Path(__file__).resolve().parents[2] / "modules" / "metric_types.json"

ENUMERATION_TYPE = "enum:enumerationItemType"

# XML Schema whiteSpace="collapse": leading/trailing whitespace is removed
# before the lexical value is checked.
_XML_WHITESPACE = " \t\n\r"

# Explicit [0-9] (not \d) so that non-ASCII digits are rejected.
_DECIMAL_RE = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)")
_INTEGER_RE = re.compile(r"[+-]?[0-9]+")
_DATE_RE = re.compile(
    r"(-?)([0-9]{4,})-([0-9]{2})-([0-9]{2})"
    r"(?:Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?"
)
_NCNAME = r"[^\W\d][\w.\-]*"
_QNAME_RE = re.compile(rf"(?:({_NCNAME}):)?({_NCNAME})")

_BOOLEAN_VALUES = frozenset({"true", "false", "1", "0"})

_DAYS_IN_MONTH = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


# ---------------------------------------------------------------------------
# Lexical checks
# ---------------------------------------------------------------------------
def _is_decimal(value: str) -> bool:
    return _DECIMAL_RE.fullmatch(value.strip(_XML_WHITESPACE)) is not None


def _is_integer(value: str) -> bool:
    return _INTEGER_RE.fullmatch(value.strip(_XML_WHITESPACE)) is not None


def _is_boolean(value: str) -> bool:
    return value.strip(_XML_WHITESPACE) in _BOOLEAN_VALUES


def _is_true(value: str) -> bool:
    # model:trueItemType restricts xbrli:booleanItemType with pattern="true".
    return value.strip(_XML_WHITESPACE) == "true"


def _is_date(value: str) -> bool:
    match = _DATE_RE.fullmatch(value.strip(_XML_WHITESPACE))
    if match is None:
        return False
    year, month, day = int(match.group(2)), int(match.group(3)), int(match.group(4))
    if year == 0 or not 1 <= month <= 12:
        # Year 0000 is not allowed in XML Schema 1.0.
        return False
    days_in_month = _DAYS_IN_MONTH[month - 1] + (1 if month == 2 and calendar.isleap(year) else 0)
    return 1 <= day <= days_in_month


def _is_not_empty(value: str) -> bool:
    # model:notEmptyStringItemType: minLength=1 on a whiteSpace="preserve" type.
    return len(value) > 0


def _is_qname(value: str) -> bool:
    return _QNAME_RE.fullmatch(value.strip(_XML_WHITESPACE)) is not None


_DECIMAL = (_is_decimal, "a decimal number")

# item type → (check, description of the expected value)
_CHECKS: Dict[str, Tuple[Callable[[str], bool], str]] = {
    "xbrli:monetaryItemType": _DECIMAL,
    "xbrli:decimalItemType": _DECIMAL,
    "xbrli:pureItemType": _DECIMAL,
    "xbrli:sharesItemType": _DECIMAL,
    "num:percentItemType": _DECIMAL,
    "dtr:percentItemType": _DECIMAL,
    "xbrli:integerItemType": (_is_integer, "an integer"),
    "xbrli:booleanItemType": (_is_boolean, "a boolean (true, false, 1 or 0)"),
    "model:trueItemType": (_is_true, "the value 'true'"),
    "xbrli:dateItemType": (_is_date, "a valid date (YYYY-MM-DD)"),
    "model:notEmptyStringItemType": (_is_not_empty, "a non-empty string"),
    ENUMERATION_TYPE: (_is_qname, "a QName (prefix:localName)"),
}


def invalid_value_reason(item_type: str, value: str) -> Optional[str]:
    """Return what *value* should have been when it is not valid for *item_type*.

    Returns ``None`` when the value is valid, or when *item_type* has no check
    (strings, unknown types).
    """
    check = _CHECKS.get(item_type)
    if check is None:
        return None
    is_valid, expected = check
    return None if is_valid(value) else expected


# ---------------------------------------------------------------------------
# Enumeration values
# ---------------------------------------------------------------------------
def split_qname(value: str) -> Optional[Tuple[Optional[str], str]]:
    """Split a QName value into ``(prefix, localname)``; ``None`` if not a QName."""
    match = _QNAME_RE.fullmatch(value.strip(_XML_WHITESPACE))
    if match is None:
        return None
    return match.group(1), match.group(2)


def normalize_enumeration_value(namespace_uri: str, localname: str) -> Optional[str]:
    """Return the enumeration value in the module prefix convention.

    Allowed values in the module JSON files use the EBA prefixes
    (``eba_AS:x1`` for domain members, ``eba_met:si288`` for metrics), so a
    reported value is compared after deriving the same prefix from its
    namespace.
    """
    prefix = _derive_metric_prefix(namespace_uri)
    return f"{prefix}:{localname}" if prefix else None


# ---------------------------------------------------------------------------
# Metric types
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def load_metric_types() -> Dict[str, str]:
    """Return the ``{metric_qname: item_type}`` map bundled with xbridge.

    Returns an empty map when the file is missing, so the checks are skipped.
    """
    try:
        with open(METRIC_TYPES_PATH, encoding="utf-8") as fl:
            data = json.load(fl)
    except FileNotFoundError:
        return {}
    return data if isinstance(data, dict) else {}
