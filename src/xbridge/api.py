"""API module."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from xbridge.converter import Converter
from xbridge.instance import Instance


def convert_instance(
    instance_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    headers_as_datapoints: bool = False,
    validate_filing_indicators: bool = True,
    strict_validation: bool = True,
) -> Path:
    """
    Convert one single instance of XBRL-XML file to a CSV file

    :param instance_path: Path to the XBRL-XML instance

    :param output_path: Path to the output CSV file

    :param headers_as_datapoints: If True, the headers will be treated as datapoints.

    :param validate_filing_indicators: If True, validate that no facts are orphaned
        (belong only to non-reported tables). Default is True.

    :param strict_validation: If True (default), raise an error on orphaned facts. If False,
        emit a warning instead and continue.

    :return: Converted CSV file.

    """
    if output_path is None:
        output_path = Path(".")

    converter = Converter(instance_path)
    return converter.convert(
        output_path,
        headers_as_datapoints,
        validate_filing_indicators,
        strict_validation,
    )


def load_instance(instance_path: Union[str, Path]) -> Instance:
    """
    Load an XBRL XML instance file

    :param instance_path: Path to the instance XBRL file

    :return: An instance object may be return
    """

    return Instance.from_path(instance_path)
