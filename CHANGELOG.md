# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.1] - 2026-03-25

### Fixed
- Fixed case-insensitive file extension handling in `Instance.from_path()`: files with uppercase extensions (`.XBRL`, `.XML`, `.ZIP`) are now processed correctly (#109).

## [2.0.0] - 2026-03-17

### Added
- **Standalone Validation API**: New `xbridge.validation` module with `validate()` function for checking XBRL instance files against structural and regulatory rules — both XBRL-XML and XBRL-CSV formats.
- **Validation CLI Command**: New `validate` subcommand with `--eba`, `--post-conversion`, and `--json` flags for running validation checks from the command line.
- **Validate-Convert-Validate Pipeline**: New `--validate` and `--eba` CLI flags for the `convert` command run validation before and after conversion. Equivalent `validate=` and `eba=` parameters added to `convert_instance()`. Raises `ValidationError` on failure.
- **XML Validation Rules**: 30+ rules covering well-formedness (XML-001..XML-003), schemaRef checks (XML-010/012), filing indicators (XML-020..XML-026), context structure (XML-030..XML-035), fact structure (XML-040..XML-043), unit UTR reference (XML-050), document-level checks (XML-060..XML-069), and taxonomy conformance (XML-070..XML-072).
- **CSV Validation Rules**: 30+ rules covering report package structure (CSV-001..CSV-006), report.json metadata (CSV-010..CSV-016), parameters.csv (CSV-020..CSV-026), FilingIndicators.csv (CSV-030..CSV-035), data table checks (CSV-040..CSV-049), fact-level checks (CSV-050..CSV-052), and taxonomy conformance (CSV-060..CSV-062).
- **EBA-specific Validation Rules**: Entity identifier checks (EBA-ENTITY-001/002), currency validation (EBA-CUR-001..003), non-monetary unit checks (EBA-UNIT-001/002), decimals accuracy (EBA-DEC-001..004), guidance compliance (EBA-GUIDE-001..007), file naming conventions (EBA-NAME-001..071), and supplementary regulatory checks (EBA-2.5, EBA-2.16.1, EBA-2.24, EBA-2.25).
- **EBA Taxonomy 4.2.1**: Added support for FINREP 4.2.1 (`finrep9dp` module).
- **Validation Documentation**: New `docs/validation.rst` with full API reference, usage examples, and integration guide.

### Changed
- **Scoped Validation Results**: `validate()` returns a dictionary keyed by validation scope (`"XBRL"` always present, `"EBA"` when `eba=True`). Each scope contains `"errors"` and `"warnings"` sub-dicts keyed by rule code. Code previously reading `results["errors"]` must access `results["XBRL"]["errors"]` or iterate `results.values()`.
- **Validation Performance**: Single-pass XML scanning and shared cache across rules eliminate redundant I/O (~60-65% faster for CSV validation).
- **Simplified Module Interface**: Removed external `dim_dom_mapping*.json` dependency; dimension-domain variable mapping is now computed inline from table column metadata.
- **Converter Output**: Updated `reportPackage.json` and `report.json` to use final XBRL specification URLs (`https://xbrl.org/report-package/2023` and `https://xbrl.org/2021/xbrl-csv`).

### Fixed
- Fixed `Scenario.parse()` crash on dimension attributes without a namespace prefix.
- Fixed EBA-CUR-002 incorrectly flagging non-monetary facts in a denomination context.
- Fixed `iso4217:`-prefixed `baseCurrency` parameter handling in CSV validation rules.
- Fixed ZIP root folder prefix detection affecting CSV-003 and CSV-005.
- Fixed CSV-033 to accept boolean values `'1'` and `'0'` for filing indicator `reported` column.
- Fixed CSV-025 `baseCurrency` check to only consider actually reported datapoints.
- Fixed incorrect `R_02.00.a` filing indicator in the `rem_bm` module — corrected to `R_02.00`.

## [1.5.2] - 2026-02-13

### Fixed
- Fixed `baseCurrency` parameter handling: now only included in XBRL-CSV output when present in the source instance, preventing null values in parameters.csv.
- Fixed filing indicators parsing to handle multiple `find:fIndicators` blocks in a single XBRL instance. Previously only the first block was processed, silently dropping indicators from subsequent blocks (#60).

## [1.5.1] - 2026-02-04

### Fixed
- Fixed handling of filing indicators codes by getting them from JSON files in the taxonomy instead of deriving them.
- Fixed unit attribute handling for variables without unit in dimensions. Unit values are now correctly cleared for datapoints that don't have `"unit": "$unit"` or `"unit": "$baseCurrency"` in their dimensions, preventing incorrect unit assignment in XBRL-CSV output.

## [1.5.0] - 2026-01-15

### Added
- **EBA Taxonomy 4.2 Support**: Updated to latest EBA taxonomy version published on 2026-01-14.
- **DORA CSV Conversion**: Full support for Digital Operational Resilience Act reporting (#42).
- **Schema References Validation**: Validate schema references in XBRL instances (#44).
- **Configurable Filing Indicator Validation**: New `strict_validation` parameter for handling orphaned facts with configurable strictness.
- **Custom Exception Types**: `SchemaRefValueError` and `DecimalValueError` exceptions that include offending values for better debugging.
- **Structured Warning Types**: `XbridgeWarning`, `IdentifierPrefixWarning`, and `FilingIndicatorWarning` for easier integration with external tooling.
- **Flexible Filing Indicator Parsing**: Support for "0" and "1" values in filing indicator `filed` attribute (in addition to "true" and "false").
- **Documentation**: Examples for capturing or promoting XBridge warnings when using `convert_instance`.

### Changed
- **New Namespaces Architecture**: Refactored internal namespace handling for improved maintainability (#50).
- **Centralized Decimals Validation**: Unified decimals validation logic to normalize and validate decimal values.
- **Improved Decimal Conversion**: Enhanced decimal handling with better precision management (#45).
- Updated dependency urllib3 from 2.3.0 to 2.6.0.

### Fixed
- Fixed filing indicators error handling (#43).
- Fixed version consistency check (#46).
- Fixed decimals handling edge cases.
- Fixed various issues with the new architecture.

## [1.4.0] - 2024-07-18

### Added
- Handling of special values in parameters
- Adaptation to latest DORA specification (#36)
- Configurable decimals handling from data types

### Changed
- Updated version to 1.4.0

### Fixed
- Fixed potential error when mixing INF and integers
- Fixed decimals handling
- Fixed Linux compatibility issue for loading taxonomies

## [1.3.1rc1] - 2024-06-15

### Added
- Check for filing indicator codes
- Integer decimals and INF handling

### Fixed
- Fixed decimals parameters issue (#32)
- Handling @none for decimals

## [1.3.0] - 2024-05-20

### Added
- Updated taxonomy to EBA 4.1 version
- Python 3.13 compatibility (#25)
- Default entity prefix (#24)
- Version workflow
- Root folder support (#22)

### Changed
- Updated taxonomy files to 4.1 version
- Updated numpy dependencies for Python 3.13
- Updated project description
- Dimension-domain mapping fix (#29)

### Removed
- Removed conversion files

## [1.2.0] - 2024-03-15

### Added
- DORA datapoints support (#15)
- New taxonomy architecture (#11)

### Changed
- Reorganized instance class
- Converter code improved for readability and performance
- Flat to datapoints implementation

### Fixed
- Fixed issues #13 and #14
- Fixed module reference (#18)
- Fixed code on taxonomy loader to prevent storing modules in memory

## [1.1.1] - 2024-02-10

### Fixed
- Various bug fixes and stability improvements

## [1.1.0] - 2024-01-20

### Added
- Initial stable release with core functionality
- XBRL-XML to XBRL-CSV conversion for EBA Taxonomy
- Support for filing indicators
- Parameters handling (entity, period, baseCurrency, decimals)

### Changed
- Adapted CI pipelines to Open Source Standards
- Adapted file structure to regular open source
- Updated pyproject to Poetry 2.0
- Added ruff and mypy as dependencies

### Security
- Added SECURITY.md file

## [1.0.4] - 2023-12-15

### Changed
- Pre-release improvements and bug fixes

## [1.0.3] - 2023-12-01

### Changed
- Pre-release improvements

## [1.0.2] - 2023-11-15

### Added
- Initial pre-release version

[Unreleased]: https://github.com/Meaningful-Data/xbridge/compare/v2.0.1...HEAD
[2.0.1]: https://github.com/Meaningful-Data/xbridge/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/Meaningful-Data/xbridge/compare/v1.5.2...v2.0.0
[1.5.2]: https://github.com/Meaningful-Data/xbridge/compare/v1.5.1...v1.5.2
[1.5.1]: https://github.com/Meaningful-Data/xbridge/compare/v1.5.0...v1.5.1
[1.5.0]: https://github.com/Meaningful-Data/xbridge/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/Meaningful-Data/xbridge/compare/v1.3.1rc1...v1.4.0
[1.3.1rc1]: https://github.com/Meaningful-Data/xbridge/compare/v1.3.0...v1.3.1rc1
[1.3.0]: https://github.com/Meaningful-Data/xbridge/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/Meaningful-Data/xbridge/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/Meaningful-Data/xbridge/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/Meaningful-Data/xbridge/compare/v1.0.4...v1.1.0
[1.0.4]: https://github.com/Meaningful-Data/xbridge/compare/v1.0.3...v1.0.4
[1.0.3]: https://github.com/Meaningful-Data/xbridge/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/Meaningful-Data/xbridge/releases/tag/v1.0.2
