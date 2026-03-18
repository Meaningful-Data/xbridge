"""Tests for XML-030..XML-035: context structure checks."""

import importlib
import sys
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.xml_context"

_NS = (
    'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    'xmlns:xbrldi="http://xbrl.org/2006/xbrldi" '
    'xmlns:find="http://www.eurofiling.info/xbrl/ext/filing-indicators"'
)


def _xbrl(body: str = "") -> bytes:
    """Build a minimal xbrli:xbrl document."""
    return (f'<?xml version="1.0" encoding="utf-8"?><xbrli:xbrl {_NS}>{body}</xbrli:xbrl>').encode()


def _context(
    ctx_id: str = "c1",
    period: str = "<xbrli:instant>2024-12-31</xbrli:instant>",
    scheme: str = "http://standards.iso.org/iso/17442",
    identifier: str = "LEICODE",
    extra: str = "",
) -> str:
    """Build an xbrli:context element with configurable parts."""
    return (
        f'<xbrli:context id="{ctx_id}">'
        f"<xbrli:entity>"
        f'<xbrli:identifier scheme="{scheme}">{identifier}</xbrli:identifier>'
        f"</xbrli:entity>"
        f"<xbrli:period>{period}</xbrli:period>"
        f"{extra}"
        f"</xbrli:context>"
    )


def _valid_instance() -> bytes:
    """A valid instance with one context and filing indicators."""
    ctx = _context("c1")
    indicators = (
        "<find:fIndicators>"
        '<find:filingIndicator contextRef="c1">R_01.00</find:filingIndicator>'
        "</find:fIndicators>"
    )
    return _xbrl(ctx + indicators)


def _ensure_registered() -> None:
    """Ensure all rule implementations in the module are registered."""
    if ("XML-030", None) not in _impl_registry:
        if _MOD in sys.modules:
            importlib.reload(sys.modules[_MOD])
        else:
            importlib.import_module(_MOD)


# ---------------------------------------------------------------------------
# XML-030: Period date elements must be xs:date
# ---------------------------------------------------------------------------


