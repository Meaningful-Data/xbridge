"""
Tests for decimal precision logic in converter
"""

from unittest.mock import Mock, patch

import pandas as pd
import pytest

from xbridge.converter import Converter
from xbridge.exceptions import DecimalValueError


class TestDecimalPrecision:
    """Tests for the decimal precision handling in the converter"""

    @pytest.fixture
    def converter_instance(self):
        """Create a converter instance with mocked dependencies"""
        # Mock the instance file to avoid needing real files
        with patch("xbridge.converter.Instance") as mock_instance_class:
            mock_instance = Mock()
            mock_instance.module_ref = "test_module"
            mock_instance.instance_df = pd.DataFrame()
            mock_instance_class.return_value = mock_instance

            with patch("xbridge.converter.Module") as mock_module_class:
                mock_module = Mock()
                mock_module_class.from_serialized.return_value = mock_module

                with patch("xbridge.converter.index", {"test_module": "test.json"}):
                    converter = Converter("dummy_path.xml")
                    return converter

    def test_minimum_precision_basic(self, converter_instance):
        """Test that minimum precision is kept between two numeric values"""
        # Setup initial state
        converter_instance._decimals_parameters = {}

        # Simulate processing decimals table
        data_type1 = "MonetaryAmount"

        # First encounter: decimals = 4
        converter_instance._decimals_parameters[data_type1] = 4

        # Second encounter: decimals = 2 (should update to 2 as it's smaller)
        decimals = 2
        if (
            isinstance(converter_instance._decimals_parameters[data_type1], int)
            and decimals < converter_instance._decimals_parameters[data_type1]
        ):
            converter_instance._decimals_parameters[data_type1] = decimals

        assert converter_instance._decimals_parameters[data_type1] == 2

    def test_minimum_precision_multiple_values(self, converter_instance):
        """Test minimum precision with multiple progressively smaller values"""
        converter_instance._decimals_parameters = {}

        data_type = "Percentage"

        # Sequence: 6 -> 4 -> 2 -> 3 (should end up at 2)
        values = [6, 4, 2, 3]

        for decimals in values:
            if data_type not in converter_instance._decimals_parameters:
                converter_instance._decimals_parameters[data_type] = decimals
            else:
                if (
                    isinstance(converter_instance._decimals_parameters[data_type], int)
                    and decimals < converter_instance._decimals_parameters[data_type]
                ):
                    converter_instance._decimals_parameters[data_type] = decimals

        assert converter_instance._decimals_parameters[data_type] == 2

    def test_inf_then_numeric_prefers_numeric(self, converter_instance):
        """Test that a numeric value replaces infinity (numeric values preferred)"""
        converter_instance._decimals_parameters = {}

        data_type = "Rate"

        # First encounter: decimals = infinity
        converter_instance._decimals_parameters[data_type] = "#none"

        # Second encounter: decimals = 2 (should replace infinity with 2)
        decimals = 2
        if (
            decimals != "#none"
            and converter_instance._decimals_parameters[data_type] == "#none"
            or (
                isinstance(converter_instance._decimals_parameters[data_type], int)
                and decimals < converter_instance._decimals_parameters[data_type]
            )
        ):
            converter_instance._decimals_parameters[data_type] = decimals

        assert converter_instance._decimals_parameters[data_type] == 2

    def test_numeric_then_inf_skips_inf(self, converter_instance):
        """Test that infinity does not override existing numeric precision"""
        converter_instance._decimals_parameters = {}

        data_type = "Amount"

        # First encounter: decimals = 3
        converter_instance._decimals_parameters[data_type] = 3

        # Second encounter: decimals = infinity (should be skipped per new logic)
        decimals = "#none"
        if decimals == "#none":
            # Special values are skipped when an existing value exists
            pass
        else:
            if (
                isinstance(converter_instance._decimals_parameters[data_type], int)
                and decimals < converter_instance._decimals_parameters[data_type]
            ):
                converter_instance._decimals_parameters[data_type] = decimals

        assert converter_instance._decimals_parameters[data_type] == 3

    def test_first_encounter_sets_value(self, converter_instance):
        """Test that first encounter sets the value regardless of what it is"""
        converter_instance._decimals_parameters = {}

        # Test with numeric value
        data_type1 = "Type1"
        if data_type1 not in converter_instance._decimals_parameters:
            converter_instance._decimals_parameters[data_type1] = 5
        assert converter_instance._decimals_parameters[data_type1] == 5

        # Test with INF, which normalisation canonicalises to "#none"
        data_type2 = "Type2"
        if data_type2 not in converter_instance._decimals_parameters:
            converter_instance._decimals_parameters[data_type2] = (
                converter_instance._normalize_decimals_value("INF")
            )
        assert converter_instance._decimals_parameters[data_type2] == "#none"

        # Test with #none
        data_type3 = "Type3"
        if data_type3 not in converter_instance._decimals_parameters:
            converter_instance._decimals_parameters[data_type3] = "#none"
        assert converter_instance._decimals_parameters[data_type3] == "#none"

    def test_larger_value_does_not_override(self, converter_instance):
        """Test that a larger value does not override smaller existing value"""
        converter_instance._decimals_parameters = {}

        data_type = "Balance"

        # First encounter: decimals = 2
        converter_instance._decimals_parameters[data_type] = 2

        # Second encounter: decimals = 5 (should NOT update)
        decimals = 5
        if (
            isinstance(converter_instance._decimals_parameters[data_type], int)
            and decimals < converter_instance._decimals_parameters[data_type]
        ):
            converter_instance._decimals_parameters[data_type] = decimals

        assert converter_instance._decimals_parameters[data_type] == 2

    def test_equal_value_does_not_override(self, converter_instance):
        """Test that an equal value does not trigger update"""
        converter_instance._decimals_parameters = {}

        data_type = "Balance"

        # First encounter: decimals = 3
        converter_instance._decimals_parameters[data_type] = 3

        # Second encounter: decimals = 3 (should NOT update, condition is <, not <=)
        decimals = 3
        if (
            isinstance(converter_instance._decimals_parameters[data_type], int)
            and decimals < converter_instance._decimals_parameters[data_type]
        ):
            converter_instance._decimals_parameters[data_type] = decimals

        assert converter_instance._decimals_parameters[data_type] == 3

    def test_none_value_skipped(self, converter_instance):
        """Test that #none special value is skipped when existing value exists"""
        converter_instance._decimals_parameters = {}

        data_type = "Status"

        # First encounter: decimals = 2
        converter_instance._decimals_parameters[data_type] = 2

        # Second encounter: decimals = #none (should be skipped)
        decimals = "#none"
        if decimals == "#none":
            # Special values are skipped when an existing value exists
            pass
        else:
            if (
                isinstance(converter_instance._decimals_parameters[data_type], int)
                and decimals < converter_instance._decimals_parameters[data_type]
            ):
                converter_instance._decimals_parameters[data_type] = decimals

        assert converter_instance._decimals_parameters[data_type] == 2

    def test_zero_precision(self, converter_instance):
        """Test that zero precision works correctly (minimum possible)"""
        converter_instance._decimals_parameters = {}

        data_type = "Integer"

        # First encounter: decimals = 3
        converter_instance._decimals_parameters[data_type] = 3

        # Second encounter: decimals = 0 (should update to 0)
        decimals = 0
        if (
            isinstance(converter_instance._decimals_parameters[data_type], int)
            and decimals < converter_instance._decimals_parameters[data_type]
        ):
            converter_instance._decimals_parameters[data_type] = decimals

        assert converter_instance._decimals_parameters[data_type] == 0

    def test_order_independence_inf_and_numeric(self, converter_instance):
        """Order of infinity and numeric values must not matter - both yield numeric"""
        # Test 1: infinity -> 2 should yield 2
        converter_instance._decimals_parameters = {}
        data_type1 = "Type1"

        values_inf_first = ["#none", 2]
        for decimals in values_inf_first:
            if data_type1 not in converter_instance._decimals_parameters:
                converter_instance._decimals_parameters[data_type1] = decimals
            else:
                if decimals == "#none":
                    pass
                else:
                    if converter_instance._decimals_parameters[data_type1] == "#none" or (
                        isinstance(converter_instance._decimals_parameters[data_type1], int)
                        and decimals < converter_instance._decimals_parameters[data_type1]
                    ):
                        converter_instance._decimals_parameters[data_type1] = decimals

        # Test 2: 2 -> infinity should yield 2
        data_type2 = "Type2"

        values_numeric_first = [2, "#none"]
        for decimals in values_numeric_first:
            if data_type2 not in converter_instance._decimals_parameters:
                converter_instance._decimals_parameters[data_type2] = decimals
            else:
                if decimals == "#none":
                    pass
                else:
                    if converter_instance._decimals_parameters[data_type2] == "#none" or (
                        isinstance(converter_instance._decimals_parameters[data_type2], int)
                        and decimals < converter_instance._decimals_parameters[data_type2]
                    ):
                        converter_instance._decimals_parameters[data_type2] = decimals

        # Both should result in 2
        assert converter_instance._decimals_parameters[data_type1] == 2
        assert converter_instance._decimals_parameters[data_type2] == 2

    def test_invalid_decimal_value_raises_custom_exception(self, converter_instance):
        """Ensure invalid decimals raise a DecimalValueError with offending value."""
        with pytest.raises(DecimalValueError, match="Invalid decimals value") as exc_info:
            converter_instance._normalize_decimals_value("2.0")

        # Verify it's the exact exception type, not wrapped
        assert type(exc_info.value) is DecimalValueError
        assert exc_info.value.offending_value == "2.0"


