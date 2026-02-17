"""Tests for XML-070..XML-072: taxonomy conformance checks."""

import importlib
import sys
from pathlib import Path

from lxml import etree

from xbridge.modules import Module, Table, Variable
from xbridge.validation._context import ValidationContext
from xbridge.validation._models import RuleDefinition, Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.xml_taxonomy"

# --- Namespace declarations for test XML ----------------------------------

_NS = (
    'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    'xmlns:link="http://www.xbrl.org/2003/linkbase" '
    'xmlns:find="http://www.eurofiling.info/xbrl/ext/filing-indicators" '
    'xmlns:xbrldi="http://xbrl.org/2006/xbrldi" '
    'xmlns:eba_met="http://www.eba.europa.eu/xbrl/crr/dict/met" '
    'xmlns:eba_dim="http://www.eba.europa.eu/xbrl/crr/dict/dim" '
    'xmlns:eba_BA="http://www.eba.europa.eu/xbrl/crr/dict/dom/BA" '
    'xmlns:eba_MC="http://www.eba.europa.eu/xbrl/crr/dict/dom/MC" '
    'xmlns:iso4217="http://www.xbrl.org/2003/iso4217" '
    'xmlns:eg="http://example.com/facts" '
    'xmlns:eg_dim="http://example.com/dim" '
    'xmlns:eg_dom="http://example.com/dom"'
)


# --- Rule definitions for direct context construction ---------------------

_RULE_DEFS = {
    code: RuleDefinition(
        code=code,
        message=msg,
        severity=Severity.ERROR,
        xml=True,
        csv=False,
        eba=False,
        post_conversion=False,
        eba_ref=None,
    )
    for code, msg in [
        ("XML-070", "All fact concepts MUST be defined in the taxonomy: {detail}"),
        ("XML-071", "All explicit dimension QNames MUST be defined in the taxonomy: {detail}"),
        ("XML-072", "All dimension member values MUST be valid for their dimension: {detail}"),
    ]
}


# --- Helpers ---------------------------------------------------------------


def _ensure_registered() -> None:
    """Re-registration guard shared by all test classes."""
    if ("XML-070", None) not in _impl_registry:
        if _MOD in sys.modules:
            importlib.reload(sys.modules[_MOD])
        else:
            importlib.import_module(_MOD)


def _make_module(
    variables: list[Variable] | None = None,
    open_keys: list[str] | None = None,
    architecture: str = "datapoints",
    columns: list[dict] | None = None,
) -> Module:
    """Build a minimal Module with one table for testing."""
    table = Table(
        code="T_01.00",
        url="http://example.com/table",
        filing_indicator="T_01.00",
        open_keys=open_keys or [],
        variables=variables or [],
        architecture=architecture,
        columns=columns or [],
    )
    module = Module.__new__(Module)
    module.code = "test_module"
    module.url = "http://test/a/b/c/d/e/f/g/h/i/j/k/l"
    module._tables = [table]
    return module


def _make_variable(dims: dict[str, str]) -> Variable:
    """Build a Variable with given dimensions dict."""
    return Variable(code="v1", dimensions=dims)


def _parse(body: str = "") -> etree._Element:
    """Parse an xbrli:xbrl document and return root."""
    xml = f'<?xml version="1.0" encoding="utf-8"?><xbrli:xbrl {_NS}>{body}</xbrli:xbrl>'
    return etree.fromstring(xml.encode())


def _context_with_dim(
    ctx_id: str = "c1",
    dimension: str = "eba_dim:BAS",
    member: str = "eba_BA:x17",
) -> str:
    """Build a context with an explicit dimension member in xbrli:scenario."""
    return (
        f'<xbrli:context id="{ctx_id}">'
        "<xbrli:entity>"
        '<xbrli:identifier scheme="http://standards.iso.org/iso/17442">LEI</xbrli:identifier>'
        "</xbrli:entity>"
        "<xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period>"
        "<xbrli:scenario>"
        f'<xbrldi:explicitMember dimension="{dimension}">{member}</xbrldi:explicitMember>'
        "</xbrli:scenario>"
        "</xbrli:context>"
    )


def _plain_context(ctx_id: str = "c1") -> str:
    """Build a plain context without scenario."""
    return (
        f'<xbrli:context id="{ctx_id}">'
        "<xbrli:entity>"
        '<xbrli:identifier scheme="http://standards.iso.org/iso/17442">LEI</xbrli:identifier>'
        "</xbrli:entity>"
        "<xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period>"
        "</xbrli:context>"
    )


