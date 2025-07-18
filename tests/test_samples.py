"""
Test that EBA samples are transformed correctly
"""

from pathlib import Path
from zipfile import ZipFile

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

    zip_file_path = test_full_obj.generated_output_path

    with ZipFile(zip_file_path, "r") as z:
        entries = z.namelist()
        root_folders = {entry.split("/")[0] for entry in entries if "/" in entry}

        assert len(root_folders) == 1, "ZIP file should contain one root folder"
        root_folder = root_folders.pop()

        subfolders = {"/".join(entry.split("/")[:2]) for entry in entries if "/" in entry}
        expected_subfolders = {f"{root_folder}/META-INF", f"{root_folder}/reports"}
        for folder in expected_subfolders:
            assert folder in subfolders, f"{folder} folder is left in ZIP file"


@pytest.mark.parametrize("instance_path, expected_output_path", params_basic)
def test_basic(instance_path, expected_output_path):
    test_basic_obj = BasicConversionTest()
    test_basic_obj.instance_path = instance_path
    test_basic_obj.expected_output_path = expected_output_path
    test_basic_obj.setup_method(None)

    zip_file_path = test_basic_obj.generated_output_path

    with ZipFile(zip_file_path, "r") as z:
        entries = z.namelist()
        root_folders = {entry.split("/")[0] for entry in entries if "/" in entry}

        assert len(root_folders) == 1, "ZIP file should contain one root folder"
        root_folder = root_folders.pop()

        subfolders = {"/".join(entry.split("/")[:2]) for entry in entries if "/" in entry}
        expected_subfolders = {f"{root_folder}/META-INF", f"{root_folder}/reports"}
        for folder in expected_subfolders:
            assert folder in subfolders, f"{folder} folder is left in ZIP file"
