"""Command-line interface for xbridge."""

import argparse
import sys
from pathlib import Path

from xbridge.api import convert_instance


def main() -> None:
    """Main CLI entry point for xbridge converter."""
    parser = argparse.ArgumentParser(
        description="Convert XBRL-XML instances to XBRL-CSV format",
        prog="xbridge",
    )

    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the input XBRL-XML file",
    )

    parser.add_argument(
        "--output-path",
        type=str,
        default=None,
        help="Output directory path (default: same folder as input file)",
    )

    parser.add_argument(
        "--headers-as-datapoints",
        action="store_true",
        default=False,
        help="Treat headers as datapoints (default: False)",
    )

    parser.add_argument(
        "--strict-validation",
        action="store_true",
        default=True,
        help="Raise errors on validation failures (default: True)",
    )

    parser.add_argument(
        "--no-strict-validation",
        action="store_false",
        dest="strict_validation",
        help="Emit warnings instead of errors for validation failures",
    )

    args = parser.parse_args()

    # Determine output path
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    if args.output_path is None:
        output_path = input_path.parent
    else:
        output_path = Path(args.output_path)
        if not output_path.exists():
            print(f"Error: Output path does not exist: {args.output_path}", file=sys.stderr)
            sys.exit(1)

    try:
        result_path = convert_instance(
            instance_path=input_path,
            output_path=output_path,
            headers_as_datapoints=args.headers_as_datapoints,
            validate_filing_indicators=True,
            strict_validation=args.strict_validation,
        )
        print(f"Conversion successful: {result_path}")
    except Exception as e:
        print(f"Conversion failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
