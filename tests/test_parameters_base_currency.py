from __future__ import annotations

import csv
from pathlib import Path

from xbridge.converter import Converter


class DummyInstance:
    def __init__(self, entity: str, period: str, base_currency: str | None) -> None:
        self.entity = entity
        self.period = period
        self.base_currency = base_currency


def _read_parameters(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def test_parameters_omit_base_currency_when_none(tmp_path: Path) -> None:
    conv = Converter.__new__(Converter)
    conv.instance = DummyInstance("ENT1", "2024-01-01", None)
    conv._decimals_parameters = {}

    conv._convert_parameters(tmp_path)

    params_path = tmp_path / "parameters.csv"
    rows = _read_parameters(params_path)

    names = {row["name"] for row in rows}
    assert "entityID" in names
    assert "refPeriod" in names
    assert "baseCurrency" not in names


def test_parameters_include_base_currency_when_present(tmp_path: Path) -> None:
    conv = Converter.__new__(Converter)
    conv.instance = DummyInstance("ENT1", "2024-01-01", "iso4217:EUR")
    conv._decimals_parameters = {}

    conv._convert_parameters(tmp_path)

    params_path = tmp_path / "parameters.csv"
    rows = _read_parameters(params_path)

    by_name = {row["name"]: row["value"] for row in rows}
    assert by_name["entityID"] == "ENT1"
    assert by_name["refPeriod"] == "2024-01-01"
    assert by_name["baseCurrency"] == "iso4217:EUR"
