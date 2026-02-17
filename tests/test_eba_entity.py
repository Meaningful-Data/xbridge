"""Tests for EBA-ENTITY-001 and EBA-ENTITY-002: entity identifier checks."""

import importlib
import sys
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.eba_entity"

_NS = (
    'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    'xmlns:link="http://www.xbrl.org/2003/linkbase" '
    'xmlns:find="http://www.eurofiling.info/xbrl/ext/filing-indicators"'
)


def _xbrl(body: str = "") -> bytes:
    return f'<?xml version="1.0" encoding="utf-8"?><xbrli:xbrl {_NS}>{body}</xbrli:xbrl>'.encode()


def _context(
    scheme: str = "http://standards.iso.org/iso/17442",
    identifier: str = "529900T8BM49AURSDO55",
) -> str:
    return (
        '<xbrli:context id="c1">'
        "<xbrli:entity>"
        f'<xbrli:identifier scheme="{scheme}">{identifier}</xbrli:identifier>'
        "</xbrli:entity>"
        "<xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period>"
        "</xbrli:context>"
    )


def _run(xml_bytes: bytes, rule_id: str) -> list:
    with NamedTemporaryFile(suffix=".xbrl") as tmp:
        tmp.write(xml_bytes)
        tmp.flush()
        results = run_validation(tmp.name, eba=True)
    return [r for r in results if r.rule_id == rule_id]


def _ensure_registered() -> None:
    if ("EBA-ENTITY-001", "xml") not in _impl_registry:
        if _MOD in sys.modules:
            importlib.reload(sys.modules[_MOD])
        else:
            importlib.import_module(_MOD)


# ===================================================================
# EBA-ENTITY-001 — Accepted identifier schemes
# ===================================================================


class TestEBAEntity001Scheme:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_lei_scheme_no_findings(self) -> None:
        xml = _xbrl(_context(scheme="http://standards.iso.org/iso/17442"))
        assert _run(xml, "EBA-ENTITY-001") == []

    def test_qualified_scheme_no_findings(self) -> None:
        xml = _xbrl(_context(scheme="https://eurofiling.info/eu/rs", identifier="ABC123"))
        assert _run(xml, "EBA-ENTITY-001") == []

    def test_invalid_scheme_detected(self) -> None:
        xml = _xbrl(_context(scheme="http://example.com/bad"))
        findings = _run(xml, "EBA-ENTITY-001")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "example.com" in findings[0].message

    def test_empty_scheme_detected(self) -> None:
        xml = _xbrl(_context(scheme=""))
        findings = _run(xml, "EBA-ENTITY-001")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_no_contexts_no_findings(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-ENTITY-001") == []


# ===================================================================
# EBA-ENTITY-002 — Identifier value conventions
# ===================================================================


class TestEBAEntity002Value:
    def setup_method(self) -> None:
        _ensure_registered()

    # --- Valid LEI identifiers ---

    def test_valid_lei_20_chars(self) -> None:
        xml = _xbrl(_context(identifier="529900T8BM49AURSDO55"))
        assert _run(xml, "EBA-ENTITY-002") == []

    def test_valid_lei_with_con_suffix(self) -> None:
        xml = _xbrl(_context(identifier="529900T8BM49AURSDO55.CON"))
        assert _run(xml, "EBA-ENTITY-002") == []

    def test_valid_lei_with_ind_suffix(self) -> None:
        xml = _xbrl(_context(identifier="529900T8BM49AURSDO55.IND"))
        assert _run(xml, "EBA-ENTITY-002") == []

    def test_valid_lei_with_crdliqsubgrp_suffix(self) -> None:
        xml = _xbrl(_context(identifier="529900T8BM49AURSDO55.CRDLIQSUBGRP"))
        assert _run(xml, "EBA-ENTITY-002") == []

    # --- Invalid LEI identifiers ---

    def test_lei_too_short(self) -> None:
        xml = _xbrl(_context(identifier="ABCD1234.IND"))
        findings = _run(xml, "EBA-ENTITY-002")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "ABCD1234" in findings[0].message
        assert "20 alphanumeric" in findings[0].message

    def test_lei_too_long(self) -> None:
        xml = _xbrl(_context(identifier="A" * 21))
        findings = _run(xml, "EBA-ENTITY-002")
        assert len(findings) == 1

    def test_lei_with_invalid_chars(self) -> None:
        xml = _xbrl(_context(identifier="52990!T8BM49AURSDO55"))
        findings = _run(xml, "EBA-ENTITY-002")
        assert len(findings) == 1

    def test_lei_lowercase_rejected(self) -> None:
        xml = _xbrl(_context(identifier="529900t8bm49aursdo55"))
        findings = _run(xml, "EBA-ENTITY-002")
        assert len(findings) == 1

    def test_lei_unknown_suffix(self) -> None:
        xml = _xbrl(_context(identifier="529900T8BM49AURSDO55.UNKNOWN"))
        findings = _run(xml, "EBA-ENTITY-002")
        assert len(findings) == 1
        assert ".UNKNOWN" in findings[0].message

    def test_empty_identifier(self) -> None:
        xml = _xbrl(_context(identifier=""))
        findings = _run(xml, "EBA-ENTITY-002")
        assert len(findings) == 1
        assert "empty" in findings[0].message.lower()

    # --- Qualified scheme — less strict ---

    def test_qualified_scheme_any_value_accepted(self) -> None:
        xml = _xbrl(_context(scheme="https://eurofiling.info/eu/rs", identifier="ABC"))
        assert _run(xml, "EBA-ENTITY-002") == []

    def test_qualified_scheme_empty_value_rejected(self) -> None:
        xml = _xbrl(_context(scheme="https://eurofiling.info/eu/rs", identifier=""))
        findings = _run(xml, "EBA-ENTITY-002")
        assert len(findings) == 1

    # --- Edge cases ---

    def test_no_contexts_no_findings(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-ENTITY-002") == []

    def test_unknown_scheme_value_not_checked(self) -> None:
        """If the scheme is unknown (EBA-ENTITY-001 handles it), don't also flag the value."""
        xml = _xbrl(_context(scheme="http://bad.scheme", identifier="short"))
        assert _run(xml, "EBA-ENTITY-002") == []
