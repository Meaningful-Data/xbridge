"""
    File for development testing
"""
import os
from glob import glob
from pathlib import Path
from time import time

import pandas as pd

from xbridge.converter import Converter


if __name__ == "__main__":
    INPUT_PATH_3_3 = Path(__file__).parent / "xbridge"/ "Testing" / "test_files" / "sample_3_3"
    INSTANCE_PATH = Path.cwd()  / "input" / "instances" / "no_data.xbrl"
    # INSTANCE_PATH = INPUT_PATH_3_3 / "test1_in.xbrl"

    start = time()
    converter = Converter(INSTANCE_PATH)
    initial = time()
    print(converter.convert(output_path="output/"))
    end = time()
    print(f"Time to initialize: {initial - start}")
    print(f"Time to convert: {end - initial}")
    print(f"Total time: {end - start}")
