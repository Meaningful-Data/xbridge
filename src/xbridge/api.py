"""API module."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from xbridge.converter import Converter
from xbridge.exceptions import ValidationError
from xbridge.instance import Instance


def convert_instance(
    instance_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    headers_as_datapoints: bool = False,
    validate_filing_indicators: bool = True,
    strict_validation: bool = True,
    validate: bool = False,
    eba: bool = False,
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

    :param validate: If True, run validation before and after conversion.  Pre-conversion
        errors stop the pipeline; post-conversion errors are reported after the output
        file has been written.  Default is False.

    :param eba: If True, enable EBA-specific validation rules.  Only used when
        *validate* is True.  Default is False.

    :return: Converted CSV file.

    :raises ValidationError: When *validate* is True and validation finds errors.

    """
    if validate:
        from xbridge.validation import validate as _validate

        pre_results = _validate(instance_path, eba=eba)
        if any(section["errors"] for section in pre_results.values()):
            raise ValidationError(pre_results)

    if output_path is None:
        output_path = Path(".")

    converter = Converter(instance_path)
    result = converter.convert(
        output_path,
        headers_as_datapoints,
        validate_filing_indicators,
        strict_validation,
    )

    if validate:
        from xbridge.validation import validate as _validate

        post_results = _validate(result, eba=eba, post_conversion=True)
        if any(section["errors"] for section in post_results.values()):
            raise ValidationError(post_results, path=result)

    return result


def load_instance(instance_path: Union[str, Path]) -> Instance:
    """
    Load an XBRL XML instance file

    :param instance_path: Path to the instance XBRL file

    :return: An instance object may be return
    """

    return Instance.from_path(instance_path)
