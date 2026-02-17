"""XML-070..XML-072: Taxonomy conformance checks.

Uses ``ctx.xml_root`` and ``ctx.module`` (the pre-loaded Module).
Taxonomy data is extracted **once** from the module and cached.
The XML is scanned **once** for fact concepts and explicit dimension
members; results are cached per root so all three rule functions
share the work.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, FrozenSet, List, Optional, Tuple

from lxml import etree

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl

if TYPE_CHECKING:
    from xbridge.modules import Module

# ---------------------------------------------------------------------------
# Namespace / tag constants
# ---------------------------------------------------------------------------
_XBRLI_NS = "http://www.xbrl.org/2003/instance"
_LINK_NS = "http://www.xbrl.org/2003/linkbase"
_FIND_NS = "http://www.eurofiling.info/xbrl/ext/filing-indicators"
_XBRLDI_NS = "http://xbrl.org/2006/xbrldi"

_EXPLICIT_MEMBER_TAG = f"{{{_XBRLDI_NS}}}explicitMember"

# Infrastructure namespaces — children in these are not facts.
_INFRA_NS = frozenset({_XBRLI_NS, _LINK_NS, _FIND_NS})

# Special dimension keys that are not real dimensions.
_SKIP_DIM_KEYS = frozenset({"concept", "unit", "decimals"})

# URI/localname pair.
_UriLn = Tuple[str, str]


# ---------------------------------------------------------------------------
# Taxonomy data extraction (cached per module)
# ---------------------------------------------------------------------------
class _TaxonomyData:
    """Pre-computed taxonomy lookup sets extracted from a Module.

    Dimension keys are matched by **localname only** because
    ``Variable.from_dict`` strips namespace prefixes from dimension
    keys during deserialization (e.g. ``eba_dim:BAS`` → ``BAS``).
    """

    __slots__ = (
        "valid_concepts",
        "valid_dim_localnames",
        "dim_members",
        "open_key_localnames",
    )

    def __init__(
        self,
        valid_concepts: FrozenSet[_UriLn],
        valid_dim_localnames: FrozenSet[str],
        dim_members: Dict[str, FrozenSet[_UriLn]],
        open_key_localnames: FrozenSet[str],
    ) -> None:
        self.valid_concepts = valid_concepts
        self.valid_dim_localnames = valid_dim_localnames
        self.dim_members = dim_members
        self.open_key_localnames = open_key_localnames


def _resolve_qname(qname: str, nsmap: Dict[Optional[str], str]) -> Optional[_UriLn]:
    """Resolve *prefix:localname* to *(namespace_uri, localname)*.

    Returns ``None`` when the prefix cannot be resolved.
    """
    colon = qname.find(":")
    if colon < 1:
        return None
    prefix = qname[:colon]
    uri = nsmap.get(prefix)
    if uri is None:
        return None
    return (uri, qname[colon + 1 :])


def _extract_taxonomy(module: Module, nsmap: Dict[Optional[str], str]) -> _TaxonomyData:
    """Build lookup sets from *module*, resolving QNames via *nsmap*.

    Dimension keys may be bare localnames (``BAS``) when the module was
    loaded via ``from_serialized`` / ``Variable.from_dict``, or prefixed
    QNames (``eba_dim:BAS``) when loaded from the raw taxonomy.  Both
    forms are handled — the localname is always extracted and used as
    the dimension identifier.
    """
    concepts: set[_UriLn] = set()
    dim_localnames: set[str] = set()
    dim_members: Dict[str, set[_UriLn]] = {}
    open_keys: set[str] = set()

    for table in module.tables:
        # Collect open keys.
        for ok in table.open_keys:
            open_keys.add(ok)

        # "datapoints" architecture — variables list.
        for var in table.variables:
            _collect_dims(var.dimensions, nsmap, concepts, dim_localnames, dim_members)

        # "headers" architecture — columns list.
        if table.architecture == "headers" and table.columns:
            for col in table.columns:
                col_dims = col.get("dimensions")
                if isinstance(col_dims, dict):
                    _collect_dims(col_dims, nsmap, concepts, dim_localnames, dim_members)

    # Open key dimensions are valid dimensions but their members are not
    # enumerated in the module.  They are already bare localnames.
    for ok in open_keys:
        dim_localnames.add(ok)

    return _TaxonomyData(
        valid_concepts=frozenset(concepts),
        valid_dim_localnames=frozenset(dim_localnames),
        dim_members={k: frozenset(v) for k, v in dim_members.items()},
        open_key_localnames=frozenset(open_keys),
    )


def _collect_dims(
    dims: Dict[str, str],
    nsmap: Dict[Optional[str], str],
    concepts: set[_UriLn],
    dim_localnames: set[str],
    dim_members: Dict[str, set[_UriLn]],
) -> None:
    """Collect concepts, dimensions, and members from a single dimensions dict.

    Dimension keys may be prefixed (``eba_dim:BAS``) or bare localnames
    (``BAS``).  In either case the localname is extracted and used as the
    dimension identifier.
    """
    for key, value in dims.items():
        if key == "concept":
            resolved = _resolve_qname(value, nsmap)
            if resolved is not None:
                concepts.add(resolved)
        elif key in _SKIP_DIM_KEYS or key.startswith("$"):
            continue
        else:
            # Extract localname: strip prefix if present.
            colon = key.find(":")
            dim_ln = key[colon + 1 :] if colon >= 1 else key
            dim_localnames.add(dim_ln)
            member_resolved = _resolve_qname(value, nsmap)
            if member_resolved is not None:
                dim_members.setdefault(dim_ln, set()).add(member_resolved)


# Single-entry caches.
_last_taxonomy: Optional[Tuple[int, _TaxonomyData]] = None


def _get_taxonomy(module: Module, nsmap: Dict[Optional[str], str]) -> _TaxonomyData:
    """Return cached taxonomy data for *module*."""
    global _last_taxonomy  # noqa: PLW0603
    mid = id(module)
    if _last_taxonomy is not None and _last_taxonomy[0] == mid:
        return _last_taxonomy[1]
    result = _extract_taxonomy(module, nsmap)
    _last_taxonomy = (mid, result)
    return result


# ---------------------------------------------------------------------------
# XML scan (cached per root)
# ---------------------------------------------------------------------------
class _ScanResult:
    """Findings collected in one pass over the XML tree."""

    __slots__ = ("unknown_concepts", "unknown_dimensions", "invalid_members")

    def __init__(self) -> None:
        # (localname,) for XML-070
        self.unknown_concepts: List[str] = []
        # (context_id, dimension_qname) for XML-071
        self.unknown_dimensions: List[Tuple[str, str]] = []
        # (context_id, dimension_qname, member_qname) for XML-072
        self.invalid_members: List[Tuple[str, str, str]] = []


_last_scan: Optional[Tuple[int, _ScanResult]] = None


def _scan(root: etree._Element, taxonomy: _TaxonomyData) -> _ScanResult:
    """Single-pass scan collecting findings for all three rules."""
    global _last_scan  # noqa: PLW0603
    rid = id(root)
    if _last_scan is not None and _last_scan[0] == rid:
        return _last_scan[1]

    r = _ScanResult()
    nsmap = root.nsmap

    # --- XML-070: check fact concepts ---
    for child in root:
        tag = child.tag
        if not isinstance(tag, str):
            continue
        if not tag.startswith("{"):
            continue
        ns_end = tag.index("}")
        ns = tag[1:ns_end]
        if ns in _INFRA_NS:
            continue
        localname = tag[ns_end + 1 :]
        if (ns, localname) not in taxonomy.valid_concepts:
            r.unknown_concepts.append(localname)

    # --- XML-071 / XML-072: check explicit dimension members ---
    for em in root.iter(_EXPLICIT_MEMBER_TAG):
        # Find parent context id.
        parent = em.getparent()
        ctx_id = "?"
        if parent is not None:
            grandparent = parent.getparent()
            if grandparent is not None:
                ctx_id = grandparent.get("id", "?")

        dim_qname = em.get("dimension", "")
        dim_resolved = _resolve_qname(dim_qname, nsmap)

        # Extract the dimension localname for matching.
        dim_ln = dim_resolved[1] if dim_resolved is not None else None

        # XML-071: is the dimension known?
        if dim_ln is None or dim_ln not in taxonomy.valid_dim_localnames:
            r.unknown_dimensions.append((ctx_id, dim_qname))
            continue  # can't validate member if dimension unknown

        # XML-072: is the member valid?
        # Skip open key dimensions — members are not enumerated.
        if dim_ln in taxonomy.open_key_localnames:
            continue

        member_text = (em.text or "").strip()
        if not member_text:
            continue
        member_resolved = _resolve_qname(member_text, nsmap)
        valid_members = taxonomy.dim_members.get(dim_ln, frozenset())
        if member_resolved is None or member_resolved not in valid_members:
            r.invalid_members.append((ctx_id, dim_qname, member_text))

    _last_scan = (rid, r)
    return r


def _get_scan(ctx: ValidationContext) -> Optional[_ScanResult]:
    """Return cached scan result, or None if prerequisites are missing."""
    root = ctx.xml_root
    module = ctx.module
    if root is None or module is None:
        return None
    taxonomy = _get_taxonomy(module, root.nsmap)
    return _scan(root, taxonomy)


# ---------------------------------------------------------------------------
# XML-070  Valid fact concepts
# ---------------------------------------------------------------------------


@rule_impl("XML-070")
def check_valid_concepts(ctx: ValidationContext) -> None:
    """All fact concepts MUST be defined in the taxonomy."""
    scan = _get_scan(ctx)
    if scan is None:
        return
    for localname in scan.unknown_concepts:
        ctx.add_finding(
            location=f"fact:{localname}",
            context={
                "detail": (
                    f"Concept '{localname}' is not defined in the taxonomy for this entry point."
                )
            },
        )


# ---------------------------------------------------------------------------
# XML-071  Valid explicit dimensions
# ---------------------------------------------------------------------------


@rule_impl("XML-071")
def check_valid_dimensions(ctx: ValidationContext) -> None:
    """All explicit dimension QNames MUST be defined in the taxonomy."""
    scan = _get_scan(ctx)
    if scan is None:
        return
    for ctx_id, dim_qname in scan.unknown_dimensions:
        ctx.add_finding(
            location=f"context:{ctx_id}",
            context={
                "detail": (
                    f"Dimension '{dim_qname}' in context '{ctx_id}' is not defined in the taxonomy."
                )
            },
        )


# ---------------------------------------------------------------------------
# XML-072  Valid dimension members
# ---------------------------------------------------------------------------


@rule_impl("XML-072")
def check_valid_members(ctx: ValidationContext) -> None:
    """All dimension member values MUST be valid for their dimension."""
    scan = _get_scan(ctx)
    if scan is None:
        return
    for ctx_id, dim_qname, member_qname in scan.invalid_members:
        ctx.add_finding(
            location=f"context:{ctx_id}",
            context={
                "detail": (
                    f"Member '{member_qname}' is not a valid value "
                    f"for dimension '{dim_qname}' in context '{ctx_id}'."
                )
            },
        )