def _run_rule(rule_id: str, root: etree._Element, module: Module) -> list:
    """Execute a single taxonomy rule and return findings."""
    _ensure_registered()

    # Clear caches to ensure fresh scan per test.
    import xbridge.validation.rules.xml_taxonomy as mod

    mod._last_taxonomy = None
    mod._last_scan = None

    rule_def = _RULE_DEFS[rule_id]
    ctx = ValidationContext(
        rule_set="xml",
        rule_definition=rule_def,
        file_path=Path("test.xbrl"),
        raw_bytes=b"",
        module=module,
        xml_root=root,
    )
    impl = _impl_registry[(rule_id, None)]
    impl(ctx)
    return ctx.findings


# ===========================================================================
# XML-070 — Valid fact concepts
# ===========================================================================


class TestXML070ValidConcepts:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_known_concept_no_findings(self) -> None:
        module = _make_module(
            variables=[
                _make_variable({"concept": "eba_met:ei4"}),
            ]
        )
        root = _parse(
            _plain_context() + '<eba_met:ei4 contextRef="c1" decimals="2">100</eba_met:ei4>'
        )
        assert _run_rule("XML-070", root, module) == []

    def test_unknown_concept_detected(self) -> None:
        module = _make_module(
            variables=[
                _make_variable({"concept": "eba_met:ei4"}),
            ]
        )
        root = _parse(
            _plain_context()
            + '<eba_met:unknown_concept contextRef="c1" decimals="2">100</eba_met:unknown_concept>'
        )
        findings = _run_rule("XML-070", root, module)
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "unknown_concept" in findings[0].message

    def test_multiple_unknown_concepts(self) -> None:
        module = _make_module(
            variables=[
                _make_variable({"concept": "eba_met:ei4"}),
            ]
        )
        root = _parse(
            _plain_context()
            + '<eba_met:badA contextRef="c1" decimals="2">1</eba_met:badA>'
            + '<eba_met:badB contextRef="c1" decimals="2">2</eba_met:badB>'
        )
        findings = _run_rule("XML-070", root, module)
        assert len(findings) == 2

    def test_infrastructure_ns_children_ignored(self) -> None:
        """Children in xbrli/link/find namespaces are not facts."""
        module = _make_module(
            variables=[
                _make_variable({"concept": "eba_met:ei4"}),
            ]
        )
        # xbrli:context, link:schemaRef, find:fIndicators are infra — not checked.
        root = _parse(_plain_context())
        assert _run_rule("XML-070", root, module) == []

    def test_multiple_variables_valid(self) -> None:
        module = _make_module(
            variables=[
                _make_variable({"concept": "eba_met:ei4"}),
                _make_variable({"concept": "eba_met:mi64"}),
            ]
        )
        root = _parse(
            _plain_context()
            + '<eba_met:ei4 contextRef="c1" decimals="2">100</eba_met:ei4>'
            + '<eba_met:mi64 contextRef="c1" decimals="2">200</eba_met:mi64>'
        )
        assert _run_rule("XML-070", root, module) == []

    def test_no_module_returns_no_findings(self) -> None:
        """When module is None, rules silently skip."""
        _ensure_registered()
        import xbridge.validation.rules.xml_taxonomy as mod

        mod._last_taxonomy = None
        mod._last_scan = None

        root = _parse(
            _plain_context() + '<eba_met:whatever contextRef="c1" decimals="2">1</eba_met:whatever>'
        )
        rule_def = _RULE_DEFS["XML-070"]
        ctx = ValidationContext(
            rule_set="xml",
            rule_definition=rule_def,
            file_path=Path("test.xbrl"),
            raw_bytes=b"",
            module=None,
            xml_root=root,
        )
        impl = _impl_registry[("XML-070", None)]
        impl(ctx)
        assert ctx.findings == []

    def test_headers_architecture_concepts(self) -> None:
        """Concepts from headers-architecture columns are valid."""
        module = _make_module(
            architecture="headers",
            columns=[
                {"variable_id": "v1", "dimensions": {"concept": "eba_met:ei4"}},
                {"variable_id": "v2", "dimensions": {"concept": "eba_met:mi64"}},
            ],
        )
        root = _parse(
            _plain_context()
            + '<eba_met:ei4 contextRef="c1" decimals="2">100</eba_met:ei4>'
            + '<eba_met:mi64 contextRef="c1" decimals="2">200</eba_met:mi64>'
        )
        assert _run_rule("XML-070", root, module) == []

    def test_headers_architecture_unknown_concept(self) -> None:
        module = _make_module(
            architecture="headers",
            columns=[
                {"variable_id": "v1", "dimensions": {"concept": "eba_met:ei4"}},
            ],
        )
        root = _parse(
            _plain_context() + '<eba_met:unknown contextRef="c1" decimals="2">1</eba_met:unknown>'
        )
        findings = _run_rule("XML-070", root, module)
        assert len(findings) == 1
        assert "unknown" in findings[0].message


