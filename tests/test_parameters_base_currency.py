from __future__ import annotations

import csv
from pathlib import Path

import pytest

from xbridge.converter import BaseCurrencyEvidence, Converter
from xbridge.exceptions import MultipleBaseCurrenciesError


class DummyInstance:
    def __init__(self, entity: str, period: str, base_currency: str | None) -> None:
        self.entity = entity
        self.period = period
        self.base_currency = base_currency


def _converter(instance: DummyInstance, candidates: dict | None = None) -> Converter:
    conv = Converter.__new__(Converter)
    conv.instance = instance  # type: ignore[assignment]
    conv._decimals_parameters = {}
    conv._base_currency_candidates = candidates or {}
    return conv


def _read_parameters(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def test_parameters_omit_base_currency_when_none(tmp_path: Path) -> None:
    conv = _converter(DummyInstance("ENT1", "2024-01-01", None))

    conv._convert_parameters(tmp_path)

    params_path = tmp_path / "parameters.csv"
    rows = _read_parameters(params_path)

    names = {row["name"] for row in rows}
    assert "entityID" in names
    assert "refPeriod" in names
    assert "baseCurrency" not in names


def test_parameters_include_base_currency_when_present(tmp_path: Path) -> None:
    conv = _converter(DummyInstance("ENT1", "2024-01-01", "iso4217:EUR"))

    conv._convert_parameters(tmp_path)

    params_path = tmp_path / "parameters.csv"
    rows = _read_parameters(params_path)

    by_name = {row["name"]: row["value"] for row in rows}
    assert by_name["entityID"] == "ENT1"
    assert by_name["refPeriod"] == "2024-01-01"
    assert by_name["baseCurrency"] == "iso4217:EUR"


def test_parameters_prefer_currency_of_reported_facts(tmp_path: Path) -> None:
    """The currency of the facts wins over the first unit declared in the instance."""
    conv = _converter(
        DummyInstance("ENT1", "2024-01-01", "iso4217:AED"),
        {
            "iso4217:EUR": BaseCurrencyEvidence(
                currency="iso4217:EUR",
                fact_count=12,
                example_table="C_72-00-a",
                example_datapoint="dp1",
            )
        },
    )

    conv._convert_parameters(tmp_path)

    rows = _read_parameters(tmp_path / "parameters.csv")
    by_name = {row["name"]: row["value"] for row in rows}
    assert by_name["baseCurrency"] == "iso4217:EUR"


def test_parameters_raise_on_conflicting_base_currencies(tmp_path: Path) -> None:
    """Facts pointing to two base currencies make the instance non-convertible."""
    conv = _converter(
        DummyInstance("ENT1", "2024-01-01", "iso4217:EUR"),
        {
            "iso4217:EUR": BaseCurrencyEvidence(
                currency="iso4217:EUR",
                fact_count=12,
                example_table="C_72-00-a",
                example_datapoint="dp1",
            ),
            "iso4217:AED": BaseCurrencyEvidence(
                currency="iso4217:AED",
                fact_count=3,
                example_table="C_72-00-a",
                example_datapoint="dp2",
            ),
        },
    )

    with pytest.raises(MultipleBaseCurrenciesError) as exc_info:
        conv._convert_parameters(tmp_path)

    assert exc_info.value.currencies == ["iso4217:AED", "iso4217:EUR"]
    assert "dp2" in str(exc_info.value)
    assert not (tmp_path / "parameters.csv").exists()
