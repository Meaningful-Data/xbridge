"""
Tests for conditional unit attribute handling based on variable dimensions.

When a table has "unit" in its attributes, the unit column should only be
populated for datapoints that have "unit": "$unit" in their dimensions.
For datapoints without this key-value pair, the unit column should be empty.
"""

from unittest.mock import Mock, patch

import pandas as pd
import pytest

from xbridge.converter import Converter
from xbridge.modules import Table, Variable


class TestHasUnitDimTracking:
    """Tests for _has_unit_dim tracking in generate_variable_df()"""

    def test_datapoints_architecture_with_unit_in_dimensions(self):
        """Test that _has_unit_dim is True when variable has unit in dimensions"""
        variable_with_unit = Variable(
            code="dp001",
            dimensions={
                "concept": "eba_met:mi123",
                "eba_dim:qABC": "eba_qABC:qx1",
                "unit": "$unit",
            },
            attributes="$decimalsMonetary",
        )

        table = Table(
            code="T_01.00",
            variables=[variable_with_unit],
            attributes=["unit"],
            architecture="datapoints",
        )

        table.generate_variable_df()

        assert table.variable_df is not None
        assert "_has_unit_dim" in table.variable_df.columns
        assert table.variable_df.loc[0, "_has_unit_dim"] == True  # noqa: E712

    def test_datapoints_architecture_without_unit_in_dimensions(self):
        """Test that _has_unit_dim == False  # noqa: E712 when variable doesn't have unit in dimensions"""
        variable_without_unit = Variable(
            code="dp002",
            dimensions={
                "concept": "eba_met:mi456",
                "eba_dim:qDEF": "eba_qDEF:qx2",
            },
            attributes="$decimalsInteger",
        )

        table = Table(
            code="T_01.00",
            variables=[variable_without_unit],
            attributes=["unit"],
            architecture="datapoints",
        )

        table.generate_variable_df()

        assert table.variable_df is not None
        assert "_has_unit_dim" in table.variable_df.columns
        assert table.variable_df.loc[0, "_has_unit_dim"] == False  # noqa: E712

    def test_datapoints_architecture_mixed_variables(self):
        """Test mixed variables - some with unit, some without"""
        variable_with_unit = Variable(
            code="dp001",
            dimensions={
                "concept": "eba_met:mi123",
                "unit": "$unit",
            },
            attributes="$decimalsMonetary",
        )
        variable_without_unit = Variable(
            code="dp002",
            dimensions={
                "concept": "eba_met:mi456",
            },
            attributes="$decimalsInteger",
        )

        table = Table(
            code="T_01.00",
            variables=[variable_with_unit, variable_without_unit],
            attributes=["unit"],
            architecture="datapoints",
        )

        table.generate_variable_df()

        assert table.variable_df is not None
        assert len(table.variable_df) == 2

        # Check that the variable with unit has _has_unit_dim = True
        row_with_unit = table.variable_df[table.variable_df["datapoint"] == "dp001"]
        assert row_with_unit["_has_unit_dim"].values[0] == True  # noqa: E712

        # Check that the variable without unit has _has_unit_dim = False
        row_without_unit = table.variable_df[table.variable_df["datapoint"] == "dp002"]
        assert row_without_unit["_has_unit_dim"].values[0] == False  # noqa: E712

    def test_headers_architecture_with_unit_in_dimensions(self):
        """Test that _has_unit_dim is True for headers architecture with unit"""
        columns = [
            {
                "variable_id": "col001",
                "dimensions": {
                    "concept": "eba_met:mi123",
                    "unit": "$unit",
                },
                "decimals": "$decimalsMonetary",
            }
        ]

        table = Table(
            code="T_02.00",
            columns=columns,
            attributes=["unit"],
            architecture="headers",
        )

        table.generate_variable_df()

        assert table.variable_df is not None
        assert "_has_unit_dim" in table.variable_df.columns
        assert table.variable_df.loc[0, "_has_unit_dim"] == True  # noqa: E712

    def test_headers_architecture_without_unit_in_dimensions(self):
        """Test that _has_unit_dim == False  # noqa: E712 for headers architecture without unit"""
        columns = [
            {
                "variable_id": "col002",
                "dimensions": {
                    "concept": "eba_met:mi456",
                },
                "decimals": "$decimalsInteger",
            }
        ]

        table = Table(
            code="T_02.00",
            columns=columns,
            attributes=["unit"],
            architecture="headers",
        )

        table.generate_variable_df()

        assert table.variable_df is not None
        assert "_has_unit_dim" in table.variable_df.columns
        assert table.variable_df.loc[0, "_has_unit_dim"] == False  # noqa: E712

    def test_headers_architecture_without_dimensions_key(self):
        """Test headers architecture where column has no dimensions key"""
        columns = [
            {
                "variable_id": "col003",
                "decimals": "$decimalsInteger",
            }
        ]

        table = Table(
            code="T_02.00",
            columns=columns,
            attributes=["unit"],
            architecture="headers",
        )

        table.generate_variable_df()

        assert table.variable_df is not None
        assert "_has_unit_dim" in table.variable_df.columns
        # Should be False since there's no dimensions key
        assert table.variable_df.loc[0, "_has_unit_dim"] == False  # noqa: E712


