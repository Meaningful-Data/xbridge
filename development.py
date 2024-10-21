"""
    File for development testing
"""
import os
from glob import glob
from pathlib import Path
from time import time

import pandas as pd

from xbridge.converter import Converter


def compare_with_baseline():
    """
    Compares the output files with the baseline files
    """
    EXT = "*.csv"
    PATH = str(Path.cwd() / "output")
    all_csv_files = [file
                     for path, subdir, files in os.walk(PATH)
                     for file in glob(os.path.join(path, EXT))]
    baseline_dfs = {}
    new_dfs = {}
    for file in all_csv_files:
        df = pd.read_csv(file, sep=",")
        if "baseline" in file:
            # Get only the file name
            file = Path(file).name
            baseline_dfs[file] = df
        else:
            file = Path(file).name
            new_dfs[file] = df
    not_equal = []
    equal = []
    not_in_new = []
    not_in_baseline = []
    different_length = {}
    for key, value in baseline_dfs.items():
        if key in new_dfs:
            if "datapoint" in value.columns:
                value = value.dropna(axis=0, how='all')
                new_dfs[key] = new_dfs[key].dropna(axis=0, how='all')
                value = value.reindex(sorted(value.columns), axis=1)
                new_dfs[key] = new_dfs[key].reindex(sorted(new_dfs[key].columns), axis=1)
                value = value.reset_index(drop=True)
                new_dfs[key] = new_dfs[key].reset_index(drop=True)
                open_keys = [col for col in value.columns if col not in ["datapoint", "factValue"]]
                sorting_keys = ['datapoint']
                if len(open_keys) > 0:
                    sorting_keys.extend(open_keys)
                value = value.sort_values(by=sorting_keys, ascending=True)
                new_dfs[key] = new_dfs[key].sort_values(by=sorting_keys, ascending=True)
                value = value.reset_index(drop=True)
                new_dfs[key] = new_dfs[key].reset_index(drop=True)
            if len(value) != len(new_dfs[key]):
                different_length[key] = {"baseline": len(value), "new": len(new_dfs[key])}
                continue
            if not value.equals(new_dfs[key]):
                not_equal.append(key)
            else:
                equal.append(key)
        else:
            not_in_new.append(key)
    for key, value in new_dfs.items():
        if key not in baseline_dfs:
            not_in_baseline.append(key)

    print(f"Files not equal: {not_equal}")
    print(f"Files equal: {equal}")
    print(f"Files with different length: {different_length}")
    print(f"Files not in new but present in baseline: {not_in_new}")
    print(f"Files not in baseline but present in new: {not_in_baseline}")


TAXONOMY_PATH = Path(__file__).parent / "input" / "taxonomy" / "FullTaxonomy.7z"

if __name__ == "__main__":
    INPUT_PATH_3_3 = Path(__file__).parent / "tests" / "test_files" / "sample_3_3"
    # INSTANCE_PATH = Path.cwd()  / "input" / "instances" / "corep_of1.xbrl"
    INSTANCE_PATH = INPUT_PATH_3_3 / "test1_in.xbrl"

    start = time()
    converter = Converter(INSTANCE_PATH)
    initial = time()
    print(converter.convert(output_path="output/"))
    end = time()
    print(f"Time to initialize: {initial - start}")
    print(f"Time to convert: {end - initial}")
    print(f"Total time: {end - start}")
    compare_with_baseline()
