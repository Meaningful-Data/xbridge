"""Tests for EBA-DATE-001: instance reference date within the module applicability range.

Also covers the ``from``/``to`` applicability dates on :class:`~xbridge.modules.Module`
and their presence in the committed module JSON files.
"""

import importlib
import io
import sys
import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile

from xbridge.modules import Module
from xbridge.validation._context import ValidationContext
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry, load_registry

_MOD = "xbridge.validation.rules.eba_dates"
_MODULES_DIR = Path(__file__).parents[1] / "src" / "xbridge" / "modules"


def _ensure_registered() -> None:
    if ("EBA-DATE-001", "xml") not in _impl_registry:
        if _MOD in sys.modules:
            importlib.reload(sys.modules[_MOD])
        else:
            importlib.import_module(_MOD)


def _rule_def():
    for rule in load_registry():
        if rule.code == "EBA-DATE-001":
            return rule
    raise AssertionError("EBA-DATE-001 not found in registry")


class _FakeModule:
    def __init__(self, from_date, to_date):
        self.from_date = from_date
        self.to_date = to_date


class _FakeXmlInstance:
    def __init__(self, period):
        self.period = period


def _xml_ctx(module, period):
    ctx = ValidationContext(
        rule_set="xml",
        rule_definition=_rule_def(),
        file_path=Path("instance.xbrl"),
        raw_bytes=b"",
        xml_instance=_FakeXmlInstance(period),
        module=module,
    )
    return ctx


def _csv_zip(ref_period: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # Mirror a real EBA report package: a single top-level folder containing reports/.
        zf.writestr("pkg/reports/report.json", "{}")
        zf.writestr(
            "pkg/reports/parameters.csv",
            f"name,value\nentityID,DUMMY\nrefPeriod,{ref_period}\n",
        )
    return buf.getvalue()


def _csv_ctx(module, ref_period):
    with NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(_csv_zip(ref_period))
        tmp.flush()
    return ValidationContext(
        rule_set="csv",
        rule_definition=_rule_def(),
        file_path=Path(tmp.name),
        raw_bytes=b"",
        module=module,
    )


# ===================================================================
# EBA-DATE-001 — XML
# ===================================================================


class TestEBADATE001Xml:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_inside_closed_range_no_finding(self) -> None:
        from xbridge.validation.rules.eba_dates import check_reference_date_in_range_xml

        ctx = _xml_ctx(_FakeModule("2018-12-31", "2021-06-29"), "2020-01-01")
        check_reference_date_in_range_xml(ctx)
        assert ctx.findings == []

    def test_before_from_is_error(self) -> None:
        from xbridge.validation.rules.eba_dates import check_reference_date_in_range_xml

        ctx = _xml_ctx(_FakeModule("2018-12-31", "2021-06-29"), "2018-12-30")
        check_reference_date_in_range_xml(ctx)
        assert len(ctx.findings) == 1
        assert ctx.findings[0].severity == Severity.ERROR
        assert ctx.findings[0].rule_id == "EBA-DATE-001"

    def test_after_to_is_error(self) -> None:
        from xbridge.validation.rules.eba_dates import check_reference_date_in_range_xml

        ctx = _xml_ctx(_FakeModule("2018-12-31", "2021-06-29"), "2021-06-30")
        check_reference_date_in_range_xml(ctx)
        assert len(ctx.findings) == 1

    def test_boundaries_are_inclusive(self) -> None:
        from xbridge.validation.rules.eba_dates import check_reference_date_in_range_xml

        for ref in ("2018-12-31", "2021-06-29"):
            ctx = _xml_ctx(_FakeModule("2018-12-31", "2021-06-29"), ref)
            check_reference_date_in_range_xml(ctx)
            assert ctx.findings == [], f"{ref} should be in range"

    def test_open_ended_range(self) -> None:
        from xbridge.validation.rules.eba_dates import check_reference_date_in_range_xml

        ok = _xml_ctx(_FakeModule("2026-03-31", None), "2099-01-01")
        check_reference_date_in_range_xml(ok)
        assert ok.findings == []

        bad = _xml_ctx(_FakeModule("2026-03-31", None), "2026-03-30")
        check_reference_date_in_range_xml(bad)
        assert len(bad.findings) == 1

    def test_module_without_from_is_skipped(self) -> None:
        from xbridge.validation.rules.eba_dates import check_reference_date_in_range_xml

        ctx = _xml_ctx(_FakeModule(None, None), "1999-01-01")
        check_reference_date_in_range_xml(ctx)
        assert ctx.findings == []

    def test_no_module_is_skipped(self) -> None:
        from xbridge.validation.rules.eba_dates import check_reference_date_in_range_xml

        ctx = _xml_ctx(None, "1999-01-01")
        check_reference_date_in_range_xml(ctx)
        assert ctx.findings == []

    def test_malformed_reference_date_is_skipped(self) -> None:
        from xbridge.validation.rules.eba_dates import check_reference_date_in_range_xml

        ctx = _xml_ctx(_FakeModule("2018-12-31", "2021-06-29"), "not-a-date")
        check_reference_date_in_range_xml(ctx)
        assert ctx.findings == []


# ===================================================================
# EBA-DATE-001 — CSV
# ===================================================================


class TestEBADATE001Csv:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_inside_range_no_finding(self) -> None:
        from xbridge.validation.rules.eba_dates import check_reference_date_in_range_csv

        ctx = _csv_ctx(_FakeModule("2018-12-31", "2021-06-29"), "2020-01-01")
        check_reference_date_in_range_csv(ctx)
        assert ctx.findings == []

    def test_out_of_range_is_error(self) -> None:
        from xbridge.validation.rules.eba_dates import check_reference_date_in_range_csv

        ctx = _csv_ctx(_FakeModule("2018-12-31", "2021-06-29"), "2025-01-01")
        check_reference_date_in_range_csv(ctx)
        assert len(ctx.findings) == 1
        assert ctx.findings[0].severity == Severity.ERROR


# ===================================================================
# Module from/to applicability dates
# ===================================================================


class TestModuleApplicabilityDates:
    def test_versioned_module_open_ended(self) -> None:
        module = Module.from_serialized(_MODULES_DIR / "ae_ae_4.2.json")
        assert module.from_date == "2026-03-31"
        assert module.to_date is None
        d = module.to_dict()
        assert d["from"] == "2026-03-31"
        assert d["to"] is None

    def test_legacy_module_closed_range(self) -> None:
        module = Module.from_serialized(_MODULES_DIR / "ae_con_cir-680-2014_2018-03-31.json")
        assert module.from_date == "2018-12-31"
        assert module.to_date == "2021-06-29"

    def test_module_without_dates_omits_keys(self) -> None:
        # dora_dora_4.2 has no source reference dates available.
        module = Module.from_serialized(_MODULES_DIR / "dora_dora_4.2.json")
        assert module.from_date is None
        assert module.to_date is None
        d = module.to_dict()
        assert "from" not in d
        assert "to" not in d

    def test_roundtrip_preserves_dates(self) -> None:
        path = _MODULES_DIR / "ae_con_cir-680-2014_2018-03-31.json"
        module = Module.from_serialized(path)
        d = module.to_dict()
        # from/to appear immediately after architecture, before tables.
        keys = list(d.keys())
        assert keys.index("from") == keys.index("architecture") + 1
        assert keys.index("to") == keys.index("from") + 1
        assert keys.index("tables") == keys.index("to") + 1