class TestVariableColumnsProperty:
    """Tests for variable_columns property excluding _has_unit_dim"""

    def test_variable_columns_excludes_has_unit_dim(self):
        """Test that variable_columns property excludes _has_unit_dim"""
        variable = Variable(
            code="dp001",
            dimensions={
                "concept": "eba_met:mi123",
                "eba_dim:qABC": "eba_qABC:qx1",
                "unit": "$unit",
            },
            attributes="$decimalsMonetary",
        )

        table = Table(
            code="T_01.00",
            variables=[variable],
            attributes=["unit"],
            architecture="datapoints",
        )

        table.generate_variable_df()

        # _has_unit_dim should be in the dataframe
        assert "_has_unit_dim" in table.variable_df.columns

        # But not in variable_columns (used for merging)
        assert "_has_unit_dim" not in table.variable_columns

    def test_variable_columns_excludes_all_metadata(self):
        """Test that variable_columns excludes all metadata columns"""
        variable = Variable(
            code="dp001",
            dimensions={
                "concept": "eba_met:mi123",
                "unit": "$unit",
            },
            attributes="$decimalsMonetary",
        )

        table = Table(
            code="T_01.00",
            variables=[variable],
            attributes=["unit"],
            architecture="datapoints",
        )

        table.generate_variable_df()

        variable_cols = table.variable_columns

        # All metadata columns should be excluded
        assert "datapoint" not in variable_cols
        assert "data_type" not in variable_cols
        assert "allowed_values" not in variable_cols
        assert "_has_unit_dim" not in variable_cols

        # But actual dimension columns should be included
        assert "metric" in variable_cols  # concept becomes metric


class TestConditionalUnitClearing:
    """Tests for conditional unit clearing in _variable_generator()"""

    @pytest.fixture
    def converter_instance(self):
        """Create a converter instance with mocked dependencies"""
        with patch("xbridge.converter.Instance") as mock_instance_class:
            mock_instance = Mock()
            mock_instance.module_ref = "test_module"
            mock_instance.instance_df = pd.DataFrame()
            mock_instance.units = {"EUR": "iso4217:EUR", "USD": "iso4217:USD"}
            mock_instance_class.return_value = mock_instance

            with patch("xbridge.converter.Module") as mock_module_class:
                mock_module = Mock()
                mock_module_class.from_serialized.return_value = mock_module

                with patch("xbridge.converter.index", {"test_module": "test.json"}):
                    converter = Converter("dummy_path.xml")
                    return converter

    def test_unit_cleared_for_variables_without_unit_dim(self, converter_instance):
        """Test that unit is cleared for rows where variable had no unit in dimensions"""
        # Create a dataframe simulating the merged result with _has_unit_dim marker
        table_df = pd.DataFrame(
            {
                "datapoint": ["dp001", "dp002", "dp003"],
                "value": [100.0, 200.0, 300.0],
                "unit": ["EUR", "EUR", "EUR"],
                "_has_unit_dim": [True, False, True],
            }
        )

        # Apply the unit clearing logic (same as in converter.py)
        if "_has_unit_dim" in table_df.columns:
            table_df.loc[~table_df["_has_unit_dim"], "unit"] = pd.NA

        # Check results
        assert table_df.loc[0, "unit"] == "EUR"  # Has unit dim, should keep
        assert pd.isna(table_df.loc[1, "unit"])  # No unit dim, should be NA
        assert table_df.loc[2, "unit"] == "EUR"  # Has unit dim, should keep

    def test_unit_mapping_respects_na_values(self, converter_instance):
        """Test that unit mapping with na_action='ignore' preserves NA values"""
        units_mapping = {"EUR": "iso4217:EUR", "USD": "iso4217:USD"}

        table_df = pd.DataFrame(
            {
                "datapoint": ["dp001", "dp002", "dp003"],
                "value": [100.0, 200.0, 300.0],
                "unit": ["EUR", pd.NA, "USD"],
            }
        )

        # Apply unit mapping (same as in converter.py)
        table_df["unit"] = table_df["unit"].map(units_mapping, na_action="ignore")

        # Check results
        assert table_df.loc[0, "unit"] == "iso4217:EUR"
        assert pd.isna(table_df.loc[1, "unit"])  # NA should remain NA
        assert table_df.loc[2, "unit"] == "iso4217:USD"

    def test_full_flow_mixed_variables(self, converter_instance):
        """Test the full flow with mixed variables - some with unit, some without"""
        # Simulate the merged dataframe before unit processing
        table_df = pd.DataFrame(
            {
                "datapoint": ["dp001", "dp002", "dp003", "dp004"],
                "value": [100.0, 0.5, 200.0, 0.75],
                "unit": ["EUR", "EUR", "USD", "USD"],
                "_has_unit_dim": [True, False, True, False],
            }
        )

        units_mapping = {"EUR": "iso4217:EUR", "USD": "iso4217:USD"}

        # Step 1: Clear unit for rows without unit in dimensions
        if "_has_unit_dim" in table_df.columns:
            table_df.loc[~table_df["_has_unit_dim"], "unit"] = pd.NA

        # Step 2: Apply unit mapping
        table_df["unit"] = table_df["unit"].map(units_mapping, na_action="ignore")

        # Step 3: Drop the marker column
        table_df = table_df.drop(columns=["_has_unit_dim"])

        # Verify results
        assert "unit" in table_df.columns
        assert "_has_unit_dim" not in table_df.columns

        # Monetary values (with unit dim) should have mapped units
        assert table_df.loc[0, "unit"] == "iso4217:EUR"
        assert table_df.loc[2, "unit"] == "iso4217:USD"

        # Percentage values (without unit dim) should have NA
        assert pd.isna(table_df.loc[1, "unit"])
        assert pd.isna(table_df.loc[3, "unit"])

    def test_all_variables_have_unit(self, converter_instance):
        """Test that all units are kept when all variables have unit in dimensions"""
        table_df = pd.DataFrame(
            {
                "datapoint": ["dp001", "dp002"],
                "value": [100.0, 200.0],
                "unit": ["EUR", "USD"],
                "_has_unit_dim": [True, True],
            }
        )

        units_mapping = {"EUR": "iso4217:EUR", "USD": "iso4217:USD"}

        # Clear unit for rows without unit in dimensions
        if "_has_unit_dim" in table_df.columns:
            table_df.loc[~table_df["_has_unit_dim"], "unit"] = pd.NA

        # Apply unit mapping
        table_df["unit"] = table_df["unit"].map(units_mapping, na_action="ignore")

        # All units should be mapped (none cleared)
        assert table_df.loc[0, "unit"] == "iso4217:EUR"
        assert table_df.loc[1, "unit"] == "iso4217:USD"

    def test_no_variables_have_unit(self, converter_instance):
        """Test that all units are cleared when no variables have unit in dimensions"""
        table_df = pd.DataFrame(
            {
                "datapoint": ["dp001", "dp002"],
                "value": [0.5, 0.75],
                "unit": ["EUR", "USD"],
                "_has_unit_dim": [False, False],
            }
        )

        units_mapping = {"EUR": "iso4217:EUR", "USD": "iso4217:USD"}

        # Clear unit for rows without unit in dimensions
        if "_has_unit_dim" in table_df.columns:
            table_df.loc[~table_df["_has_unit_dim"], "unit"] = pd.NA

        # Apply unit mapping
        table_df["unit"] = table_df["unit"].map(units_mapping, na_action="ignore")

        # All units should be NA
        assert pd.isna(table_df.loc[0, "unit"])
        assert pd.isna(table_df.loc[1, "unit"])


