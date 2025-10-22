"""
Test filing indicator validation functionality
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from xbridge.converter import Converter
from xbridge.modules import Table
from xbridge.xml_instance import FilingIndicator


class TestFilingIndicatorValidation:
    """Tests for filing indicator validation"""

    def test_validation_passes_when_no_facts_for_false_indicators(self):
        """Test that validation passes when tables with false filing indicators have no facts"""
        with TemporaryDirectory() as tmp_dir:
            # This test would require a valid XBRL file with proper structure
            # For now, we'll test the logic using mocks
            pass

    def test_validation_fails_when_facts_exist_for_false_indicators(self):
        """Test that validation raises ValueError when tables with false filing indicators have facts"""
        # Create a mock converter with false filing indicators and facts
        with patch('xbridge.converter.Instance') as mock_instance_class:
            with patch('xbridge.converter.Module') as mock_module_class:
                # Setup mock instance
                mock_instance = MagicMock()
                mock_instance_class.return_value = mock_instance
                mock_instance.module_ref = "test_module"

                # Create a false filing indicator
                false_filing_ind = MagicMock(spec=FilingIndicator)
                false_filing_ind.value = False
                false_filing_ind.table = "C.01.00"

                mock_instance.filing_indicators = [false_filing_ind]
                mock_instance.instance_df = pd.DataFrame({
                    'datapoint': ['dp1', 'dp2'],
                    'value': [100, 200]
                })

                # Setup mock module
                mock_module = MagicMock()
                mock_module_class.from_serialized.return_value = mock_module

                # Create a mock table that corresponds to the false filing indicator
                mock_table = MagicMock(spec=Table)
                mock_table.filing_indicator_code = "C.01.00"
                mock_table.variable_columns = []
                mock_table.open_keys = []
                mock_table.attributes = []

                mock_module.tables = [mock_table]

                # Create converter (this will use our mocked Instance and Module)
                with TemporaryDirectory() as tmp_dir:
                    test_file = Path(tmp_dir) / "test.xbrl"
                    test_file.write_text('<?xml version="1.0"?><xbrl></xbrl>')

                    with patch('xbridge.converter.INDEX_FILE', Path(__file__).parent.parent / "src" / "xbridge" / "modules" / "index.json"):
                        with patch('xbridge.converter.index', {"test_module": "test.json"}):
                            converter = Converter(test_file)
                            converter._reported_tables = []  # No tables reported (false filing indicator)

                            # Simulate that facts were tracked from a skipped table
                            converter._skipped_tables_facts = {
                                'C.01.00': [
                                    (('datapoint', 'dp1'),),
                                ]
                            }
                            # No facts were converted (empty set)
                            converter._converted_facts = set()

                            # The validation should raise a ValueError
                            with pytest.raises(ValueError, match="Filing indicator validation failed"):
                                converter._validate_filing_indicators()

    def test_validation_passes_when_all_indicators_true(self):
        """Test that validation passes when all filing indicators are true"""
        with patch('xbridge.converter.Instance') as mock_instance_class:
            with patch('xbridge.converter.Module') as mock_module_class:
                # Setup mock instance
                mock_instance = MagicMock()
                mock_instance_class.return_value = mock_instance
                mock_instance.module_ref = "test_module"

                # Create a true filing indicator
                true_filing_ind = MagicMock(spec=FilingIndicator)
                true_filing_ind.value = True
                true_filing_ind.table = "C.01.00"

                mock_instance.filing_indicators = [true_filing_ind]

                # Setup mock module
                mock_module = MagicMock()
                mock_module_class.from_serialized.return_value = mock_module
                mock_module.tables = []

                # Create converter
                with TemporaryDirectory() as tmp_dir:
                    test_file = Path(tmp_dir) / "test.xbrl"
                    test_file.write_text('<?xml version="1.0"?><xbrl></xbrl>')

                    with patch('xbridge.converter.INDEX_FILE', Path(__file__).parent.parent / "src" / "xbridge" / "modules" / "index.json"):
                        with patch('xbridge.converter.index', {"test_module": "test.json"}):
                            converter = Converter(test_file)
                            converter._reported_tables = ["C.01.00"]

                            # The validation should not raise any error
                            converter._validate_filing_indicators()  # Should pass without error

    def test_validation_passes_when_no_filing_indicators(self):
        """Test that validation passes when there are no filing indicators"""
        with patch('xbridge.converter.Instance') as mock_instance_class:
            with patch('xbridge.converter.Module') as mock_module_class:
                # Setup mock instance
                mock_instance = MagicMock()
                mock_instance_class.return_value = mock_instance
                mock_instance.module_ref = "test_module"
                mock_instance.filing_indicators = None

                # Setup mock module
                mock_module = MagicMock()
                mock_module_class.from_serialized.return_value = mock_module

                # Create converter
                with TemporaryDirectory() as tmp_dir:
                    test_file = Path(tmp_dir) / "test.xbrl"
                    test_file.write_text('<?xml version="1.0"?><xbrl></xbrl>')

                    with patch('xbridge.converter.INDEX_FILE', Path(__file__).parent.parent / "src" / "xbridge" / "modules" / "index.json"):
                        with patch('xbridge.converter.index', {"test_module": "test.json"}):
                            converter = Converter(test_file)

                            # The validation should not raise any error
                            converter._validate_filing_indicators()  # Should pass without error

    def test_error_message_includes_table_and_fact_count(self):
        """Test that error message includes table code and fact count"""
        with patch('xbridge.converter.Instance') as mock_instance_class:
            with patch('xbridge.converter.Module') as mock_module_class:
                # Setup mock instance
                mock_instance = MagicMock()
                mock_instance_class.return_value = mock_instance
                mock_instance.module_ref = "test_module"

                # Create false filing indicators
                false_filing_ind1 = MagicMock(spec=FilingIndicator)
                false_filing_ind1.value = False
                false_filing_ind1.table = "C.01.00"

                false_filing_ind2 = MagicMock(spec=FilingIndicator)
                false_filing_ind2.value = False
                false_filing_ind2.table = "C.02.00"

                mock_instance.filing_indicators = [false_filing_ind1, false_filing_ind2]

                # Setup mock module
                mock_module = MagicMock()
                mock_module_class.from_serialized.return_value = mock_module

                # Create mock tables
                mock_table1 = MagicMock(spec=Table)
                mock_table1.filing_indicator_code = "C.01.00"
                mock_table1.variable_columns = []
                mock_table1.open_keys = []
                mock_table1.attributes = []

                mock_table2 = MagicMock(spec=Table)
                mock_table2.filing_indicator_code = "C.02.00"
                mock_table2.variable_columns = []
                mock_table2.open_keys = []
                mock_table2.attributes = []

                mock_module.tables = [mock_table1, mock_table2]

                # Create converter
                with TemporaryDirectory() as tmp_dir:
                    test_file = Path(tmp_dir) / "test.xbrl"
                    test_file.write_text('<?xml version="1.0"?><xbrl></xbrl>')

                    with patch('xbridge.converter.INDEX_FILE', Path(__file__).parent.parent / "src" / "xbridge" / "modules" / "index.json"):
                        with patch('xbridge.converter.index', {"test_module": "test.json"}):
                            converter = Converter(test_file)
                            converter._reported_tables = []

                            # Simulate tracked facts from skipped tables
                            converter._skipped_tables_facts = {
                                'C.01.00': [
                                    (('datapoint', 'dp1'),),
                                    (('datapoint', 'dp2'),),
                                ],
                                'C.02.00': [
                                    (('datapoint', 'dp3'),),
                                    (('datapoint', 'dp4'),),
                                    (('datapoint', 'dp5'),),
                                ]
                            }
                            # No facts were converted
                            converter._converted_facts = set()

                            # Check that error message contains both tables and their fact counts
                            with pytest.raises(ValueError) as exc_info:
                                converter._validate_filing_indicators()

                            error_msg = str(exc_info.value)
                            assert "C.01.00" in error_msg
                            assert "2 fact(s)" in error_msg
                            assert "C.02.00" in error_msg
                            assert "3 fact(s)" in error_msg

    def test_no_error_when_facts_shared_across_tables(self):
        """Test that validation passes when facts in false-indicator tables are also in true-indicator tables"""
        with patch('xbridge.converter.Instance') as mock_instance_class:
            with patch('xbridge.converter.Module') as mock_module_class:
                # Setup mock instance
                mock_instance = MagicMock()
                mock_instance_class.return_value = mock_instance
                mock_instance.module_ref = "test_module"

                # Create filing indicators - one true, one false
                true_filing_ind = MagicMock(spec=FilingIndicator)
                true_filing_ind.value = True
                true_filing_ind.table = "C.01.00"

                false_filing_ind = MagicMock(spec=FilingIndicator)
                false_filing_ind.value = False
                false_filing_ind.table = "C.02.00"

                mock_instance.filing_indicators = [true_filing_ind, false_filing_ind]

                # Setup mock module
                mock_module = MagicMock()
                mock_module_class.from_serialized.return_value = mock_module

                # Create mock tables
                mock_table1 = MagicMock(spec=Table)
                mock_table1.filing_indicator_code = "C.01.00"
                mock_table1.variable_columns = []
                mock_table1.open_keys = []
                mock_table1.attributes = []

                mock_table2 = MagicMock(spec=Table)
                mock_table2.filing_indicator_code = "C.02.00"
                mock_table2.variable_columns = []
                mock_table2.open_keys = []
                mock_table2.attributes = []

                mock_module.tables = [mock_table1, mock_table2]

                # Create converter
                with TemporaryDirectory() as tmp_dir:
                    test_file = Path(tmp_dir) / "test.xbrl"
                    test_file.write_text('<?xml version="1.0"?><xbrl></xbrl>')

                    with patch('xbridge.converter.INDEX_FILE', Path(__file__).parent.parent / "src" / "xbridge" / "modules" / "index.json"):
                        with patch('xbridge.converter.index', {"test_module": "test.json"}):
                            converter = Converter(test_file)
                            converter._reported_tables = ["C.01.00"]  # Only table 1 is reported

                            # Simulate that the same facts were tracked in both tables
                            shared_facts = [
                                (('datapoint', 'dp1'), ('metric', 'm1')),
                                (('datapoint', 'dp2'), ('metric', 'm2')),
                            ]

                            # These facts were converted from table C.01.00
                            converter._converted_facts = set(shared_facts)

                            # The same facts were in skipped table C.02.00
                            converter._skipped_tables_facts = {
                                'C.02.00': shared_facts
                            }

                            # The validation should NOT raise an error because all facts
                            # from table C.02.00 are also in table C.01.00 (which is reported)
                            converter._validate_filing_indicators()  # Should pass without error

    def test_error_when_only_some_facts_shared_across_tables(self):
        """Test that validation fails only for orphaned facts when tables share some but not all facts"""
        with patch('xbridge.converter.Instance') as mock_instance_class:
            with patch('xbridge.converter.Module') as mock_module_class:
                # Setup mock instance
                mock_instance = MagicMock()
                mock_instance_class.return_value = mock_instance
                mock_instance.module_ref = "test_module"

                # Create filing indicators - one true, one false
                true_filing_ind = MagicMock(spec=FilingIndicator)
                true_filing_ind.value = True
                true_filing_ind.table = "C.01.00"

                false_filing_ind = MagicMock(spec=FilingIndicator)
                false_filing_ind.value = False
                false_filing_ind.table = "C.02.00"

                mock_instance.filing_indicators = [true_filing_ind, false_filing_ind]

                # Setup mock module
                mock_module = MagicMock()
                mock_module_class.from_serialized.return_value = mock_module

                # Create mock tables
                mock_table1 = MagicMock(spec=Table)
                mock_table1.filing_indicator_code = "C.01.00"
                mock_table1.variable_columns = []
                mock_table1.open_keys = []
                mock_table1.attributes = []

                mock_table2 = MagicMock(spec=Table)
                mock_table2.filing_indicator_code = "C.02.00"
                mock_table2.variable_columns = []
                mock_table2.open_keys = []
                mock_table2.attributes = []

                mock_module.tables = [mock_table1, mock_table2]

                # Create converter
                with TemporaryDirectory() as tmp_dir:
                    test_file = Path(tmp_dir) / "test.xbrl"
                    test_file.write_text('<?xml version="1.0"?><xbrl></xbrl>')

                    with patch('xbridge.converter.INDEX_FILE', Path(__file__).parent.parent / "src" / "xbridge" / "modules" / "index.json"):
                        with patch('xbridge.converter.index', {"test_module": "test.json"}):
                            converter = Converter(test_file)
                            converter._reported_tables = ["C.01.00"]  # Only table 1 is reported

                            # Simulate partially overlapping facts
                            shared_facts = [
                                (('datapoint', 'dp1'), ('metric', 'm1')),
                                (('datapoint', 'dp2'), ('metric', 'm2')),
                            ]
                            orphaned_facts = [
                                (('datapoint', 'dp3'), ('metric', 'm3')),
                                (('datapoint', 'dp4'), ('metric', 'm4')),
                            ]

                            # Only shared facts were converted from table C.01.00
                            converter._converted_facts = set(shared_facts)

                            # Table C.02.00 has both shared and orphaned facts
                            converter._skipped_tables_facts = {
                                'C.02.00': shared_facts + orphaned_facts
                            }

                            # The validation should raise an error for the 2 orphaned facts
                            with pytest.raises(ValueError) as exc_info:
                                converter._validate_filing_indicators()

                            error_msg = str(exc_info.value)
                            # Should mention table C.02.00
                            assert "C.02.00" in error_msg
                            # Should indicate 2 out of 4 facts would be lost
                            assert "2 of 4" in error_msg
                            assert "would be lost" in error_msg
