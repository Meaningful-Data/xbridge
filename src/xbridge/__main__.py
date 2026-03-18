"""Command-line interface for xbridge."""

import argparse
import json
import sys
from pathlib import Path

from xbridge.api import convert_instance
from xbridge.exceptions import ValidationError


def _convert_main() -> None:
    """CLI entry point for the convert command (default behaviour)."""
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

    parser.add_argument(
        "--validate",
        action="store_true",
        default=False,
        help="Run validation before and after conversion (default: False)",
    )

    parser.add_argument(
        "--eba",
        action="store_true",
        default=False,
        help="Enable EBA-specific validation rules (only applies with --validate)",
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
            print(
                f"Error: Output path does not exist: {args.output_path}",
                file=sys.stderr,
            )
            sys.exit(1)

    try:
        if args.validate:
            print("Running pre-conversion validation...")
        result_path = convert_instance(
            instance_path=input_path,
            output_path=output_path,
            headers_as_datapoints=args.headers_as_datapoints,
            validate_filing_indicators=True,
            strict_validation=args.strict_validation,
            validate=args.validate,
            eba=args.eba,
        )
        if args.validate:
            print("Pre-conversion validation passed.")
            print(f"Conversion successful: {result_path}")
            print("Post-conversion validation passed.")
        else:
            print(f"Conversion successful: {result_path}")
    except ValidationError as ve:
        results = ve.results
        error_count = 0
        warning_count = 0
        for section in results.values():
            error_count += sum(len(v) for v in section["errors"].values())
            warning_count += sum(len(v) for v in section["warnings"].values())

        for section in results.values():
            for findings_by_code in (section["errors"], section["warnings"]):
                for _code, occurrences in findings_by_code.items():
                    for finding in occurrences:
                        print(
                            f"[{finding['severity']}] {finding['rule_id']}: {finding['message']}",
                            file=sys.stderr,
                        )
                        print(f"  Location: {finding['location']}", file=sys.stderr)

        total = error_count + warning_count
        print(
            f"\nFound {total} issue(s): {error_count} error(s), {warning_count} warning(s)",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(f"Conversion failed: {e}", file=sys.stderr)
        sys.exit(1)


def _validate_main() -> None:
    """CLI entry point for the validate subcommand."""
    parser = argparse.ArgumentParser(
        description="Validate an XBRL instance file",
        prog="xbridge validate",
    )

    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the XBRL file (.xbrl, .xml, or .zip)",
    )

    parser.add_argument(
        "--eba",
        action="store_true",
        default=False,
        help="Enable EBA-specific validation rules (default: False)",
    )

    parser.add_argument(
        "--post-conversion",
        action="store_true",
        default=False,
        help=(
            "Skip structural checks guaranteed by xbridge's converter. "
            "Only meaningful for .zip (CSV) files (default: False)"
        ),
    )

    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        dest="json_output",
        help="Output findings as JSON instead of human-readable text",
    )

    # Strip the leading "validate" from sys.argv so argparse sees only the
    # arguments that belong to this subcommand.
    args = parser.parse_args(sys.argv[2:])

    from xbridge.validation import validate

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    try:
        results = validate(
            file=input_path,
            eba=args.eba,
            post_conversion=args.post_conversion,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json_output:
        print(json.dumps(results, indent=2))
    else:
        error_count = 0
        warning_count = 0
        for section in results.values():
            error_count += sum(len(v) for v in section["errors"].values())
            warning_count += sum(len(v) for v in section["warnings"].values())
        total = error_count + warning_count

        if not total:
            print("No issues found.")
        else:
            for section in results.values():
                for findings_by_code in (section["errors"], section["warnings"]):
                    for _code, occurrences in findings_by_code.items():
                        for finding in occurrences:
                            print(
                                f"[{finding['severity']}] {finding['rule_id']}: "
                                f"{finding['message']}"
                            )
                            print(f"  Location: {finding['location']}")

            print()
            print(f"Found {total} issue(s): {error_count} error(s), {warning_count} warning(s)")

    if any(section["errors"] for section in results.values()):
        sys.exit(1)


def main() -> None:
    """Main CLI entry point for xbridge.

    Routes to the appropriate subcommand:
      - ``xbridge validate <file> [options]`` — validate an XBRL instance
      - ``xbridge <file> [options]``          — convert XBRL-XML to XBRL-CSV
    """
    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        _validate_main()
    else:
        _convert_main()


if __name__ == "__main__":
    main()
