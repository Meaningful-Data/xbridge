"""
Test that EBA samples are transformed correctly
"""

import unittest
from pathlib import Path

from test_samples_base import (TestInstanceConversionBasic,
                                               TestInstanceConversionFull)


INPUT_PATH_3_2p3 = Path(__file__).parent / "test_files" / "sample_3_2_phase3"
INPUT_PATH_3_3 = Path(__file__).parent / "test_files" / "sample_3_3"


class TestCase1(TestInstanceConversionFull):
    """
    File 1
    """

    def setUp(self):
        super().setUp(
            instance_path=INPUT_PATH_3_2p3 / "test1_in.xbrl",
            expected_output_path=INPUT_PATH_3_2p3 / "test1_out.zip",
        )


class TestCase2(TestInstanceConversionBasic):
    def setUp(self):
        super().setUp(
            instance_path=INPUT_PATH_3_2p3 / "test2_in.xbrl",
            expected_output_path=INPUT_PATH_3_2p3 / "test2_out.zip",
        )


class TestCase3(TestInstanceConversionFull):
    def setUp(self):
        super().setUp(
            instance_path=INPUT_PATH_3_2p3 / "test3_in.xbrl",
            expected_output_path=INPUT_PATH_3_2p3 / "test3_out.zip",
        )


class TestCase4(TestInstanceConversionFull):
    def setUp(self):
        super().setUp(
            instance_path=INPUT_PATH_3_2p3 / "test4_in.xbrl",
            expected_output_path=INPUT_PATH_3_2p3 / "test4_out.zip",
        )


class TestCase5(TestInstanceConversionBasic):
    def setUp(self):
        super().setUp(
            instance_path=INPUT_PATH_3_2p3 / "test5_in.xbrl",
            expected_output_path=INPUT_PATH_3_2p3 / "test5_out.zip",
        )


class TestCase6(TestInstanceConversionBasic):
    def setUp(self):
        super().setUp(
            instance_path=INPUT_PATH_3_3 / "test1_in.xbrl",
            expected_output_path=INPUT_PATH_3_3 / "test1_out.zip",
        )


if __name__ == "__main__":
    unittest.main()
