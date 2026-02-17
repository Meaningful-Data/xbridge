"""EBA-ENTITY-001, EBA-ENTITY-002: Entity identifier checks.

Shared rules (XML + CSV).  Only the XML implementation is provided
here; the CSV side will be added when the CSV parameter infrastructure
is available.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

from lxml import etree

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl

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


def _check_lei_value(ctx: ValidationContext, value: str) -> None:
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
            location="entity:identifier",
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
            location="entity:identifier",
            context={
                "detail": (
                    f"LEI suffix '.{suffix}' is not recognised. "
                    f"Accepted suffixes: {', '.join(sorted('.' + s for s in _LEI_SUFFIXES))}."
                )
            },
        )