class TestXML030PeriodDateFormat:
    """Tests for the XML-030 rule implementation."""

    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_date_no_findings(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_valid_instance())
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-030"]
        assert findings == []

    def test_datetime_detected(self) -> None:
        """A dateTime value triggers a finding."""
        body = _context(period="<xbrli:instant>2024-12-31T00:00:00</xbrli:instant>")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-030"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "T00:00:00" in findings[0].message

    def test_timezone_offset_detected(self) -> None:
        """A date with timezone offset triggers a finding."""
        body = _context(period="<xbrli:instant>2024-12-31+01:00</xbrli:instant>")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-030"]
        assert len(findings) == 1
        assert "+01:00" in findings[0].message

    def test_z_suffix_detected(self) -> None:
        """A date with Z timezone triggers a finding."""
        body = _context(period="<xbrli:instant>2024-12-31Z</xbrli:instant>")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-030"]
        assert len(findings) == 1
        assert "Z" in findings[0].message

    def test_duration_dates_also_checked(self) -> None:
        """StartDate and endDate are also validated for format."""
        body = _context(
            period=(
                "<xbrli:startDate>2024-01-01T00:00:00</xbrli:startDate>"
                "<xbrli:endDate>2024-12-31</xbrli:endDate>"
            )
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-030"]
        assert len(findings) == 1
        assert "startDate" in findings[0].location

    def test_multiple_bad_dates_multiple_findings(self) -> None:
        """Each bad date element gets its own finding."""
        body = _context(
            "c1",
            period="<xbrli:instant>2024-12-31T00:00:00</xbrli:instant>",
        ) + _context(
            "c2",
            period="<xbrli:instant>2024-06-30Z</xbrli:instant>",
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-030"]
        assert len(findings) == 2

    def test_empty_date_text_detected(self) -> None:
        """An empty instant text is not a valid xs:date."""
        body = _context(period="<xbrli:instant></xbrli:instant>")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-030"]
        assert len(findings) == 1

    def test_location_contains_context_id(self) -> None:
        body = _context(
            "ctx_7",
            period="<xbrli:instant>2024-12-31T12:00:00</xbrli:instant>",
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-030"]
        assert len(findings) == 1
        assert "ctx_7" in findings[0].location
        assert "instant" in findings[0].location

    def test_malformed_xml_skipped(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"not xml")
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-030"]
        assert findings == []

    def test_eba_false_skips(self) -> None:
        body = _context(period="<xbrli:instant>2024-12-31T00:00:00</xbrli:instant>")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=False)
        findings = [r for r in results if r.rule_id == "XML-030"]
        assert findings == []


# ---------------------------------------------------------------------------
# XML-031: All periods must be instants
# ---------------------------------------------------------------------------


class TestXML031PeriodsAreInstants:
    """Tests for the XML-031 rule implementation."""

    def setup_method(self) -> None:
        _ensure_registered()

    def test_instant_period_no_findings(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_valid_instance())
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-031"]
        assert findings == []

    def test_duration_period_detected(self) -> None:
        body = _context(
            period=(
                "<xbrli:startDate>2024-01-01</xbrli:startDate>"
                "<xbrli:endDate>2024-12-31</xbrli:endDate>"
            )
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-031"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "duration" in findings[0].message

    def test_start_date_only_detected(self) -> None:
        """Even just startDate alone triggers the finding."""
        body = _context(period="<xbrli:startDate>2024-01-01</xbrli:startDate>")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-031"]
        assert len(findings) == 1

    def test_multiple_duration_contexts(self) -> None:
        """Each duration context gets its own finding."""
        body = _context(
            "c1",
            period=(
                "<xbrli:startDate>2024-01-01</xbrli:startDate>"
                "<xbrli:endDate>2024-12-31</xbrli:endDate>"
            ),
        ) + _context(
            "c2",
            period=(
                "<xbrli:startDate>2023-01-01</xbrli:startDate>"
                "<xbrli:endDate>2023-12-31</xbrli:endDate>"
            ),
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-031"]
        assert len(findings) == 2

    def test_location_has_context_id(self) -> None:
        body = _context(
            "ctx_dur",
            period=(
                "<xbrli:startDate>2024-01-01</xbrli:startDate>"
                "<xbrli:endDate>2024-12-31</xbrli:endDate>"
            ),
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-031"]
        assert len(findings) == 1
        assert "ctx_dur" in findings[0].location

    def test_malformed_xml_skipped(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"not xml")
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-031"]
        assert findings == []

    def test_eba_false_skips(self) -> None:
        body = _context(
            period=(
                "<xbrli:startDate>2024-01-01</xbrli:startDate>"
                "<xbrli:endDate>2024-12-31</xbrli:endDate>"
            )
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=False)
        findings = [r for r in results if r.rule_id == "XML-031"]
        assert findings == []


# ---------------------------------------------------------------------------
# XML-032: All periods must refer to the same reference date
# ---------------------------------------------------------------------------


class TestXML032SingleReferenceDate:
    """Tests for the XML-032 rule implementation."""

    def setup_method(self) -> None:
        _ensure_registered()

    def test_same_dates_no_findings(self) -> None:
        body = _context("c1") + _context("c2")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-032"]
        assert findings == []

    def test_different_dates_detected(self) -> None:
        body = _context("c1", period="<xbrli:instant>2024-12-31</xbrli:instant>") + _context(
            "c2", period="<xbrli:instant>2024-06-30</xbrli:instant>"
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-032"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "2024-12-31" in findings[0].message
        assert "2024-06-30" in findings[0].message

    def test_three_different_dates(self) -> None:
        """All distinct dates are listed in the finding."""
        body = (
            _context("c1", period="<xbrli:instant>2024-12-31</xbrli:instant>")
            + _context("c2", period="<xbrli:instant>2024-06-30</xbrli:instant>")
            + _context("c3", period="<xbrli:instant>2023-12-31</xbrli:instant>")
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-032"]
        assert len(findings) == 1
        assert "2023-12-31" in findings[0].message
        assert "2024-06-30" in findings[0].message
        assert "2024-12-31" in findings[0].message

    def test_single_context_no_findings(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_valid_instance())
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-032"]
        assert findings == []

    def test_no_contexts_no_findings(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl())
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-032"]
        assert findings == []

    def test_malformed_xml_skipped(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"not xml")
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-032"]
        assert findings == []

    def test_eba_false_skips(self) -> None:
        body = _context("c1", period="<xbrli:instant>2024-12-31</xbrli:instant>") + _context(
            "c2", period="<xbrli:instant>2024-06-30</xbrli:instant>"
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=False)
        findings = [r for r in results if r.rule_id == "XML-032"]
        assert findings == []


# ---------------------------------------------------------------------------
# XML-033: Identical entity identifiers across contexts
# ---------------------------------------------------------------------------


class TestXML033IdenticalIdentifiers:
    """Tests for the XML-033 rule implementation."""

    def setup_method(self) -> None:
        _ensure_registered()

    def test_same_identifiers_no_findings(self) -> None:
        body = _context("c1") + _context("c2")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-033"]
        assert findings == []

    def test_different_identifier_values(self) -> None:
        body = _context("c1", identifier="LEI_AAA") + _context("c2", identifier="LEI_BBB")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-033"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "LEI_AAA" in findings[0].message
        assert "LEI_BBB" in findings[0].message

    def test_different_schemes(self) -> None:
        body = _context("c1", scheme="http://standards.iso.org/iso/17442") + _context(
            "c2", scheme="https://eurofiling.info/eu/rs"
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-033"]
        assert len(findings) == 1
        assert "scheme=" in findings[0].message

    def test_single_context_no_findings(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_valid_instance())
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-033"]
        assert findings == []

    def test_three_contexts_same_id(self) -> None:
        body = _context("c1") + _context("c2") + _context("c3")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-033"]
        assert findings == []

    def test_malformed_xml_skipped(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"not xml")
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-033"]
        assert findings == []

    def test_eba_false_skips(self) -> None:
        body = _context("c1", identifier="LEI_AAA") + _context("c2", identifier="LEI_BBB")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=False)
        findings = [r for r in results if r.rule_id == "XML-033"]
        assert findings == []


# ---------------------------------------------------------------------------
# XML-034: xbrli:segment must not be used
# ---------------------------------------------------------------------------


class TestXML034NoSegments:
    """Tests for the XML-034 rule implementation."""

    def setup_method(self) -> None:
        _ensure_registered()

    def test_no_segment_no_findings(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_valid_instance())
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-034"]
        assert findings == []

    def test_segment_detected(self) -> None:
        body = _context(
            "c1",
            extra="",
        ).replace(
            "</xbrli:entity>",
            "<xbrli:segment><xbrldi:explicitMember>d:v</xbrldi:explicitMember></xbrli:segment>"
            "</xbrli:entity>",
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-034"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "segment" in findings[0].message

    def test_multiple_contexts_with_segments(self) -> None:
        """Each context with a segment gets its own finding."""
        c1 = _context("c1").replace(
            "</xbrli:entity>",
            "<xbrli:segment/></xbrli:entity>",
        )
        c2 = _context("c2").replace(
            "</xbrli:entity>",
            "<xbrli:segment/></xbrli:entity>",
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(c1 + c2))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-034"]
        assert len(findings) == 2

    def test_location_has_context_id(self) -> None:
        body = _context("ctx_seg").replace(
            "</xbrli:entity>",
            "<xbrli:segment/></xbrli:entity>",
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-034"]
        assert len(findings) == 1
        assert "ctx_seg" in findings[0].location

    def test_mixed_contexts(self) -> None:
        """Only the context with segment is reported."""
        c_clean = _context("c_clean")
        c_bad = _context("c_bad").replace(
            "</xbrli:entity>",
            "<xbrli:segment/></xbrli:entity>",
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(c_clean + c_bad))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-034"]
        assert len(findings) == 1
        assert "c_bad" in findings[0].message

    def test_malformed_xml_skipped(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"not xml")
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-034"]
        assert findings == []

    def test_eba_false_skips(self) -> None:
        body = _context("c1").replace(
            "</xbrli:entity>",
            "<xbrli:segment/></xbrli:entity>",
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=False)
        findings = [r for r in results if r.rule_id == "XML-034"]
        assert findings == []


# ---------------------------------------------------------------------------
# XML-035: Scenario children must be dimension members only
# ---------------------------------------------------------------------------


class TestXML035ScenarioDimensionOnly:
    """Tests for the XML-035 rule implementation."""

    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_scenario_no_findings(self) -> None:
        """Scenario with only explicitMember children is valid."""
        body = _context(
            extra=(
                "<xbrli:scenario>"
                '<xbrldi:explicitMember dimension="dim:D1">dom:V1</xbrldi:explicitMember>'
                "</xbrli:scenario>"
            ),
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-035"]
        assert findings == []

    def test_typed_member_valid(self) -> None:
        """Scenario with typedMember is valid."""
        body = _context(
            extra=(
                "<xbrli:scenario>"
                '<xbrldi:typedMember dimension="dim:D1"><val>123</val></xbrldi:typedMember>'
                "</xbrli:scenario>"
            ),
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-035"]
        assert findings == []

    def test_mixed_explicit_and_typed_valid(self) -> None:
        """Both explicitMember and typedMember together are valid."""
        body = _context(
            extra=(
                "<xbrli:scenario>"
                '<xbrldi:explicitMember dimension="dim:D1">dom:V1</xbrldi:explicitMember>'
                '<xbrldi:typedMember dimension="dim:D2"><val>X</val></xbrldi:typedMember>'
                "</xbrli:scenario>"
            ),
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-035"]
        assert findings == []

    def test_empty_scenario_no_findings(self) -> None:
        """An empty scenario has no invalid children."""
        body = _context(extra="<xbrli:scenario/>")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-035"]
        assert findings == []

    def test_no_scenario_no_findings(self) -> None:
        """Context without scenario is valid."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_valid_instance())
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-035"]
        assert findings == []

    def test_non_dimension_child_detected(self) -> None:
        """A non-dimension element in scenario triggers a finding."""
        body = _context(
            extra=("<xbrli:scenario><someElement>value</someElement></xbrli:scenario>"),
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-035"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "someElement" in findings[0].message

    def test_mixed_valid_and_invalid_children(self) -> None:
        """One invalid child among valid ones triggers a finding."""
        body = _context(
            extra=(
                "<xbrli:scenario>"
                '<xbrldi:explicitMember dimension="dim:D1">dom:V1</xbrldi:explicitMember>'
                "<badElement>oops</badElement>"
                "</xbrli:scenario>"
            ),
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-035"]
        assert len(findings) == 1
        assert "badElement" in findings[0].message

    def test_one_finding_per_context(self) -> None:
        """Multiple invalid children in one scenario produce only one finding."""
        body = _context(
            extra=("<xbrli:scenario><bad1>a</bad1><bad2>b</bad2></xbrli:scenario>"),
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-035"]
        assert len(findings) == 1

    def test_multiple_bad_contexts(self) -> None:
        """Each bad context gets its own finding."""
        c1 = _context(
            "c1",
            extra="<xbrli:scenario><bad/></xbrli:scenario>",
        )
        c2 = _context(
            "c2",
            extra="<xbrli:scenario><bad/></xbrli:scenario>",
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(c1 + c2))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-035"]
        assert len(findings) == 2

    def test_location_has_context_id(self) -> None:
        body = _context(
            "ctx_sc",
            extra="<xbrli:scenario><bad/></xbrli:scenario>",
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-035"]
        assert len(findings) == 1
        assert "ctx_sc" in findings[0].location

    def test_malformed_xml_skipped(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"not xml")
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-035"]
        assert findings == []

    def test_eba_false_skips(self) -> None:
        body = _context(extra="<xbrli:scenario><bad/></xbrli:scenario>")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=False)
        findings = [r for r in results if r.rule_id == "XML-035"]
        assert findings == []