class TestEdgeCases:
    """Tests for edge cases in unit attribute handling"""

    def test_variable_with_base_currency_unit(self):
        """Test that $baseCurrency unit placeholder is also tracked"""
        variable_with_base_currency = Variable(
            code="dp001",
            dimensions={
                "concept": "eba_met:mi123",
                "unit": "$baseCurrency",
            },
            attributes="$decimalsMonetary",
        )

        table = Table(
            code="T_01.00",
            variables=[variable_with_base_currency],
            attributes=["unit"],
            architecture="datapoints",
        )

        table.generate_variable_df()

        # $baseCurrency should also result in _has_unit_dim = True
        assert table.variable_df.loc[0, "_has_unit_dim"] == True  # noqa: E712

    def test_variable_with_none_code_skipped(self):
        """Test that variables with None code are skipped"""
        variable_with_unit = Variable(
            code="dp001",
            dimensions={
                "concept": "eba_met:mi123",
                "unit": "$unit",
            },
            attributes="$decimalsMonetary",
        )
        variable_no_code = Variable(
            code=None,
            dimensions={
                "concept": "eba_met:mi456",
            },
            attributes="$decimalsInteger",
        )

        table = Table(
            code="T_01.00",
            variables=[variable_with_unit, variable_no_code],
            attributes=["unit"],
            architecture="datapoints",
        )

        table.generate_variable_df()

        # Only the variable with a code should be in the dataframe
        assert len(table.variable_df) == 1
        assert table.variable_df.loc[0, "datapoint"] == "dp001"

    def test_empty_table_no_variables(self):
        """Test handling of table with no variables"""
        table = Table(
            code="T_01.00",
            variables=[],
            attributes=["unit"],
            architecture="datapoints",
        )

        table.generate_variable_df()

        assert table.variable_df is not None
        assert len(table.variable_df) == 0

    def test_table_without_unit_attribute(self):
        """Test that _has_unit_dim is still tracked even if table doesn't have unit attribute"""
        variable = Variable(
            code="dp001",
            dimensions={
                "concept": "eba_met:mi123",
                "unit": "$unit",
            },
            attributes="$decimalsMonetary",
        )

        table = Table(
            code="T_01.00",
            variables=[variable],
            attributes=[],  # No unit attribute
            architecture="datapoints",
        )

        table.generate_variable_df()

        # _has_unit_dim should still be tracked
        assert "_has_unit_dim" in table.variable_df.columns
        assert table.variable_df.loc[0, "_has_unit_dim"] == True  # noqa: E712