# ===========================================================================
# XML-071 — Valid explicit dimensions
# ===========================================================================


class TestXML071ValidDimensions:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_known_dimension_prefixed_key(self) -> None:
        """Dimension key with prefix (raw taxonomy path)."""
        module = _make_module(
            variables=[
                _make_variable(
                    {
                        "concept": "eba_met:ei4",
                        "eba_dim:BAS": "eba_BA:x17",
                    }
                ),
            ]
        )
        root = _parse(
            _context_with_dim("c1", "eba_dim:BAS", "eba_BA:x17")
            + '<eba_met:ei4 contextRef="c1" decimals="2">100</eba_met:ei4>'
        )
        assert _run_rule("XML-071", root, module) == []

    def test_known_dimension_bare_localname_key(self) -> None:
        """Dimension key as bare localname (from_dict / deserialized path)."""
        module = _make_module(
            variables=[
                _make_variable(
                    {
                        "concept": "eba_met:ei4",
                        "BAS": "eba_BA:x17",
                    }
                ),
            ]
        )
        root = _parse(
            _context_with_dim("c1", "eba_dim:BAS", "eba_BA:x17")
            + '<eba_met:ei4 contextRef="c1" decimals="2">100</eba_met:ei4>'
        )
        assert _run_rule("XML-071", root, module) == []

    def test_unknown_dimension_detected(self) -> None:
        module = _make_module(
            variables=[
                _make_variable(
                    {
                        "concept": "eba_met:ei4",
                        "BAS": "eba_BA:x17",
                    }
                ),
            ]
        )
        root = _parse(
            _context_with_dim("c1", "eg_dim:UNKNOWN", "eg_dom:val")
            + '<eba_met:ei4 contextRef="c1" decimals="2">100</eba_met:ei4>'
        )
        findings = _run_rule("XML-071", root, module)
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "eg_dim:UNKNOWN" in findings[0].message
        assert findings[0].location == "context:c1"

    def test_multiple_unknown_dimensions(self) -> None:
        module = _make_module(
            variables=[
                _make_variable({"concept": "eba_met:ei4"}),
            ]
        )
        dim1 = _context_with_dim("c1", "eg_dim:A", "eg_dom:v1")
        dim2 = _context_with_dim("c2", "eg_dim:B", "eg_dom:v2")
        root = _parse(
            dim1
            + dim2
            + '<eba_met:ei4 contextRef="c1" decimals="2">1</eba_met:ei4>'
            + '<eba_met:ei4 contextRef="c2" decimals="2">2</eba_met:ei4>'
        )
        findings = _run_rule("XML-071", root, module)
        assert len(findings) == 2

    def test_open_key_dimension_accepted(self) -> None:
        """Open key dimensions are valid even if not in variable dimensions."""
        module = _make_module(
            variables=[
                _make_variable(
                    {
                        "concept": "eba_met:ei4",
                        "BAS": "eba_BA:x17",
                    }
                ),
            ],
            open_keys=["CUS"],
        )
        root = _parse(
            _context_with_dim("c1", "eba_dim:CUS", "eba_BA:something")
            + '<eba_met:ei4 contextRef="c1" decimals="2">100</eba_met:ei4>'
        )
        assert _run_rule("XML-071", root, module) == []

    def test_no_explicit_members_no_findings(self) -> None:
        """Contexts without explicit dimensions don't trigger."""
        module = _make_module(
            variables=[
                _make_variable({"concept": "eba_met:ei4"}),
            ]
        )
        root = _parse(
            _plain_context() + '<eba_met:ei4 contextRef="c1" decimals="2">100</eba_met:ei4>'
        )
        assert _run_rule("XML-071", root, module) == []


# ===========================================================================
# XML-072 — Valid dimension members
# ===========================================================================


