# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.5.1rc1] - 2026-01-XX

### Fixed
- Fixed handling of filing indicators codes by getting them from JSON files in the taxonomy instead of deriving them.
## [1.5.1rc2] - 2026-02-02

### Fixed
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

[Unreleased]: https://github.com/Meaningful-Data/xbridge/compare/v1.5.1rc2...HEAD
[1.5.1rc2]: https://github.com/Meaningful-Data/xbridge/compare/v1.5.1rc1...v1.5.1rc2
[1.5.1rc1]: https://github.com/Meaningful-Data/xbridge/compare/v1.5.0...v1.5.1rc1
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
