# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.2.0] - 2026-09-03

### Added
- **Validation rule EBA-CUR-004** (ERROR, XML only): reports an instance whose facts point to more than one base currency, i.e. facts of datapoints declared in the taxonomy JSON with `"unit": "$baseCurrency"` reported in different currencies. The check is taxonomy-driven: each fact is matched against the datapoint signatures of the module (metric plus closed dimensions, with the table's open keys removed), so facts holding a currency breakdown (`"unit": "$unit"`) are not flagged and reports "in significant currencies" stay valid. It therefore fires *before* the conversion — `convert_instance(..., validate=True, eba=True)` stops with `ValidationError` and writes no output — complementing the `MultipleBaseCurrenciesError` raised by the converter itself. Facts whose signature matches datapoints of both kinds are ignored, and the rule is skipped when no taxonomy module can be resolved (#123).

### Fixed
- **Wrong `baseCurrency` in multi-currency reports**: the base currency was taken from the first `iso4217` unit declared in the XBRL-XML instance, so in a report with a currency breakdown (e.g. COREP LCR/ALM tables reported "in significant currencies") the parameter depended on the order of the `xbrli:unit` declarations and could end up holding a breakdown currency instead of the reporting currency. It is now determined from the facts themselves: the taxonomy JSON declares, per datapoint, whether its unit comes from the `baseCurrency` parameter (`"unit": "$baseCurrency"`) or is reported in the table's `unit` column (`"unit": "$unit"`), and only the facts of the former kind fix the parameter. When those facts are reported in more than one currency the instance is erroneous and the conversion now raises the new `MultipleBaseCurrenciesError` — naming the conflicting currencies, their fact counts and an example datapoint — instead of silently converting with an arbitrary currency. Reports where no such fact is present keep the previous behaviour (first declared currency) (#123).
- **`#none` accepted as a decimals parameter value (xBRL-CSV infinite precision)**: validation rejected `decimalsMonetary,#none` (and the other `decimals*` parameters) as invalid, even though `#none` is the *only* legal way to express infinite precision in xBRL-CSV. Per [xBRL-CSV 1.0 REC §3.1.9](https://www.xbrl.org/Specification/xbrl-csv/REC-2021-10-13/xbrl-csv-REC-2021-10-13.html) a decimals value must be an integer or the special value `#none`; `INF` is the xBRL-XML lexical form and a conformant processor rejects it with `xbrlce:invalidDecimalsValue`. CSV-026 had the two spellings inverted — it accepted `INF` and rejected `#none` — so `xbridge validate` reported a false-positive ERROR on spec-conformant packages. CSV-026 now accepts an integer or `#none` and flags `INF` with a message naming the encoding to use instead. The EBA decimals rules (EBA-DEC-001..004) previously recognised only `INF`, so a `#none` parameter bypassed them entirely; they now treat both spellings identically via the new `is_infinite_decimals()` helper.
- **Converter no longer emits `INF` into `parameters.csv`**: when a source XBRL-XML instance reported `@decimals="INF"` — legal in xBRL-XML and endorsed by the EBA Filing Rules (v5.9, §2.18) — the converter propagated the literal `INF` into the generated `parameters.csv`, producing output that conformant xBRL-CSV processors reject. `Converter._normalize_decimals_value()` now canonicalises both spellings of infinity to `#none`, so the xBRL-XML form never reaches the xBRL-CSV output. Both spellings are still accepted on input.

## [2.1.0] - 2026-07-29

### Added
- **EBA Taxonomy 4.4 support (phase 1, draft)**: Loaded the EBA 4.4 phase 1 draft taxonomy, adding ten modules: `ifrs18` (FINREP under IFRS 18), `codis`, `esgdis`, `findis`, `gsiidis` and `p3dh` (Pillar 3 disclosures), `resol1` and `resol2` (resolution planning), `mrel_decisions` (MREL) and `aml_eligibility` (AMLA). The corresponding `dim_dom_mapping_4.4.json` dimension-domain mapping was generated. All modules declare applicability dates starting between 2026-12-31 and 2027-12-31. Existing 4.2 / 4.2.1 / 4.3 modules are unchanged; the package now bundles taxonomy versions 4.2, 4.2.1, 4.3 and 4.4.
- **Module applicability dates**: each converted module JSON now records the reference-date range the module applies to as `from` (first applicable reference date) and `to` (last applicable reference date, or `null` for an open-ended range). These are read from the taxonomy module entry point (`documentInfo` → `eba:documentation`, `FromReferenceDate` / `To`|`toReferenceDate`) during conversion and exposed on `Module` as `from_date` / `to_date`. The `from`/`to` fields were backfilled into 374 bundled modules (every module for which the source declares reference dates).
- **Validation rule EBA-DATE-001** (ERROR, XML and CSV): reports an instance whose reference date falls outside the module's inclusive `[from, to]` applicability range. The check is skipped for modules without applicability dates and does not fire when the reference date is missing or malformed (those are covered by EBA-NAME-050 / CSV-024) (#121).
- **EBA Taxonomy 4.3 support**: Loaded the EBA 4.3 taxonomy release, adding the reporting frameworks introduced in that version. New modules: `aml_ra` (AMLA — Anti-Money Laundering Authority risk assessment) and the Third Country Branches (`tcb`) framework — `tcb_core`, `tcb_hu` and `tcb_liquidity`. The corresponding `dim_dom_mapping_4.3.json` dimension-domain mapping was generated. Existing 4.2 / 4.2.1 modules are unchanged; the package now bundles taxonomy versions 4.2, 4.2.1 and 4.3.
- **Fact reconciliation census**: after an XML → CSV conversion, `Converter.reconciliation` now holds a `FactReconciliation` accounting for every source fact, so incomplete conversions no longer pass unnoticed. Each detected fact is classified as `converted`, `excluded_non_reported` (orphaned to non-reported tables) or `unmatched` (matched no table definition), and top-level elements never recognised as facts are collected separately as `unrecognized_elements`. `unmatched` facts and `unrecognized_elements` are silent losses: they are reported through the new `FactReconciliationWarning` / `FactReconciliationError`, governed by the existing `strict_validation` flag (warn when `False`, raise when `True`). The census reuses the masks already computed for filing-indicator validation, so it adds negligible overhead. A new `Instance.unrecognized_fact_elements` property exposes the detection-stage findings (#120).
- **OneGate envelope support**: XBRL-XML instances delivered inside a OneGate `XbrlDeclarationReport` message envelope are now accepted. The nested `xbrli:xbrl` element is transparently extracted so conversion and validation proceed exactly as for a bare instance. Accepted input formats are defined by an explicit whitelist in the new `xbridge.envelope` module; an `.xml`/`.xbrl` file whose root is neither `xbrli:xbrl` nor a recognised envelope now raises `UnsupportedInstanceFormatError` instead of being parsed into a silently empty instance (#117).

### Fixed
- **Facts with per-element namespace declarations were silently dropped**: `Instance.get_facts` detected facts by matching each child's prefix against the metric/dimension prefixes found in the *root* `nsmap`. Instances that declare the metric namespace on each fact element (e.g. `<eba:qNJH xmlns:eba="…/dict/met" …>`) instead of on the root — valid XBRL, since a namespace declaration is in scope wherever it sits — left those prefixes absent from the root `nsmap`, so every such fact was skipped with no error. Detection now resolves each element's namespace from its expanded (Clark-notation) tag, which is independent of where the declaration appears (#118).
- **`schemaRef` detection relied on the literal `link` prefix**: `Converter.get_module_code` located the `schemaRef` element with `child.prefix == "link"`, which fails when the linkbase namespace is bound to a different prefix or declared per-element. It now matches by the element's expanded name (`{http://www.xbrl.org/2003/linkbase}schemaRef`), consistent with how contexts, units and filing indicators are already resolved (#119).

## [2.0.2] - 2026-05-14

### Fixed
- Fixed EBA-DEC-002 false positives on integer-typed metrics that use the `pure` unit. `Fact.metric` stores the metric QName in Clark notation (`{namespace}localname`), but `_build_metric_type_map()` was keyed on prefix notation (`eba_met:qXYZ`) taken from the module, so every lookup missed and the validator fell back to unit-based inference, flagging every `pure`-unit integer fact (e.g. `qAZH`, `qCCG`, `qDGB`) as a percentage. Added a `Fact.metric_qname` property that exposes the prefix-normalised QName and updated the decimals rules (EBA-DEC-001/002/003) to use it. Integer classification is now fully taxonomy-driven — the unit-based fallback in `check_integer_decimals_xml` has been removed. No backward-incompatible changes: `Fact.metric` is unchanged (#111).

### Security
- Updated `urllib3` and widened the `sphinx` constraint (`^7.4.7` → `>=7.4.7,<8.2`) to pull in patched releases addressing reported vulnerabilities (#112).

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

[Unreleased]: https://github.com/Meaningful-Data/xbridge/compare/v2.0.2...HEAD
[2.0.2]: https://github.com/Meaningful-Data/xbridge/compare/v2.0.1...v2.0.2
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
