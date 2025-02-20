"""
File for development testing
"""

from pathlib import Path
from time import time

from xbridge.converter import Converter


def main():
    INSTANCE_PATH = Path.cwd() / "input" / "dora_sample.xbrl"

    start = time()
    converter = Converter(INSTANCE_PATH)
    initial = time()
    print(converter.convert(output_path="output/", headers_as_datapoints=True))
    end = time()
    print(f"Time to initialize: {initial - start}")
    print(f"Time to convert: {end - initial}")
    print(f"Total time: {end - start}")

if __name__ == "__main__":
    main()
