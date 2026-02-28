"""EBA-ENTITY-001, EBA-ENTITY-002: Entity identifier checks.

Shared rules (XML + CSV).

XML side reads the ``xbrli:identifier`` element from the first context.
CSV side reads the ``entityID`` parameter from ``parameters.csv``
(format: ``prefix:value``, e.g. ``lei:529900T8BM49AURSDO55``).
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

from lxml import etree

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl
from xbridge.validation.rules.csv_parameters import _parse_parameters

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_XBRLI_NS = "http://www.xbrl.org/2003/instance"
_XBRLI_CONTEXT = f"{{{_XBRLI_NS}}}context"
_XBRLI_ENTITY = f"{{{_XBRLI_NS}}}entity"
_XBRLI_IDENTIFIER = f"{{{_XBRLI_NS}}}identifier"

_ACCEPTED_SCHEMES = frozenset(
    {
        "http://standards.iso.org/iso/17442",
        "https://eurofiling.info/eu/rs",
    }
)

_LEI_SCHEME = "http://standards.iso.org/iso/17442"

# CSV entityID prefix → full scheme URI.
_CSV_PREFIX_TO_SCHEME = {
    "lei": "http://standards.iso.org/iso/17442",
    "rs": "https://eurofiling.info/eu/rs",
}

_PARAMETERS_CSV = "reports/parameters.csv"

# LEI base: exactly 20 alphanumeric characters.
_LEI_BASE_RE = re.compile(r"^[A-Z0-9]{20}$")

# Known suffixes appended to the LEI.
_LEI_SUFFIXES = frozenset(
    {
        "CON",
        "IND",
        "CRDLIQSUBGRP",
    }
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _first_identifier(root: etree._Element) -> Optional[Tuple[str, str]]:
    """Return *(scheme, value)* from the first context, or ``None``."""
    ctx_elem = root.find(f".//{_XBRLI_CONTEXT}")
    if ctx_elem is None:
        return None
    entity = ctx_elem.find(_XBRLI_ENTITY)
    if entity is None:
        return None
    ident = entity.find(_XBRLI_IDENTIFIER)
    if ident is None:
        return None
    scheme = ident.get("scheme", "")
    value = (ident.text or "").strip()
    return (scheme, value)


def _parse_csv_entity(ctx: ValidationContext) -> Optional[Tuple[str, str]]:
    """Parse CSV ``entityID`` into *(scheme_uri, value)*.

    Returns ``None`` when ``entityID`` is missing or empty (CSV-022 handles).
    Returns ``("", raw_value)`` when no colon prefix is found.
    """
    params = _parse_parameters(ctx)
    if params is None:
        return None
    raw = params.get("entityID", "").strip()
    if not raw:
        return None
    colon = raw.find(":")
    if colon < 1:
        # No valid prefix — return empty scheme so EBA-ENTITY-001 flags it.
        return ("", raw)
    prefix = raw[:colon]
    value = raw[colon + 1 :]
    scheme = _CSV_PREFIX_TO_SCHEME.get(prefix, "")
    if not scheme:
        # Unknown prefix — return it as-is for the error message.
        return (prefix, value)
    return (scheme, value)


# ---------------------------------------------------------------------------
# EBA-ENTITY-001  Accepted identifier schemes
# ---------------------------------------------------------------------------


@rule_impl("EBA-ENTITY-001", format="xml")
def check_entity_scheme_xml(ctx: ValidationContext) -> None:
    """The entity identifier @scheme MUST be an accepted scheme."""
    root = ctx.xml_root
    if root is None:
        return
    pair = _first_identifier(root)
    if pair is None:
        return
    scheme, _value = pair
    if scheme not in _ACCEPTED_SCHEMES:
        ctx.add_finding(
            location="entity:identifier",
            context={
                "detail": (
                    f"Scheme '{scheme}' is not accepted. "
                    f"Expected 'http://standards.iso.org/iso/17442' (LEI) "
                    f"or 'https://eurofiling.info/eu/rs' (qualified)."
                )
            },
        )


# ---------------------------------------------------------------------------
# EBA-ENTITY-002  Identifier value conventions
# ---------------------------------------------------------------------------


@rule_impl("EBA-ENTITY-002", format="xml")
def check_entity_value_xml(ctx: ValidationContext) -> None:
    """The entity identifier value MUST follow reporting conventions."""
    root = ctx.xml_root
    if root is None:
        return
    pair = _first_identifier(root)
    if pair is None:
        return
    scheme, value = pair

    if not value:
        ctx.add_finding(
            location="entity:identifier",
            context={"detail": "Entity identifier value is empty."},
        )
        return

    if scheme == _LEI_SCHEME:
        _check_lei_value(ctx, value)


def _check_lei_value(
    ctx: ValidationContext, value: str, location: str = "entity:identifier"
) -> None:
    """Validate a LEI-scheme identifier value."""
    dot = value.find(".")
    if dot >= 0:
        base = value[:dot]
        suffix = value[dot + 1 :]
    else:
        base = value
        suffix = None

    if not _LEI_BASE_RE.match(base):
        ctx.add_finding(
            location=location,
            context={
                "detail": (
                    f"LEI base '{base}' is not valid — "
                    f"expected exactly 20 alphanumeric characters (A-Z, 0-9)."
                )
            },
        )
        return

    if suffix is not None and suffix not in _LEI_SUFFIXES:
        ctx.add_finding(
            location=location,
            context={
                "detail": (
                    f"LEI suffix '.{suffix}' is not recognised. "
                    f"Accepted suffixes: {', '.join(sorted('.' + s for s in _LEI_SUFFIXES))}."
                )
            },
        )


# ---------------------------------------------------------------------------
# CSV implementations
# ---------------------------------------------------------------------------


@rule_impl("EBA-ENTITY-001", format="csv")
def check_entity_scheme_csv(ctx: ValidationContext) -> None:
    """The entityID parameter scheme MUST be an accepted scheme (CSV)."""
    pair = _parse_csv_entity(ctx)
    if pair is None:
        return  # Missing or empty entityID — CSV-022 handles.
    scheme, _value = pair
    if scheme not in _ACCEPTED_SCHEMES:
        # Show the raw prefix for clarity.
        ctx.add_finding(
            location=_PARAMETERS_CSV,
            context={
                "detail": (
                    f"entityID scheme '{scheme}' is not accepted. "
                    f"Expected prefix 'lei' (http://standards.iso.org/iso/17442) "
                    f"or 'rs' (https://eurofiling.info/eu/rs)."
                )
            },
        )


@rule_impl("EBA-ENTITY-002", format="csv")
def check_entity_value_csv(ctx: ValidationContext) -> None:
    """The entityID parameter value MUST follow reporting conventions (CSV)."""
    pair = _parse_csv_entity(ctx)
    if pair is None:
        return  # Missing or empty entityID — CSV-022 handles.
    scheme, value = pair

    if not value:
        ctx.add_finding(
            location=_PARAMETERS_CSV,
            context={"detail": "entityID value part is empty."},
        )
        return

    # Only validate value format when the scheme is recognised.
    if scheme == _LEI_SCHEME:
        _check_lei_value(ctx, value, location=_PARAMETERS_CSV)
