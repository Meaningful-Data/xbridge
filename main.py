"""
File for development testing
"""

from pathlib import Path
from time import time

from xbridge.converter import Converter


def main():
    INSTANCE_PATH = Path(__file__).parent / "input" / "sample.xbrl"

    start = time()
    converter = Converter(INSTANCE_PATH)
    initial = time()
    print(converter.convert(output_path="output/", headers_as_datapoints=True))
    end = time()
    print(f"Time to initialize: {initial - start}")
    print(f"Time to convert: {end - initial}")
    print(f"Total time: {end - start}")

    # TAXONOMY_PATH = Path(__file__).parent / "input" / "Full_Taxonomy.7z"
    # Taxonomy.from_taxonomy(TAXONOMY_PATH)


if __name__ == "__main__":
    main()
