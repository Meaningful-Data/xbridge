"""
End-to-end tests for the base currency of multi-currency reports.

The base currency of a report is the currency of the facts whose datapoint
takes its unit from the ``baseCurrency`` parameter in the taxonomy JSON
(``"unit": "$baseCurrency"``).  Facts of datapoints that report their unit
explicitly (``"unit": "$unit"``) hold a currency breakdown and must not
influence the parameter.

The fixtures are derived at runtime from ``sample_3_2_phase1/test1_in.xbrl``
(a COREP LCR-DA report with facts in EUR, AED, AFN and ALL) so that the tests
exercise a real EBA module without adding another large sample file.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from zipfile import ZipFile

import pytest

from xbridge.api import convert_instance
from xbridge.exceptions import MultipleBaseCurrenciesError, ValidationError
from xbridge.validation import validate

MULTI_CURRENCY_SAMPLE = Path(__file__).parent / "test_files" / "sample_3_2_phase1" / "test1_in.xbrl"

_UNIT_BLOCK = re.compile(r'[ \t]*<xbrli:unit id="(u[A-Z]+)">.*?</xbrli:unit>\s*\n', re.DOTALL)


def _base_currency(zip_path: Path) -> str | None:
    """Returns the baseCurrency parameter of a generated XBRL-CSV package."""
    with ZipFile(zip_path) as archive:
        parameters_file = next(
            name for name in archive.namelist() if name.endswith("parameters.csv")
        )
        content = archive.read(parameters_file).decode("utf-8").splitlines()
    parameters = {row["name"]: row["value"] for row in csv.DictReader(content)}
    return parameters.get("baseCurrency")


def test_base_currency_is_not_taken_from_the_first_declared_unit(tmp_path: Path) -> None:
    """The order of the xbrli:unit declarations must not change the base currency.

    Regression test for issue #123: the base currency used to be the first
    ``iso4217`` unit declared in the instance, so simply moving the declaration
    of a currency-breakdown unit to the top changed the parameter.
    """
    source = MULTI_CURRENCY_SAMPLE.read_text(encoding="utf-8")
    unit_blocks = {match.group(1): match.group(0) for match in _UNIT_BLOCK.finditer(source)}
    assert {"uEUR", "uAED"} <= set(unit_blocks), "sample no longer declares EUR and AED units"

    # Declare the AED unit (a currency breakdown) before the EUR one
    reordered = source.replace(unit_blocks["uAED"], "")
    reordered = reordered.replace(unit_blocks["uEUR"], unit_blocks["uAED"] + unit_blocks["uEUR"], 1)
    reordered_path = tmp_path / "reordered_in.xbrl"
    reordered_path.write_text(reordered, encoding="utf-8")

    original_output = convert_instance(instance_path=MULTI_CURRENCY_SAMPLE, output_path=tmp_path)
    reordered_output = convert_instance(instance_path=reordered_path, output_path=tmp_path)

    assert _base_currency(Path(original_output)) == "iso4217:EUR"
    assert _base_currency(Path(reordered_output)) == "iso4217:EUR"


def test_conflicting_base_currencies_are_rejected(tmp_path: Path) -> None:
    """Facts of $baseCurrency datapoints reported in two currencies are an error."""
    source = MULTI_CURRENCY_SAMPLE.read_text(encoding="utf-8")
    # The EUR facts of this sample are the ones taking their unit from the
    # parameter; switching a few of them to AED yields two base currencies.
    conflicting = source.replace('unitRef="uEUR"', 'unitRef="uAED"', 5)
    assert conflicting != source
    conflicting_path = tmp_path / "conflicting_in.xbrl"
    conflicting_path.write_text(conflicting, encoding="utf-8")

    with pytest.raises(MultipleBaseCurrenciesError) as exc_info:
        convert_instance(instance_path=conflicting_path, output_path=tmp_path)

    assert exc_info.value.currencies == ["iso4217:AED", "iso4217:EUR"]
    assert not list(tmp_path.glob("*.zip"))


def test_validation_reports_conflicting_base_currencies(tmp_path: Path) -> None:
    """EBA-CUR-004 reports the conflict before the instance is converted."""
    source = MULTI_CURRENCY_SAMPLE.read_text(encoding="utf-8")
    conflicting_path = tmp_path / "conflicting_in.xbrl"
    conflicting_path.write_text(source.replace('unitRef="uEUR"', 'unitRef="uAED"', 5), "utf-8")

    results = validate(conflicting_path, eba=True)

    findings = results["EBA"]["errors"].get("EBA-CUR-004")
    assert findings, "EBA-CUR-004 did not report the conflicting base currencies"
    message = findings[0]["message"]
    assert "AED" in message
    assert "EUR" in message


def test_validation_accepts_a_currency_breakdown(tmp_path: Path) -> None:
    """A report with facts in several currencies is valid when only one is the base one.

    The facts of the datapoints that report their unit explicitly hold the
    breakdown by significant currency and must not be flagged.
    """
    results = validate(MULTI_CURRENCY_SAMPLE, eba=True)

    assert "EBA-CUR-004" not in results["EBA"]["errors"]


def test_conflicting_base_currencies_stop_the_validated_pipeline(tmp_path: Path) -> None:
    """With validate=True the conflict stops the conversion before any output."""
    source = MULTI_CURRENCY_SAMPLE.read_text(encoding="utf-8")
    conflicting_path = tmp_path / "conflicting_in.xbrl"
    conflicting_path.write_text(source.replace('unitRef="uEUR"', 'unitRef="uAED"', 5), "utf-8")

    with pytest.raises(ValidationError) as exc_info:
        convert_instance(
            instance_path=conflicting_path, output_path=tmp_path, validate=True, eba=True
        )

    # path is None while the failure happened before the conversion
    assert exc_info.value.path is None
    assert "EBA-CUR-004" in exc_info.value.results["EBA"]["errors"]
    assert not list(tmp_path.glob("*.zip"))
