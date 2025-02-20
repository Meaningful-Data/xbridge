"""
Test that EBA samples are transformed correctly
"""

from pathlib import Path

import pytest

from ._base_test import BasicConversionTest, FullConversionTest

INPUT_PATH_3_2p1 = Path(__file__).parent / "test_files" / "sample_3_2_phase1"
INPUT_PATH_3_2p3 = Path(__file__).parent / "test_files" / "sample_3_2_phase3"
INPUT_PATH_3_3 = Path(__file__).parent / "test_files" / "sample_3_3"

params_full = [
    (INPUT_PATH_3_2p3 / "test1_in.xbrl", INPUT_PATH_3_2p3 / "test1_out.zip"),
    (INPUT_PATH_3_2p3 / "test3_in.xbrl", INPUT_PATH_3_2p3 / "test3_out.zip"),
    (INPUT_PATH_3_2p3 / "test4_in.xbrl", INPUT_PATH_3_2p3 / "test4_out.zip"),
]

params_basic = [
    (INPUT_PATH_3_2p3 / "test2_in.xbrl", INPUT_PATH_3_2p3 / "test2_out.zip"),
    (INPUT_PATH_3_2p3 / "test5_in.xbrl", INPUT_PATH_3_2p3 / "test5_out.zip"),
    (INPUT_PATH_3_3 / "test1_in.xbrl", INPUT_PATH_3_3 / "test1_out.zip"),
    (INPUT_PATH_3_2p1 / "test1_in.xbrl", INPUT_PATH_3_2p1 / "test1_out.zip"),
]

@pytest.mark.parametrize("instance_path, expected_output_path", params_full)
def test_full(instance_path, expected_output_path):
    test_full_obj = FullConversionTest()
    test_full_obj.instance_path = instance_path
    test_full_obj.expected_output_path = expected_output_path
    test_full_obj.setup_method(None)


@pytest.mark.parametrize("instance_path, expected_output_path", params_basic)
def test_basic(instance_path, expected_output_path):
    test_basic_obj = BasicConversionTest()
    test_basic_obj.instance_path = instance_path
    test_basic_obj.expected_output_path = expected_output_path
    test_basic_obj.setup_method(None)
