"""
Test that EBA samples are transformed correctly
"""

from pathlib import Path

from .test_samples_base import TestInstanceConversionBasic, TestInstanceConversionFull

INPUT_PATH_3_2p1 = Path(__file__).parent / "test_files" / "sample_3_2_phase1"
INPUT_PATH_3_2p3 = Path(__file__).parent / "test_files" / "sample_3_2_phase3"
INPUT_PATH_3_3 = Path(__file__).parent / "test_files" / "sample_3_3"


class TestCase1(TestInstanceConversionFull):
    """
    File 1
    """

    def setup_method(self, method):
        self.instance_path = INPUT_PATH_3_2p3 / "test1_in.xbrl"
        self.expected_output_path = INPUT_PATH_3_2p3 / "test1_out.zip"
        super().setup_method(method)


class TestCase2(TestInstanceConversionBasic):
    def setup_method(self, method):
        self.instance_path = INPUT_PATH_3_2p3 / "test2_in.xbrl"
        self.expected_output_path = INPUT_PATH_3_2p3 / "test2_out.zip"
        super().setup_method(method)


class TestCase3(TestInstanceConversionFull):
    def setup_method(self, method):
        self.instance_path = INPUT_PATH_3_2p3 / "test3_in.xbrl"
        self.expected_output_path = INPUT_PATH_3_2p3 / "test3_out.zip"
        super().setup_method(method)


class TestCase4(TestInstanceConversionFull):
    def setup_method(self, method):
        self.instance_path = INPUT_PATH_3_2p3 / "test4_in.xbrl"
        self.expected_output_path = INPUT_PATH_3_2p3 / "test4_out.zip"
        super().setup_method(method)


class TestCase5(TestInstanceConversionBasic):
    def setup_method(self, method):
        self.instance_path = INPUT_PATH_3_2p3 / "test5_in.xbrl"
        self.expected_output_path = INPUT_PATH_3_2p3 / "test5_out.zip"
        super().setup_method(method)


class TestCase6(TestInstanceConversionBasic):
    def setup_method(self, method):
        self.instance_path = INPUT_PATH_3_3 / "test1_in.xbrl"
        self.expected_output_path = INPUT_PATH_3_3 / "test1_out.zip"
        super().setup_method(method)


class TestCase7(TestInstanceConversionBasic):
    def setup_method(self, method):
        self.instance_path = INPUT_PATH_3_2p1 / "test1_in.xbrl"
        self.expected_output_path = INPUT_PATH_3_2p1 / "test1_out.zip"
        super().setup_method(method)
