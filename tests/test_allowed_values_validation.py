"""
Tests for allowed_values validation and normalization
"""

import pandas as pd
import pytest

from xbridge.converter import Converter
from xbridge.modules import Module, Table, Variable


class TestAllowedValuesNormalization:
    """Tests for the _normalize_allowed_values method"""

    def test_normalize_values_with_wrong_namespace(self):
        """Test that values with wrong namespace get normalized"""
        # Create a simple datapoint_df with allowed_values
        datapoint_df = pd.DataFrame(
            [
                {
                    "datapoint": "dp123",
                    "DimX": "eba_BT:x22",
                    "allowed_values": ["eba_BT:x22", "eba_BT:x23"],
                }
            ]
        )

        # Create a table_df with facts that have wrong namespace
        table_df = pd.DataFrame(
            [
                {"datapoint": "dp123", "DimX": "wrong_ns:x22", "value": "200"},
                {"datapoint": "dp123", "DimX": "different:x23", "value": "300"},
            ]
        )

        # Create a mock converter instance
        converter = Converter.__new__(Converter)

        # Normalize
        result_df = converter._normalize_allowed_values(table_df, datapoint_df)

        # Check that wrong namespaces were corrected
        assert result_df.loc[0, "DimX"] == "eba_BT:x22"
        assert result_df.loc[1, "DimX"] == "eba_BT:x23"

    def test_normalize_values_invalid_code_raises_error(self):
        """Test that invalid codes (not in allowed_values) raise an error"""
        # Create a simple datapoint_df with allowed_values
        datapoint_df = pd.DataFrame(
            [
                {
                    "datapoint": "dp123",
                    "metric": "met1",
                    "allowed_values": ["eba_BT:x22", "eba_BT:x23"],
                }
            ]
        )

        # Create a table_df with facts that have an invalid code
        table_df = pd.DataFrame(
            [
                {"datapoint": "dp123", "metric": "wrong_ns:x99", "value": "100"},
            ]
        )

        # Create a mock converter instance
        converter = Converter.__new__(Converter)

        # Should raise ValueError for invalid code
        with pytest.raises(ValueError) as exc_info:
            converter._normalize_allowed_values(table_df, datapoint_df)

        assert "Invalid values for datapoint 'dp123'" in str(exc_info.value)
        assert "x99" in str(exc_info.value)
        assert "['x22', 'x23']" in str(exc_info.value)

    def test_normalize_values_with_multiple_dimensions(self):
        """Test normalization across multiple dimension columns"""
        # Create a datapoint_df with allowed_values
        datapoint_df = pd.DataFrame(
            [
                {
                    "datapoint": "dp456",
                    "DimA": "eba_A:a1",
                    "DimB": "eba_B:b1",
                    "allowed_values": ["eba_A:a1", "eba_A:a2", "eba_B:b1", "eba_B:b2"],
                }
            ]
        )

        # Create a table_df with facts that have wrong namespaces in multiple dims
        table_df = pd.DataFrame(
            [
                {
                    "datapoint": "dp456",
                    "DimA": "wrong:a1",
                    "DimB": "other:b2",
                    "value": "100",
                }
            ]
        )

        # Create a mock converter instance
        converter = Converter.__new__(Converter)

        # Normalize
        result_df = converter._normalize_allowed_values(table_df, datapoint_df)

        # Check both dimensions were normalized
        assert result_df.loc[0, "DimA"] == "eba_A:a1"
        assert result_df.loc[0, "DimB"] == "eba_B:b2"

    def test_normalize_values_no_allowed_values(self):
        """Test that dataframes without allowed_values are unchanged"""
        # Create a datapoint_df without allowed_values
        datapoint_df = pd.DataFrame(
            [{"datapoint": "dp789", "metric": "met1", "allowed_values": []}]
        )

        # Create a table_df with facts
        table_df = pd.DataFrame(
            [{"datapoint": "dp789", "metric": "any:value", "value": "100"}]
        )

        # Create a mock converter instance
        converter = Converter.__new__(Converter)

        # Normalize
        result_df = converter._normalize_allowed_values(table_df, datapoint_df)

        # Should be unchanged
        assert result_df.loc[0, "metric"] == "any:value"

    def test_normalize_values_preserves_correct_namespaces(self):
        """Test that values with correct namespace are not changed"""
        # Create a datapoint_df with allowed_values
        datapoint_df = pd.DataFrame(
            [
                {
                    "datapoint": "dp100",
                    "metric": "met1",
                    "allowed_values": ["eba_CU:EUR", "eba_CU:USD"],
                }
            ]
        )

        # Create a table_df with facts that already have correct namespace
        table_df = pd.DataFrame(
            [
                {"datapoint": "dp100", "metric": "eba_CU:EUR", "value": "100"},
                {"datapoint": "dp100", "metric": "eba_CU:USD", "value": "200"},
            ]
        )

        # Create a mock converter instance
        converter = Converter.__new__(Converter)

        # Normalize
        result_df = converter._normalize_allowed_values(table_df, datapoint_df)

        # Should remain unchanged
        assert result_df.loc[0, "metric"] == "eba_CU:EUR"
        assert result_df.loc[1, "metric"] == "eba_CU:USD"

    def test_normalize_values_with_empty_dataframe(self):
        """Test that empty dataframes are handled gracefully"""
        datapoint_df = pd.DataFrame(
            [
                {
                    "datapoint": "dp200",
                    "metric": "met1",
                    "allowed_values": ["eba_BT:x22"],
                }
            ]
        )

        table_df = pd.DataFrame(columns=["datapoint", "metric", "value"])

        converter = Converter.__new__(Converter)

        # Should not raise error
        result_df = converter._normalize_allowed_values(table_df, datapoint_df)

        assert len(result_df) == 0

    def test_normalize_values_missing_allowed_values_column(self):
        """Test that dataframes without allowed_values column are returned unchanged"""
        datapoint_df = pd.DataFrame([{"datapoint": "dp300", "metric": "met1"}])

        table_df = pd.DataFrame(
            [{"datapoint": "dp300", "metric": "any:value", "value": "100"}]
        )

        converter = Converter.__new__(Converter)

        result_df = converter._normalize_allowed_values(table_df, datapoint_df)

        # Should be unchanged
        assert result_df.loc[0, "metric"] == "any:value"

    def test_normalize_values_with_null_values(self):
        """Test that null values in dimension columns are handled correctly"""
        datapoint_df = pd.DataFrame(
            [
                {
                    "datapoint": "dp400",
                    "DimA": "eba_A:a1",
                    "allowed_values": ["eba_A:a1", "eba_A:a2"],
                }
            ]
        )

        table_df = pd.DataFrame(
            [
                {"datapoint": "dp400", "DimA": "wrong:a1", "value": "100"},
                {"datapoint": "dp400", "DimA": None, "value": "200"},
            ]
        )

        converter = Converter.__new__(Converter)

        result_df = converter._normalize_allowed_values(table_df, datapoint_df)

        # First row should be normalized, second should remain null
        assert result_df.loc[0, "DimA"] == "eba_A:a1"
        assert pd.isna(result_df.loc[1, "DimA"])

    def test_normalize_enumerated_values_in_value_column(self):
        """Test that enumerated values in the value column get normalized"""
        # This is for variables where the value itself is an enumerated code
        datapoint_df = pd.DataFrame(
            [
                {
                    "datapoint": "dp500",
                    "BAS": "x17",  # Fixed dimension value
                    "metric": "ei219",  # Fixed metric
                    "allowed_values": ["eba_CT:x1", "eba_CT:x10", "eba_CT:x20"],
                }
            ]
        )

        table_df = pd.DataFrame(
            [
                {"datapoint": "dp500", "BAS": "x17", "metric": "ei219", "value": "eba_CT0:x1"},
                {"datapoint": "dp500", "BAS": "x17", "metric": "ei219", "value": "wrong_ns:x20"},
            ]
        )

        converter = Converter.__new__(Converter)

        result_df = converter._normalize_allowed_values(table_df, datapoint_df)

        # Value column should be normalized for enumerated values
        assert result_df.loc[0, "value"] == "eba_CT:x1"
        assert result_df.loc[1, "value"] == "eba_CT:x20"

    def test_normalize_values_excludes_special_columns(self):
        """Test that columns like decimals and unit are not normalized"""
        datapoint_df = pd.DataFrame(
            [
                {
                    "datapoint": "dp500",
                    "DimA": "eba_A:a1",
                    "allowed_values": ["eba_A:a1"],
                }
            ]
        )

        table_df = pd.DataFrame(
            [
                {
                    "datapoint": "dp500",
                    "DimA": "wrong:a1",
                    "value": 12345,  # Numeric value, not enumerated
                    "decimals": 2,  # Should not be normalized
                    "unit": "EUR",  # Should not be normalized
                }
            ]
        )

        converter = Converter.__new__(Converter)

        result_df = converter._normalize_allowed_values(table_df, datapoint_df)

        # DimA should be normalized
        assert result_df.loc[0, "DimA"] == "eba_A:a1"
        # Special columns should not be touched
        assert result_df.loc[0, "value"] == 12345
        assert result_df.loc[0, "decimals"] == 2
        assert result_df.loc[0, "unit"] == "EUR"