class TestXML072ValidMembers:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_member_no_findings(self) -> None:
        """Bare localname keys (deserialized modules)."""
        module = _make_module(
            variables=[
                _make_variable(
                    {
                        "concept": "eba_met:ei4",
                        "BAS": "eba_BA:x17",
                    }
                ),
            ]
        )
        root = _parse(
            _context_with_dim("c1", "eba_dim:BAS", "eba_BA:x17")
            + '<eba_met:ei4 contextRef="c1" decimals="2">100</eba_met:ei4>'
        )
        assert _run_rule("XML-072", root, module) == []

    def test_invalid_member_detected(self) -> None:
        module = _make_module(
            variables=[
                _make_variable(
                    {
                        "concept": "eba_met:ei4",
                        "BAS": "eba_BA:x17",
                    }
                ),
            ]
        )
        root = _parse(
            _context_with_dim("c1", "eba_dim:BAS", "eba_BA:WRONG")
            + '<eba_met:ei4 contextRef="c1" decimals="2">100</eba_met:ei4>'
        )
        findings = _run_rule("XML-072", root, module)
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "eba_BA:WRONG" in findings[0].message
        assert "eba_dim:BAS" in findings[0].message
        assert findings[0].location == "context:c1"

    def test_multiple_valid_members_same_dimension(self) -> None:
        """Different variables can contribute different valid members for the same dimension."""
        module = _make_module(
            variables=[
                _make_variable(
                    {
                        "concept": "eba_met:ei4",
                        "BAS": "eba_BA:x17",
                    }
                ),
                _make_variable(
                    {
                        "concept": "eba_met:mi64",
                        "BAS": "eba_BA:x1",
                    }
                ),
            ]
        )
        root = _parse(
            _context_with_dim("c1", "eba_dim:BAS", "eba_BA:x17")
            + _context_with_dim("c2", "eba_dim:BAS", "eba_BA:x1")
            + '<eba_met:ei4 contextRef="c1" decimals="2">100</eba_met:ei4>'
            + '<eba_met:mi64 contextRef="c2" decimals="2">200</eba_met:mi64>'
        )
        assert _run_rule("XML-072", root, module) == []

    def test_open_key_member_not_checked(self) -> None:
        """Open key dimensions skip member validation."""
        module = _make_module(
            variables=[
                _make_variable(
                    {
                        "concept": "eba_met:ei4",
                        "BAS": "eba_BA:x17",
                    }
                ),
            ],
            open_keys=["CUS"],
        )
        # CUS is open key — any member should be accepted without checking.
        root = _parse(
            _context_with_dim("c1", "eba_dim:CUS", "eba_BA:anything")
            + '<eba_met:ei4 contextRef="c1" decimals="2">100</eba_met:ei4>'
        )
        assert _run_rule("XML-072", root, module) == []

    def test_unknown_dimension_skips_member_check(self) -> None:
        """When the dimension itself is unknown, XML-072 should not trigger (XML-071 handles it)."""
        module = _make_module(
            variables=[
                _make_variable({"concept": "eba_met:ei4"}),
            ]
        )
        root = _parse(
            _context_with_dim("c1", "eg_dim:UNKNOWN", "eg_dom:val")
            + '<eba_met:ei4 contextRef="c1" decimals="2">100</eba_met:ei4>'
        )
        # XML-071 would report this, but XML-072 should not.
        findings = _run_rule("XML-072", root, module)
        assert findings == []

    def test_empty_member_text_skipped(self) -> None:
        """Empty member text should not trigger a finding."""
        module = _make_module(
            variables=[
                _make_variable(
                    {
                        "concept": "eba_met:ei4",
                        "BAS": "eba_BA:x17",
                    }
                ),
            ]
        )
        root = _parse(
            '<xbrli:context id="c1">'
            "<xbrli:entity>"
            '<xbrli:identifier scheme="http://standards.iso.org/iso/17442">LEI</xbrli:identifier>'
            "</xbrli:entity>"
            "<xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period>"
            "<xbrli:scenario>"
            '<xbrldi:explicitMember dimension="eba_dim:BAS"></xbrldi:explicitMember>'
            "</xbrli:scenario>"
            "</xbrli:context>" + '<eba_met:ei4 contextRef="c1" decimals="2">100</eba_met:ei4>'
        )
        assert _run_rule("XML-072", root, module) == []

    def test_headers_architecture_members(self) -> None:
        """Members from headers-architecture columns are valid."""
        module = _make_module(
            architecture="headers",
            columns=[
                {
                    "variable_id": "v1",
                    "dimensions": {
                        "concept": "eba_met:ei4",
                        "eba_dim:BAS": "eba_BA:x17",
                    },
                },
            ],
        )
        root = _parse(
            _context_with_dim("c1", "eba_dim:BAS", "eba_BA:x17")
            + '<eba_met:ei4 contextRef="c1" decimals="2">100</eba_met:ei4>'
        )
        assert _run_rule("XML-072", root, module) == []

    def test_headers_architecture_invalid_member(self) -> None:
        module = _make_module(
            architecture="headers",
            columns=[
                {
                    "variable_id": "v1",
                    "dimensions": {
                        "concept": "eba_met:ei4",
                        "eba_dim:BAS": "eba_BA:x17",
                    },
                },
            ],
        )
        root = _parse(
            _context_with_dim("c1", "eba_dim:BAS", "eba_BA:WRONG")
            + '<eba_met:ei4 contextRef="c1" decimals="2">100</eba_met:ei4>'
        )
        findings = _run_rule("XML-072", root, module)
        assert len(findings) == 1
        assert "WRONG" in findings[0].message
