"""Tests for XML-073..XML-074: fact values against the data type of their concept."""

import importlib
import sys
from pathlib import Path

from lxml import etree

from xbridge.modules import Module, Table, Variable
from xbridge.validation._context import ValidationContext
from xbridge.validation._models import RuleDefinition, Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.xml_datatypes"

_NS = (
    'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
    'xmlns:eba_met="http://www.eba.europa.eu/xbrl/crr/dict/met" '
    'xmlns:met42="http://www.eba.europa.eu/xbrl/crr/dict/met/4.2" '
    'xmlns:eba_AS="http://www.eba.europa.eu/xbrl/crr/dict/dom/AS" '
    'xmlns:as_alias="http://www.eba.europa.eu/xbrl/crr/dict/dom/AS" '
    'xmlns:eg="http://example.com/facts"'
)

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
        ("XML-073", "Fact values MUST be valid for the data type of their concept: {detail}"),
        ("XML-074", "Enumeration fact values MUST be allowed values for their concept: {detail}"),
    ]
}


def _ensure_registered() -> None:
    if ("XML-073", None) not in _impl_registry:
        if _MOD in sys.modules:
            importlib.reload(sys.modules[_MOD])
        else:
            importlib.import_module(_MOD)


def _variable(code: str, concept: str, allowed: list[str] | None = None) -> Variable:
    var = Variable(code=code, dimensions={"concept": concept})
    var._allowed_values = allowed or []
    return var


def _module(variables: list[Variable] | None = None) -> Module:
    table = Table(
        code="T_01.00",
        url="t_01.00.csv",
        filing_indicator="T_01.00",
        open_keys=[],
        variables=variables or [],
        architecture="datapoints",
        columns=[],
    )
    module = Module.__new__(Module)
    module.code = "test_module"
    module.url = "http://test/a/b/c/d/e/f/g/h/i/j/k/l"
    module._tables = [table]
    return module


def _fact(concept: str, value: str, attrs: str = 'contextRef="c1"') -> str:
    return f"<{concept} {attrs}>{value}</{concept}>"


def _parse(body: str) -> etree._Element:
    xml = f'<?xml version="1.0" encoding="utf-8"?><xbrli:xbrl {_NS}>{body}</xbrli:xbrl>'
    return etree.fromstring(xml.encode())


def _run(rule_id: str, body: str, module: Module | None = None) -> list:
    _ensure_registered()
    ctx = ValidationContext(
        rule_set="xml",
        rule_definition=_RULE_DEFS[rule_id],
        file_path=Path("test.xbrl"),
        raw_bytes=b"",
        module=module,
        xml_root=_parse(body),
    )
    _impl_registry[(rule_id, None)](ctx)
    return ctx.findings


_ENUM_MODULE_VARS = [
    _variable("dp1", "eba_met:ei4", ["eba_AS:x1", "eba_AS:x2"]),
    _variable("dp2", "eba_met:ei4", ["eba_AS:x3"]),
]


