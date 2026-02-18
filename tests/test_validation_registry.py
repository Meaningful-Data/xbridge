"""Tests for the validation registry module."""

import json
from pathlib import Path

import pytest

from xbridge.validation._models import RuleDefinition, Severity
from xbridge.validation._registry import (
    _clear_registry,
    get_rule_impl,
    load_registry,
    rule_impl,
)


class TestLoadRegistry:
    """Tests for load_registry()."""

    def test_returns_list(self):
        result = load_registry()
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(r, RuleDefinition) for r in result)

    def test_xml001_present(self):
        registry = load_registry()
        codes = [r.code for r in registry]
        assert "XML-001" in codes

    def test_field_types(self):
        registry = load_registry()
        xml001 = next(r for r in registry if r.code == "XML-001")
        assert xml001.severity == Severity.ERROR
        assert isinstance(xml001.xml, bool)
        assert xml001.xml is True
        assert isinstance(xml001.csv, bool)
        assert xml001.csv is False
        assert xml001.eba_ref is None


class TestRuleImpl:
    """Tests for the @rule_impl decorator and get_rule_impl()."""

    def teardown_method(self) -> None:
        _clear_registry()

    def test_registers_generic(self):
        @rule_impl("TEST-001")
        def check_test(ctx):  # type: ignore[no-untyped-def]
            pass

        result = get_rule_impl("TEST-001", "xml")
        assert result is check_test

    def test_registers_format_specific(self):
        @rule_impl("TEST-002", format="xml")
        def check_xml(ctx):  # type: ignore[no-untyped-def]
            pass

        @rule_impl("TEST-002", format="csv")
        def check_csv(ctx):  # type: ignore[no-untyped-def]
            pass

        assert get_rule_impl("TEST-002", "xml") is check_xml
        assert get_rule_impl("TEST-002", "csv") is check_csv

    def test_duplicate_raises(self):
        @rule_impl("TEST-DUP")
        def first(ctx):  # type: ignore[no-untyped-def]
            pass

        with pytest.raises(ValueError, match="Duplicate rule implementation"):

            @rule_impl("TEST-DUP")
            def second(ctx):  # type: ignore[no-untyped-def]
                pass

    def test_format_specific_priority(self):
        @rule_impl("TEST-003")
        def generic(ctx):  # type: ignore[no-untyped-def]
            pass

        @rule_impl("TEST-003", format="xml")
        def xml_specific(ctx):  # type: ignore[no-untyped-def]
            pass

        assert get_rule_impl("TEST-003", "xml") is xml_specific

    def test_fallback_to_generic(self):
        @rule_impl("TEST-004")
        def generic(ctx):  # type: ignore[no-untyped-def]
            pass

        assert get_rule_impl("TEST-004", "csv") is generic

    def test_missing_returns_none(self):
        assert get_rule_impl("NONEXISTENT-999", "xml") is None


class TestRegistryJson:
    """Tests for the registry.json data file."""

    def _load_raw(self) -> list:  # type: ignore[type-arg]
        registry_path = (
            Path(__file__).parent.parent / "src" / "xbridge" / "validation" / "registry.json"
        )
        with open(registry_path, encoding="utf-8") as f:
            return json.load(f)  # type: ignore[no-any-return]

    def test_valid_json(self):
        data = self._load_raw()
        assert isinstance(data, list)
        assert all(isinstance(entry, dict) for entry in data)

    def test_no_duplicate_codes(self):
        data = self._load_raw()
        codes = [entry["code"] for entry in data]
        assert len(codes) == len(set(codes)), (
            f"Duplicate codes: {[c for c in codes if codes.count(c) > 1]}"
        )

    def test_required_fields(self):
        required = {
            "code",
            "message",
            "severity",
            "xml",
            "csv",
            "eba",
            "post_conversion",
            "eba_ref",
        }
        data = self._load_raw()
        for entry in data:
            missing = required - set(entry.keys())
            assert not missing, f"Entry {entry.get('code', '?')} missing fields: {missing}"
