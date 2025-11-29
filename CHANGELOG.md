# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Fixed decimals issues
- Fixed issue with stripping

## [1.5.0rc2] - 2024-11-28

### Added
- Configurable filing indicator strictness and warnings
- New `strict_validation` parameter for handling orphaned facts

### Changed
- Updated version to 1.5.0rc2

### Fixed
- Fixed issue with new architecture
- Fixed decimals issues

## [1.5.0rc1] - 2024-08-11

### Added
- Implemented DORA CSV conversion (#42)
- Schema references validation (#44)
- Allowed values to JSON mappings
- Decimal conversion improvements (#45)

### Fixed
- Filing indicators error handling (#43)
- Version consistency check (#46)

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

[Unreleased]: https://github.com/Meaningful-Data/xbridge/compare/v1.5.0rc2...HEAD
[1.5.0rc2]: https://github.com/Meaningful-Data/xbridge/compare/v1.5.0rc1...v1.5.0rc2
[1.5.0rc1]: https://github.com/Meaningful-Data/xbridge/compare/v1.4.0...v1.5.0rc1
[1.4.0]: https://github.com/Meaningful-Data/xbridge/compare/v1.3.1rc1...v1.4.0
[1.3.1rc1]: https://github.com/Meaningful-Data/xbridge/compare/v1.3.0...v1.3.1rc1
[1.3.0]: https://github.com/Meaningful-Data/xbridge/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/Meaningful-Data/xbridge/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/Meaningful-Data/xbridge/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/Meaningful-Data/xbridge/compare/v1.0.4...v1.1.0
[1.0.4]: https://github.com/Meaningful-Data/xbridge/compare/v1.0.3...v1.0.4
[1.0.3]: https://github.com/Meaningful-Data/xbridge/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/Meaningful-Data/xbridge/releases/tag/v1.0.2