class TestVariableAllowedValues:
    """Tests for Variable allowed_values extraction"""

    def test_variable_stores_allowed_values(self):
        """Test that Variable correctly stores allowed_values"""
        variable_dict = {
            "dimensions": {"concept": "eba_met:ei1399"},
            "eba:documentation": {
                "AllowedValue": {
                    "eba_BT:x22": {},
                    "eba_BT:x23": {},
                }
            },
        }

        variable = Variable.from_taxonomy("dp123", variable_dict)

        assert variable._allowed_values == ["eba_BT:x22", "eba_BT:x23"]

    def test_variable_empty_allowed_values(self):
        """Test that Variable handles missing AllowedValue"""
        variable_dict = {
            "dimensions": {"concept": "eba_met:ei1399"},
            "eba:documentation": {},
        }

        variable = Variable.from_taxonomy("dp123", variable_dict)

        assert variable._allowed_values == []

    def test_variable_to_dict_includes_allowed_values(self):
        """Test that Variable.to_dict() includes allowed_values"""
        variable = Variable(
            code="dp123",
            dimensions={"concept": "eba_met:ei1399"},
            attributes=None,
        )
        variable._allowed_values = ["eba_BT:x22", "eba_BT:x23"]

        result = variable.to_dict()

        assert "allowed_values" in result
        assert result["allowed_values"] == ["eba_BT:x22", "eba_BT:x23"]


class TestTableVariableDataFrame:
    """Tests for Table.generate_variable_df() with allowed_values"""

    def test_generate_variable_df_includes_allowed_values(self):
        """Test that generate_variable_df includes allowed_values column"""
        # Create a variable with allowed_values
        variable = Variable(
            code="dp123",
            dimensions={"concept": "eba_met:ei1399"},
            attributes=None,
        )
        variable._allowed_values = ["eba_BT:x22", "eba_BT:x23"]

        # Create a table with this variable
        table = Table(architecture="datapoints", variables=[variable])
        table.generate_variable_df()

        assert table.variable_df is not None
        assert "allowed_values" in table.variable_df.columns
        assert table.variable_df.loc[0, "allowed_values"] == ["eba_BT:x22", "eba_BT:x23"]
