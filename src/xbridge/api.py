"""API module."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from xbridge.converter import Converter
from xbridge.xml_instance import Instance


def convert_instance(
    instance_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    headers_as_datapoints: bool = False,
) -> Path:
    """
    Convert one single instance of XBRL-XML file to a CSV file

    :param instance_path: Path to the XBRL-XML instance

    :param output_path: Path to the output CSV file

    :param headers_as_datapoints: If True, the headers will be treated as datapoints.

    :return: Converted CSV file.

    """
    if output_path is None:
        output_path = Path(".")

    converter = Converter(instance_path)
    return converter.convert(output_path, headers_as_datapoints)


def load_instance(instance_path: Union[str, Path]) -> Instance:
    """
    Load an XBRL XML instance file

    :param instance_path: Path to the instance XBRL file

    :return: An instance object may be return
    """

    return Instance(str(instance_path))
