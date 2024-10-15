"""
Test that EBA samples are transformed correctly
"""

import json
import unittest
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from xbridge.api import convert_instance, load_instance

OUTPUT_PATH = Path(__file__).parent / "conversions"


class TestInstanceConversionBasic(unittest.TestCase):
    """
    Tests for the cases where only input xml is provided
    """

    def setUp(self, instance_path=None, expected_output_path=None):
        """
        Sets up the test case
        """
        if instance_path is None:
            self.skipTest("Abstract test class")

        self.instance = load_instance(instance_path)

        generated_output_path = convert_instance(
            instance_path=instance_path, output_path=OUTPUT_PATH
        )
        self.generated_output_path = Path(generated_output_path)
        self.input_path = Path(instance_path)
        self.generated_output_zip = ZipFile(generated_output_path, mode="r")
        self.generated_csv_files = [
            file
            for file in self.generated_output_zip.namelist()
            if file.startswith("reports") and file.endswith(".csv")
        ]

        self.no_xml_facts = len(self.instance.facts)
        self.no_filing_indicators = len(self.instance.filing_indicators)

        self.expected_output_zip = ZipFile(expected_output_path, mode="r")
        self.expected_root_folder_name = self.expected_output_zip.namelist()[0]
        self.expected_csv_files = [
            file
            for file in self.expected_output_zip.namelist()
            if file.startswith(f"{self.expected_root_folder_name}reports")
            and file.endswith(".csv")
        ]

    def tearDown(self) -> None:
        """
        Removes the generated zip file
        """
        self.generated_output_zip.close()
        self.generated_output_path.unlink()
        self.expected_output_zip.close()

    def test_file_created(self):
        """Asserts that the file is created"""
        self.assertTrue(self.generated_output_path.exists())

    def test_file_structure(self):
        """
        Asserts that the file has the structure of an XBRL-CSV file
        Concretely, it contains the standard folders and json files
        """
        self.assertTrue("reports/report.json" in self.generated_output_zip.namelist())
        self.assertTrue("META-INF/reports.json" in self.generated_output_zip.namelist())

    def test_number_facts(self):
        """
        Tests that the number of facts is correct
        """
        no_generated_facts = 0

        for generated_file in self.generated_csv_files:
            file_name = Path(generated_file).name
            if file_name not in ["FilingIndicators.csv", "parameters.csv"]:
                try:
                    with self.generated_output_zip.open(f"reports/{file_name}") as fl:
                        generated_df = pd.read_csv(fl)
                        no_generated_facts += len(generated_df)
                except pd.errors.EmptyDataError:
                    pass
        print(f"Generated: {no_generated_facts}; xml_facts: {self.no_xml_facts}")
        self.assertGreaterEqual(
            no_generated_facts,
            self.no_xml_facts,
            msg=(
                f"Number of facts inconsistent for {self.input_path}: Expected: "
                f"{self.no_xml_facts} Generated: {no_generated_facts} "
            ),
        )

    def test_files_same_structure(self):
        """
        Tests that all generated files have the expected structure
        """
        for expected_file in self.expected_csv_files:
            file_name = Path(expected_file).name

            with self.expected_output_zip.open(expected_file) as fl:
                expected_df = pd.read_csv(fl)
            with self.generated_output_zip.open(f"reports/{file_name}") as fl:
                generated_df = pd.read_csv(fl)

            self.assertTrue(
                set(list(expected_df.columns)) == set(list(generated_df.columns)),
                msg=(
                    f"Expected: {set(list(expected_df.columns))} "
                    f"Generated: {set(list(generated_df.columns))}"
                ),
            )


class TestInstanceConversionFull(TestInstanceConversionBasic):
    """
    Tests for the cases where input xml and expected output
    csv files are provided
    """

    def setUp(self, instance_path=None, expected_output_path=None):
        """
        Sets up the test case
        :param instance_path: Path to the input xml file
        :param expected_output_path: Path to the expected output zip file
        """
        super().setUp(instance_path, expected_output_path)

    def tearDown(self) -> None:
        super().tearDown()

    def test_reports_file(self):
        """
        Tests that the META-INFO/reports.json file is equal in
        the input and output files
        """
        with self.generated_output_zip.open("META-INF/reports.json") as fl:
            reports_generated = json.load(fl)
        with self.expected_output_zip.open(
            f"{self.expected_root_folder_name}META-INF/reports.json"
        ) as fl:
            reports_expected = json.load(fl)
        self.assertEqual(reports_generated, reports_expected)

    def test_same_report_files(self):
        """
        Tests that the number and name of csv files contained
        in both the input and output files are the same
        """
        self.assertEqual(
            {Path(file).name for file in self.expected_csv_files},
            {Path(file).name for file in self.generated_csv_files},
        )

    def test_files_same_size(self):
        """
        Tests that all generated files are exactly the same
        """
        for expected_file in self.expected_csv_files:
            file_name = Path(expected_file).name

            with self.expected_output_zip.open(expected_file) as fl:
                expected_df = pd.read_csv(fl)
            with self.generated_output_zip.open(f"reports/{file_name}") as fl:
                generated_df = pd.read_csv(fl)

            if file_name != "parameters.csv":
                self.assertTrue(
                    len(expected_df) == len(generated_df),
                    msg=(
                        f"Length of {file_name} inconsistent: Expected: "
                        f"{len(expected_df)} Generated: {len(generated_df)}"
                    ),
                )

    def test_number_filing_indicators(self):
        """
        Tests that the number of filing indicators is correct
        """

        with self.generated_output_zip.open("reports/FilingIndicators.csv") as fl:
            generated_df = pd.read_csv(fl)

            self.assertEqual(self.no_filing_indicators, len(generated_df))