class TestInfiniteDecimalsEncoding:
    """The xBRL-CSV output must spell infinite precision as ``#none``.

    xBRL-CSV 1.0 REC section 3.1.9 accepts only an integer or ``#none`` as a
    decimals value.  ``INF`` is the xBRL-XML lexical form and a conformant
    processor rejects it with ``xbrlce:invalidDecimalsValue``, so the source
    instance's ``@decimals="INF"`` must not survive into ``parameters.csv``.
    """

    @pytest.fixture
    def converter_instance(self):
        """Create a converter instance with mocked dependencies."""
        with patch("xbridge.converter.Instance") as mock_instance_class:
            mock_instance = Mock()
            mock_instance.module_ref = "test_module"
            mock_instance.instance_df = pd.DataFrame()
            mock_instance.entity = "lei:529900T8BM49AURSDO55"
            mock_instance.period = "2025-12-31"
            mock_instance.base_currency = "EUR"
            mock_instance_class.return_value = mock_instance

            with patch("xbridge.converter.Module") as mock_module_class:
                mock_module = Mock()
                mock_module_class.from_serialized.return_value = mock_module

                with patch("xbridge.converter.index", {"test_module": "test.json"}):
                    return Converter("dummy_path.xml")

    @pytest.mark.parametrize("raw", ["INF", " INF ", "#none", " #none "])
    def test_infinity_normalises_to_none(self, converter_instance, raw):
        """Both spellings of infinity canonicalise to the xBRL-CSV one."""
        assert converter_instance._normalize_decimals_value(raw) == "#none"

    @pytest.mark.parametrize(
        ("raw", "expected"), [("-3", -3), ("0", 0), ("4", 4), (2, 2), ("-6", -6)]
    )
    def test_integers_pass_through(self, converter_instance, raw, expected):
        assert converter_instance._normalize_decimals_value(raw) == expected

    def test_parameters_csv_writes_none_not_inf(self, converter_instance, tmp_path):
        """A source instance reporting @decimals="INF" yields "#none" on disk."""
        converter_instance._decimals_parameters = {
            "decimalsMonetary": converter_instance._normalize_decimals_value("INF"),
            "decimalsPercentage": 4,
        }

        converter_instance._convert_parameters(tmp_path)

        content = (tmp_path / "parameters.csv").read_text(encoding="utf-8")
        rows = dict(line.split(",", 1) for line in content.splitlines()[1:] if line)
        assert rows["decimalsMonetary"] == "#none"
        assert rows["decimalsPercentage"] == "4"
        assert "INF" not in content

    def test_invalid_value_still_rejected(self, converter_instance):
        """Canonicalisation must not widen what counts as a valid value."""
        with pytest.raises(DecimalValueError, match="Invalid decimals value"):
            converter_instance._normalize_decimals_value("inf")