class TestXML073FactValueTypes:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_values_no_findings(self) -> None:
        body = "".join(
            [
                _fact("eba_met:mi76", "1234.56", 'contextRef="c1" unitRef="u1" decimals="2"'),
                _fact("eba_met:pi1033", "0.25", 'contextRef="c1" unitRef="u2" decimals="4"'),
                _fact("eba_met:qCTE", "12", 'contextRef="c1" unitRef="u2" decimals="0"'),
                _fact("eba_met:bi137", "false"),
                _fact("eba_met:RDT", "2024-12-31"),
                _fact("eba_met:qAMI", "true"),
                _fact("eba_met:si1036", "free text"),
                _fact("eba_met:ei4", "eba_AS:x1"),
            ]
        )
        assert _run("XML-073", body) == []

    def test_invalid_monetary_value(self) -> None:
        body = _fact("eba_met:mi76", "1,234", 'contextRef="c9" unitRef="u1" decimals="2"')
        findings = _run("XML-073", body)
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].location == "fact:eba_met:mi76:context:c9"
        assert "'1,234'" in findings[0].message
        assert "xbrli:monetaryItemType" in findings[0].message

    def test_each_type_reported(self) -> None:
        body = "".join(
            [
                _fact("eba_met:qCTE", "1.5", 'contextRef="c1" unitRef="u2" decimals="0"'),
                _fact("eba_met:bi137", "yes"),
                _fact("eba_met:RDT", "2024-02-30"),
                _fact("eba_met:qAMI", "false"),
                _fact("eba_met:ei4", "not a qname"),
            ]
        )
        messages = [f.message for f in _run("XML-073", body)]
        assert len(messages) == 5
        assert "an integer" in messages[0]
        assert "a boolean" in messages[1]
        assert "a valid date" in messages[2]
        assert "the value 'true'" in messages[3]
        assert "a QName" in messages[4]

    def test_versioned_metric_namespace(self) -> None:
        body = _fact("met42:qBLH", "bad value")
        findings = _run("XML-073", body)
        assert len(findings) == 1
        assert "eba_met_4.2:qBLH" in findings[0].message

    def test_enumeration_with_undeclared_prefix(self) -> None:
        findings = _run("XML-073", _fact("eba_met:ei4", "nope:x1"))
        assert len(findings) == 1
        assert "undeclared namespace prefix 'nope'" in findings[0].message

    def test_nil_facts_skipped(self) -> None:
        body = _fact("eba_met:mi76", "", 'contextRef="c1" unitRef="u1" xsi:nil="true"')
        assert _run("XML-073", body) == []

    def test_unknown_concepts_skipped(self) -> None:
        body = _fact("eg:amount", "abc") + _fact("eba_met:notAMetric", "abc")
        assert _run("XML-073", body) == []

    def test_whitespace_collapsed_for_numbers(self) -> None:
        body = _fact("eba_met:mi76", "\n  100\n", 'contextRef="c1" unitRef="u1" decimals="0"')
        assert _run("XML-073", body) == []

    def test_works_without_module(self) -> None:
        assert len(_run("XML-073", _fact("eba_met:bi137", "maybe"), module=None)) == 1


class TestXML074EnumerationValues:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_allowed_value_no_findings(self) -> None:
        module = _module(_ENUM_MODULE_VARS)
        body = _fact("eba_met:ei4", "eba_AS:x1") + _fact("eba_met:ei4", "eba_AS:x3")
        assert _run("XML-074", body, module) == []

    def test_allowed_value_with_other_prefix(self) -> None:
        """Values are compared by namespace, not by the prefix used in the instance."""
        module = _module(_ENUM_MODULE_VARS)
        assert _run("XML-074", _fact("eba_met:ei4", "as_alias:x2"), module) == []

    def test_disallowed_value(self) -> None:
        module = _module(_ENUM_MODULE_VARS)
        findings = _run("XML-074", _fact("eba_met:ei4", "eba_AS:x99", 'contextRef="c7"'), module)
        assert len(findings) == 1
        assert findings[0].location == "fact:eba_met:ei4:context:c7"
        assert "not an allowed value" in findings[0].message

    def test_concept_with_unrestricted_datapoint_skipped(self) -> None:
        module = _module([*_ENUM_MODULE_VARS, _variable("dp3", "eba_met:ei4")])
        assert _run("XML-074", _fact("eba_met:ei4", "eba_AS:x99"), module) == []

    def test_lexically_invalid_value_not_reported_twice(self) -> None:
        module = _module(_ENUM_MODULE_VARS)
        assert _run("XML-074", _fact("eba_met:ei4", "not a qname"), module) == []

    def test_no_module_no_findings(self) -> None:
        assert _run("XML-074", _fact("eba_met:ei4", "eba_AS:x99"), module=None) == []
