"""Module with the taxonomy class, that serves to create the
JSON files with the conversion instructions.

Each time the EBA releases a new taxonomy, the taxonomy_loader.py
module must be run to reflect the changes in the taxonomy.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from time import time
from typing import Any, Dict, List, Union
from zipfile import ZipFile

from lxml import etree

from xbridge.modules import Module

MODULES_FOLDER = Path(__file__).parent / "modules"
INDEX_PATH = MODULES_FOLDER / "index.json"
DIM_DOM_MAPPING_PATH = MODULES_FOLDER / "dim_dom_mapping.json"


def _extract_specific_files_7z(file_path: Path, target_path: Path) -> None:
    cmd: Any = [
        shutil.which("7z"),
        "x",
        f"-o{target_path}",
        file_path,
        "*.json",
        "*dim-def.xml",
        "-r",
    ]
    if not cmd[0]:
        raise FileNotFoundError(
            "7z command not found, please install 7zip to be able to extract "
            "it and run the script again"
        )
    process = subprocess.run(cmd, capture_output=True)  # noqa: S603
    if process.returncode != 0:
        raise ValueError(f"Error extracting 7z file {file_path}")


class Taxonomy:
    """Class representing an XBRL taxonomy"""

    def __init__(self) -> None:
        self._modules: List[Module] = []

    @property
    def modules(self) -> List[Module]:
        """Returns the modules within the taxonomy"""
        return self._modules

    @staticmethod
    def __save_module(module: Module, file_path: Union[str, Path]) -> None:
        """Saves a module to a JSON file"""
        with open(file_path, "w", encoding="UTF-8") as fl:
            json.dump(module.to_dict(), fl)

    @staticmethod
    def _get_dim_dom_mapping(root: Any) -> Dict[str, Any]:
        ns = {
            "link": "http://www.xbrl.org/2003/linkbase",
            "xlink": "http://www.w3.org/1999/xlink",
        }
        arcroles = root.xpath(
            '//link:definitionArc[@xlink:arcrole="'
            'http://xbrl.org/int/dim/arcrole/dimension-domain"]',
            namespaces=ns,
        )
        map_dom_mapping = {}
        for element in arcroles:
            dim_locator = element.get("{http://www.w3.org/1999/xlink}from")
            dim = root.xpath(f'//link:loc[@xlink:label = "{dim_locator}"]', namespaces=ns)[0]
            dim = dim.get("{http://www.w3.org/1999/xlink}href").split("#")[1].split("_")[1]
            dom_locator = element.get("{http://www.w3.org/1999/xlink}to")
            dom = root.xpath(f'//link:loc[@xlink:label = "{dom_locator}"]', namespaces=ns)[0]
            dom = dom.get("{http://www.w3.org/1999/xlink}href").split("#")[1]
            map_dom_mapping[dim] = dom
        return map_dom_mapping

    def load_modules(self, input_path: Union[str, Path]) -> None:
        """Loads the modules in the taxonomy"""
        is_there_a_module = False
        index = {}

        dim_dom_mapping_loaded = False

        if not MODULES_FOLDER.exists():
            MODULES_FOLDER.mkdir()

        if isinstance(input_path, str):
            input_path = Path(input_path)

        if not input_path.exists():
            raise FileNotFoundError(f"File {input_path} not found")

        if input_path.suffix not in [".zip", ".7z"]:
            raise ValueError("Input file must be a zip or 7z file")

        if input_path.suffix == ".7z":
            print("Converting 7z to zip")
            start = time()
            self._convert_7z_to_zip(input_path)
            input_path = input_path.with_suffix(".zip")
            end = time()
            elapsed = round(end - start, 3)
            print(f"Conversion done in {elapsed} s")
        start = time()
        with ZipFile(input_path, mode="r") as zip_file:
            for file_path in zip_file.namelist():
                file_path_obj = Path(file_path)
                if (
                    str(file_path_obj)
                    == "www.eba.europa.eu\\eu\\fr\\xbrl\\crr\\dict\\dim\\dim-def.xml"
                ):
                    bin_read = zip_file.read(file_path)
                    root = etree.fromstring(bin_read.decode("utf-8"))
                    dim_dom_mapping = self._get_dim_dom_mapping(root)
                    with open(DIM_DOM_MAPPING_PATH, "w", encoding="UTF-8") as fl:
                        json.dump(dim_dom_mapping, fl, indent=4)
                    dim_dom_mapping_loaded = True

                if file_path_obj.suffix == ".json" and file_path_obj.parent.name == "mod":
                    is_there_a_module = True
                    print(f"Loading module {file_path_obj.stem.upper()}")
                    start = time()
                    module = Module.from_taxonomy(zip_file, file_path)
                    module_file_name = f"{module.code}_{module.framework_version}.json"
                    module_path = str(MODULES_FOLDER / module_file_name)
                    self.__save_module(module, module_path)
                    if module.url is None:
                        continue
                    index_key = f"{module.url[:-4]}xsd"
                    index[index_key] = module_file_name
                    # modules.append(module)
                    end = time()
                    elapsed = round(end - start, 3)
                    if module.code:
                        print(f"Module {module.code.upper()} loaded in {elapsed} s")
        if not is_there_a_module:
            raise TypeError(
                (
                    "No modules found in the taxonomy. "
                    "Please check that the zip file does not contain "
                    "zip files within it"
                )
            )

        if not dim_dom_mapping_loaded:
            raise ImportError("dim_dom_mapping file was not loaded")

        with open(INDEX_PATH, "w", encoding="UTF-8") as fl:
            json.dump(index, fl, indent=4)
        # self._modules = modules
        end = time()
        print(f"Time to extract modules: {end - start}")

    def get_module(self, code: str) -> Module:
        """Returns the module with the given code"""
        for module in self.modules:
            if module.code == code:
                return module
        raise ValueError(f"Module with code {code} not found in the taxonomy")

    @classmethod
    def from_taxonomy(cls, input_path: Union[str, Path]) -> None:
        """Returns a Taxonomy object from a JSON taxonomy file"""
        input_path = input_path if isinstance(input_path, Path) else Path(input_path)
        obj = cls()
        obj.load_modules(input_path)

        ##TODO:
        # Validate that the assumptions for the EBA architecture of the taxonomies is correct:
        # - Currency reported is not an attribute in the CSV
        # - The parameters expect the values we have
        # - There are no potential conflicts if we drop the previxes for
        #       the key values in the scenarios

    @staticmethod
    def _convert_7z_to_zip(input_path: Path) -> None:
        """Converts a 7z file to a zip file"""
        start = time()
        with TemporaryDirectory() as temp_folder:
            _extract_specific_files_7z(input_path, Path(temp_folder))
            extracted = time()
            print(f"7z file extracted in {extracted - start} s")
            with ZipFile(input_path.with_suffix(".zip"), mode="w") as zip_file:
                for root, _, files in os.walk(temp_folder):
                    for file in files:
                        # Compute the relative file path to the root of the temporary directory
                        relative_path = os.path.relpath(os.path.join(root, file), temp_folder)
                        # Add the file to the zip file with its relative path
                        zip_file.write(os.path.join(root, file), arcname=relative_path)
        end = time()
        elapsed = round(end - extracted, 3)
        print(f"Zip file created in {elapsed} s")
        elapsed = round(end - start, 3)
        print(f"7z to zip conversion done in {elapsed} s")


def main() -> None:
    """Main function to generate the json files from the taxonomy"""
    parser = argparse.ArgumentParser(description="Xbridge taxonomy loader")

    parser.add_argument(
        "input_path",
        type=str,
        help="Please provide the input 7z or zip file with the taxonomy.",
    )

    args = parser.parse_args()
    Taxonomy.from_taxonomy(args.input_path)


if __name__ == "__main__":
    main()
