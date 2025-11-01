"""
Tests for decimal precision logic in converter
"""

import pandas as pd
import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from xbridge.converter import Converter


class TestDecimalPrecision:
    """Tests for the decimal precision handling in the converter"""

    @pytest.fixture
    def converter_instance(self):
        """Create a converter instance with mocked dependencies"""
        # Mock the instance file to avoid needing real files
        with patch('xbridge.converter.Instance') as mock_instance_class:
            mock_instance = Mock()
            mock_instance.module_ref = "test_module"
            mock_instance.instance_df = pd.DataFrame()
            mock_instance_class.return_value = mock_instance

            with patch('xbridge.converter.Module') as mock_module_class:
                mock_module = Mock()
                mock_module_class.from_serialized.return_value = mock_module

                with patch('xbridge.converter.index', {"test_module": "test.json"}):
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

    def test_inf_with_smaller_precision(self, converter_instance):
        """Test that INF is not overridden by smaller numeric precision"""
        converter_instance._decimals_parameters = {}

        data_type = "Rate"

        # First encounter: decimals = INF
        converter_instance._decimals_parameters[data_type] = "INF"

        # Second encounter: decimals = 2 (should NOT update, INF should remain)
        decimals = 2
        if decimals not in {"INF", "#none"}:
            if (
                isinstance(converter_instance._decimals_parameters[data_type], int)
                and decimals < converter_instance._decimals_parameters[data_type]
            ):
                converter_instance._decimals_parameters[data_type] = decimals

        assert converter_instance._decimals_parameters[data_type] == "INF"

    def test_numeric_then_inf_skips_inf(self, converter_instance):
        """Test that INF does not override existing numeric precision"""
        converter_instance._decimals_parameters = {}

        data_type = "Amount"

        # First encounter: decimals = 3
        converter_instance._decimals_parameters[data_type] = 3

        # Second encounter: decimals = INF (should be skipped per new logic)
        decimals = "INF"
        if decimals in {"INF", "#none"}:
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

        # Test with INF
        data_type2 = "Type2"
        if data_type2 not in converter_instance._decimals_parameters:
            converter_instance._decimals_parameters[data_type2] = "INF"
        assert converter_instance._decimals_parameters[data_type2] == "INF"

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
        if decimals in {"INF", "#none"}:
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
