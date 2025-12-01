"""
Test that EBA samples are transformed correctly
"""

from pathlib import Path

import pytest

from ._base_test import BasicConversionTest, FullConversionTest

INPUT_PATH_3_2p1 = Path(__file__).parent / "test_files" / "sample_3_2_phase1"
INPUT_PATH_3_2p3 = Path(__file__).parent / "test_files" / "sample_3_2_phase3"
INPUT_PATH_3_3 = Path(__file__).parent / "test_files" / "sample_3_3"
INPUT_PATH_DORA = Path(__file__).parent / "test_files" / "sample_dora"

params_full = [
    (INPUT_PATH_3_2p3 / "test1_in.xbrl", INPUT_PATH_3_2p3 / "test1_out.zip"),
    (INPUT_PATH_3_2p3 / "test3_in.xbrl", INPUT_PATH_3_2p3 / "test3_out.zip"),
    (INPUT_PATH_3_2p3 / "test4_in.xbrl", INPUT_PATH_3_2p3 / "test4_out.zip"),
    (INPUT_PATH_DORA / "test1_in.xbrl", INPUT_PATH_DORA / "test1_out.zip"),
]

params_basic = [
    (INPUT_PATH_3_2p3 / "test2_in.xbrl", INPUT_PATH_3_2p3 / "test2_out.zip"),
    (INPUT_PATH_3_2p3 / "test5_in.xbrl", INPUT_PATH_3_2p3 / "test5_out.zip"),
    (INPUT_PATH_3_3 / "test1_in.xbrl", INPUT_PATH_3_3 / "test1_out.zip"),
    (INPUT_PATH_3_2p1 / "test1_in.xbrl", INPUT_PATH_3_2p1 / "test1_out.zip"),
]


@pytest.mark.parametrize("instance_path, expected_output_path", params_full)
def test_full(instance_path, expected_output_path):
    """
    Comprehensive test for full conversion samples.
    Verifies that the conversion result matches the expected output exactly.
    """
    test_full_obj = FullConversionTest()
    test_full_obj.instance_path = instance_path
    test_full_obj.expected_output_path = expected_output_path
    test_full_obj.setup_method(None)

    try:
        # Run all test methods from FullConversionTest
        test_full_obj.test_file_created()
        test_full_obj.test_file_structure()
        test_full_obj.test_number_facts()
        test_full_obj.test_files_same_structure()
        test_full_obj.test_all_expected_files_present()
        test_full_obj.test_reports_file()
        test_full_obj.test_same_report_files()
        test_full_obj.test_files_same_size()
        test_full_obj.test_number_filing_indicators()
        test_full_obj.test_all_files_identical()
        test_full_obj.test_all_zip_files_match()
    finally:
        test_full_obj.teardown_method(None)


@pytest.mark.parametrize("instance_path, expected_output_path", params_basic)
def test_basic(instance_path, expected_output_path):
    """
    Comprehensive test for basic conversion samples.
    Verifies file structure, number of facts, and column consistency.
    """
    test_basic_obj = BasicConversionTest()
    test_basic_obj.instance_path = instance_path
    test_basic_obj.expected_output_path = expected_output_path
    test_basic_obj.setup_method(None)

    try:
        # Run all test methods from BasicConversionTest
        test_basic_obj.test_file_created()
        test_basic_obj.test_file_structure()
        test_basic_obj.test_number_facts()
        test_basic_obj.test_files_same_structure()
        test_basic_obj.test_all_expected_files_present()
    finally:
        test_basic_obj.teardown_method(None)
