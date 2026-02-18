# xbridge Validation Rules -- Enumeration

**Version:** 0.2 (Draft)
**Date:** 2026-02-16
**Parent document:** [validation_specification.md](validation_specification.md)

This document enumerates all individual validation rules. Each rule has a unique
identifier, a severity, a human-readable description, and attributes controlling
when the rule is executed.

Rules are organized into two categories based on the input format:

- **XML Instance Rules** -- apply when validating `.xbrl` files.
- **CSV Report Package Rules** -- apply when validating `.zip` files.

### Rule Attributes

| Attribute      | Values   | Meaning                                                                 |
|----------------|----------|-------------------------------------------------------------------------|
| **EBA**        | Yes / No | When Yes, the rule only runs if the `eba` parameter is `True`.          |
| **EBA ref**    | Section  | Cross-reference to the EBA Filing Rules v5.7 section that this rule implements or satisfies. |
| **Post-conv.** | Yes / No | *(CSV only)* When No, the rule is skipped if `post_conversion` is `True`. |

Rules with **EBA = No** are standard XBRL 2.1 or xBRL-CSV 1.0 structural
checks. Rules with **EBA = Yes** are requirements imposed by the EBA Filing
Rules (v5.7) that go beyond the base XBRL/xBRL-CSV specifications.

---

## 1. XML Instance Rules

**Scope:** Structural and compliance checks on xBRL-XML instances.

### 1.1 XML Well-formedness and Encoding

| Rule ID  | Severity | EBA | EBA ref | Description                                                              |
|----------|----------|-----|---------|--------------------------------------------------------------------------|
| XML-001  | ERROR    | No  | --      | The file MUST be well-formed XML.                                        |
| XML-002  | ERROR    | Yes | 1.4     | The file MUST use UTF-8 encoding. (encodingNotUtf8)                      |

### 1.2 Root Element

| Rule ID  | Severity | EBA | EBA ref | Description                                                              |
|----------|----------|-----|---------|--------------------------------------------------------------------------|
| XML-003  | ERROR    | No  | --      | The root element MUST be `xbrli:xbrl`.                                   |

### 1.3 Schema Reference (schemaRef)

| Rule ID  | Severity | EBA | EBA ref | Description                                                              |
|----------|----------|-----|---------|--------------------------------------------------------------------------|
| XML-010  | ERROR    | Yes | 1.5     | Exactly one `link:schemaRef` element MUST be present. (multipleSchemaRefs) |
| XML-012  | ERROR    | Yes | 1.5     | The `schemaRef` MUST resolve to a known entry point URL. (inappropriateSchemaRef) |

### 1.4 Filing Indicators

| Rule ID  | Severity | EBA | EBA ref | Description                                                              |
|----------|----------|-----|---------|--------------------------------------------------------------------------|
| XML-020  | ERROR    | Yes | 1.6     | At least one `find:fIndicators` element MUST be present.                 |
| XML-021  | ERROR    | Yes | 1.6     | At least one filing indicator (positive or negative) MUST exist. (missingFilingIndicators) |
| XML-024  | ERROR    | Yes | 1.6     | Filing indicator values MUST match the label resources in the taxonomy. (invalidFilingIndicatorValue) |
| XML-025  | ERROR    | Yes | 1.6     | No duplicate filing indicators for the same reporting unit. (duplicateFilingIndicator) |
| XML-026  | ERROR    | Yes | 1.6     | The context referenced by filing indicators MUST NOT contain xbrli:segment or xbrli:scenario. (invalidContextForFilingIndicator) |

### 1.5 Context Structure

| Rule ID  | Severity | EBA | EBA ref | Description                                                              |
|----------|----------|-----|---------|--------------------------------------------------------------------------|
| XML-030  | ERROR    | Yes | 2.10    | All `xbrli:period` date elements MUST be `xs:date` (no dateTime, no timezone). (periodWithTimeContent, periodWithTimezone) |
| XML-031  | ERROR    | Yes | 2.13    | All periods MUST be instants (not durations). (nonInstantPeriodUsed)     |
| XML-032  | ERROR    | Yes | 2.13    | All periods MUST refer to the same reference date. (multiplePeriodsUsed) |
| XML-033  | ERROR    | Yes | 2.9     | All `xbrli:identifier` content and `@scheme` MUST be identical across contexts. (multipleIdentifiers) |
| XML-034  | ERROR    | Yes | 2.14    | `xbrli:segment` elements MUST NOT be used. (segmentUsed)                |
| XML-035  | ERROR    | Yes | 2.15    | `xbrli:scenario` children MUST only be `xbrldi:explicitMember` and/or `xbrldi:typedMember`. (scenarioContainsNonDimensionContent) |

### 1.6 Fact Structure

| Rule ID  | Severity | EBA | EBA ref | Description                                                              |
|----------|----------|-----|---------|--------------------------------------------------------------------------|
| XML-040  | ERROR    | Yes | 2.17    | The `@decimals` attribute MUST be used (not `@precision`). (precisionUsed) |
| XML-041  | ERROR    | No  | --      | The `@decimals` value MUST be a valid integer, "INF", or absent for non-numeric. |
| XML-042  | ERROR    | Yes | 2.19    | `@xsi:nil` MUST NOT be used on facts. (nilUsed)                         |
| XML-043  | ERROR    | Yes | 2.19    | String-type facts MUST NOT be empty. (emptyUsed)                        |

### 1.7 Unit Structure

| Rule ID  | Severity | EBA | EBA ref | Description                                                              |
|----------|----------|-----|---------|--------------------------------------------------------------------------|
| XML-050  | ERROR    | Yes | 2.23    | `xbrli:unit` children MUST refer to the XBRL International Unit Type Registry (UTR). (nonUtrUnit) |

### 1.8 Document-level Checks

| Rule ID  | Severity  | EBA | EBA ref | Description                                                             |
|----------|-----------|-----|---------|-------------------------------------------------------------------------|
| XML-060  | ERROR     | Yes | 2.1     | `@xml:base` MUST NOT appear anywhere in the document. (xmlBaseUsed)     |
| XML-061  | ERROR     | Yes | 2.4     | `link:linkbaseRef` MUST NOT be used. (linkbaseRefUsed)                  |
| XML-062  | ERROR     | Yes | 2.11    | `xbrli:forever` MUST NOT be used. (foreverUsed)                        |
| XML-063  | ERROR     | Yes | 1.14    | `@xsd:schemaLocation` / `@xsd:noNamespaceSchemaLocation` MUST NOT be used. (schemaLocationAttributeUsed) |
| XML-064  | ERROR     | Yes | 1.15    | `xi:include` MUST NOT be used. (xIncludeUsed)                          |
| XML-065  | WARNING   | Yes | 1.13    | The XML standalone declaration SHOULD NOT be used. (standaloneDocumentDeclarationUsed) |
| XML-066  | WARNING   | Yes | 2.7     | Unused contexts SHOULD NOT be present. (unusedContext)                  |
| XML-067  | WARNING   | Yes | 2.7     | Duplicate contexts SHOULD NOT be present. (duplicateContext)            |
| XML-068  | WARNING   | Yes | 2.22    | Unused units SHOULD NOT be present. (unusedUnit)                       |
| XML-069  | WARNING   | Yes | 2.21    | Duplicate units SHOULD NOT be present. (duplicateUnit)                 |

### 1.9 Taxonomy Conformance

| Rule ID  | Severity | EBA | EBA ref | Description                                                              |
|----------|----------|-----|---------|--------------------------------------------------------------------------|
| XML-070  | ERROR    | No  | --      | All fact element names (concepts) MUST be defined in the taxonomy for the referenced entry point. |
| XML-071  | ERROR    | No  | --      | All explicit dimension QNames used in contexts MUST be defined as dimensions in the taxonomy. |
| XML-072  | ERROR    | No  | --      | All dimension member values MUST be valid members for their respective dimension as defined in the taxonomy. |

### 1.10 Entity Identification

| Rule ID        | Severity | EBA | EBA ref | Description                                                      |
|----------------|----------|-----|---------|------------------------------------------------------------------|
| EBA-ENTITY-001 | ERROR    | Yes | 2.8     | The entity identifier `@scheme` MUST be one of the accepted schemes (`http://standards.iso.org/iso/17442` for LEI, `https://eurofiling.info/eu/rs` for qualified identifiers). (inappropriateScheme) |
| EBA-ENTITY-002 | ERROR    | Yes | 2.8     | The entity identifier value MUST follow the reporting subject conventions (LEI format, consolidation suffix, etc.). (unacceptableIdentifier) |

### 1.11 Decimals Accuracy

| Rule ID     | Severity | EBA | EBA ref | Description                                                           |
|-------------|----------|-----|---------|-----------------------------------------------------------------------|
| EBA-DEC-001 | ERROR    | Yes | 2.18    | Monetary facts: `@decimals` MUST be >= -4 (from 01/04/2025; >= -6 for FP, ESG, Pillar3, REM_DBM modules). |
| EBA-DEC-002 | ERROR    | Yes | 2.18    | Percentage facts: `@decimals` MUST be >= 4.                          |
| EBA-DEC-003 | ERROR    | Yes | 2.18    | Integer facts: `@decimals` MUST be 0.                                |
| EBA-DEC-004 | WARNING  | Yes | 2.18    | Decimals SHOULD be a realistic indication of accuracy (not excessively high). |

### 1.12 Currency Rules

| Rule ID     | Severity | EBA | EBA ref | Description                                                           |
|-------------|----------|-----|---------|-----------------------------------------------------------------------|
| EBA-CUR-001 | ERROR    | Yes | 3.1     | All monetary facts without CCA dimension `eba_CA:x1` (or qAEA `eba_qCA:qx2000`) MUST use a single "reporting currency". (multipleReportingCurrencies) |
| EBA-CUR-002 | ERROR    | Yes | 3.1     | Facts with CCA `eba_CA:x1` (or qAEA `eba_qCA:qx2000`) MUST be expressed in their currency of denomination. (currencyOfDenomination) |
| EBA-CUR-003 | ERROR    | Yes | 3.1     | For facts with CUS or CUA dimension, the unit currency MUST be consistent with the dimension value. (inconsistentCurrencyUnitAndDimension) |

### 1.13 Non-monetary Numeric Values

| Rule ID      | Severity | EBA | EBA ref | Description                                                          |
|--------------|----------|-----|---------|----------------------------------------------------------------------|
| EBA-UNIT-001 | ERROR    | Yes | 3.2     | Non-monetary numeric values MUST use the "pure" unit. (pureUnitNotUsedForMonetaryValue) |
| EBA-UNIT-002 | WARNING  | Yes | 3.2     | Rates, percentages and ratios SHOULD use decimal notation (e.g. 0.0931 not 9.31). A warning is raised when the absolute value exceeds 50, which strongly suggests percentage notation was used instead of decimal fractions. (useDecimalFractions) |


### 1.15 Additional Checks

| Rule ID     | Severity | EBA | EBA ref | Description                                                           |
|-------------|----------|-----|---------|-----------------------------------------------------------------------|
| EBA-ADD-001  | ERROR    | Yes | 2.16    | No multi-unit fact sets. (factsDifferingOnlyByUnit)                  |
| EBA-ADD-002  | ERROR    | Yes | 2.24    | Monetary units MUST be basic ISO 4217, no scaling.                   |
| EBA-ADD-003  | WARNING  | Yes | 2.25    | Footnotes are ignored. `link:footnoteLink` SHOULD NOT be present.    |
| EBA-ADD-004  | WARNING  | Yes | 2.26    | Software generator information SHOULD be present.                    |

### 1.16 Guidance

| Rule ID        | Severity | EBA | EBA ref | Description                                                       |
|----------------|----------|-----|---------|-------------------------------------------------------------------|
| EBA-GUIDE-001  | WARNING  | Yes | 3.4     | Unused namespace prefixes SHOULD NOT be declared. (unusedNamespacePrefix) |
| EBA-GUIDE-002  | WARNING  | Yes | 3.4     | Namespace prefixes SHOULD mirror canonical prefixes. (notRecommendedNamespacePrefix) |
| EBA-GUIDE-003  | WARNING  | Yes | 3.4     | Unused `@id` on facts SHOULD NOT be present. (unusedFactId)      |
| EBA-GUIDE-004  | WARNING  | Yes | 3.4     | String values SHOULD be as short as possible. (excessiveStringLength) |
| EBA-GUIDE-005  | WARNING  | Yes | 3.4     | Namespace declarations SHOULD be on the document element only. (unexpectedNamespaceDeclarations) |
| EBA-GUIDE-006  | WARNING  | Yes | 3.4     | Avoid multiple prefix declarations for the same namespace. (multiplePrefixForNamespace) |
| EBA-GUIDE-007  | WARNING  | Yes | 3.4     | String facts and domain values SHOULD NOT start/end with whitespace. (leadingOrTrailingSpacesInText) |

---

## 2. CSV Report Package Rules

**Scope:** Structural and compliance checks on xBRL-CSV report packages per the
xBRL-CSV 1.0 specification (REC 2021-10-13, errata 2023-04-19).

### 2.1 Report Package Structure

| Rule ID  | Severity | EBA | EBA ref | Post-conv. | Description                                                |
|----------|----------|-----|---------|------------|------------------------------------------------------------|
| CSV-001  | ERROR    | No  | --      | No         | The report package MUST be a valid ZIP archive.            |
| CSV-002  | ERROR    | No  | --      | No         | The ZIP MUST contain `META-INF/reportPackage.json`.        |
| CSV-003  | ERROR    | No  | --      | No         | `reportPackage.json` `documentType` MUST be `"https://xbrl.org/report-package/2023"`. |
| CSV-004  | ERROR    | No  | --      | No         | The ZIP MUST contain a `reports/` folder with at least `report.json`. |

### 2.2 Metadata File (report.json)

| Rule ID  | Severity | EBA | EBA ref | Post-conv. | Description                                                |
|----------|----------|-----|---------|------------|------------------------------------------------------------|
| CSV-010  | ERROR    | No  | --      | No         | `report.json` MUST be valid JSON.                          |
| CSV-011  | ERROR    | No  | --      | No         | `documentInfo.documentType` MUST be `"https://xbrl.org/2021/xbrl-csv"`. (xBRL-CSV 3.1.2) |
| CSV-012  | ERROR    | Yes | 1.5     | No         | `documentInfo.extends` MUST contain exactly one entry point URL. |
| CSV-013  | ERROR    | Yes | 1.5     | No         | The `extends` URL MUST resolve to a published JSON entry point. (inappropriateTaxonomyRef) |
| CSV-014  | ERROR    | No  | --      | No         | JSON representation constraints MUST be met (no duplicate keys, correct types). (xBRL-CSV 3.1.1) |
| CSV-015  | ERROR    | No  | --      | No         | All namespace prefixes used in dimension values MUST be declared in `documentInfo.namespaces`. (xBRL-CSV 3.1.5.1) |
| CSV-016  | ERROR    | No  | --      | No         | All URI aliases MUST resolve to valid absolute URIs. (xBRL-CSV 1.3) |

### 2.3 Parameters File (parameters.csv)

| Rule ID  | Severity | EBA | EBA ref | Post-conv. | Description                                                |
|----------|----------|-----|---------|------------|------------------------------------------------------------|
| CSV-020  | ERROR    | Yes | --      | No         | `parameters.csv` MUST exist in the `reports/` folder.      |
| CSV-021  | ERROR    | Yes | --      | No         | The header row MUST be `name,value`.                       |
| CSV-022  | ERROR    | Yes | --      | No         | `entityID` parameter MUST be present and non-empty.        |
| CSV-023  | ERROR    | Yes | 2.10    | No         | `refPeriod` parameter MUST be present, valid `xs:date`, and without timezone. |
| CSV-024  | ERROR    | Yes | --      | No         | `baseCurrency` parameter MUST be present if any fact references base currency. |
| CSV-025  | ERROR    | Yes | --      | No         | Decimals parameters MUST be present for each type of metric in the package. |
| CSV-026  | ERROR    | Yes | --      | No         | Decimals values MUST be valid integers or "INF".           |

### 2.4 Filing Indicators File (FilingIndicators.csv)

| Rule ID  | Severity | EBA | EBA ref | Post-conv. | Description                                                |
|----------|----------|-----|---------|------------|------------------------------------------------------------|
| CSV-030  | ERROR    | Yes | --      | No         | `FilingIndicators.csv` MUST exist in the `reports/` folder. |
| CSV-031  | ERROR    | Yes | --      | No         | The header row MUST be `templateID,reported`.              |
| CSV-032  | ERROR    | Yes | 1.6     | No         | Every `templateID` MUST be a valid filing indicator code from the taxonomy. (invalidFilingIndicatorValue) |
| CSV-033  | ERROR    | Yes | --      | No         | `reported` values MUST be boolean (`true` / `false`).      |
| CSV-034  | ERROR    | Yes | 1.6     | No         | A filing indicator MUST be present for each template in the module. (missingFilingIndicators) |
| CSV-035  | ERROR    | Yes | 1.6     | No         | No duplicate `templateID` entries. (duplicateFilingIndicator) |


### 2.5 Data Table CSV Files

| Rule ID  | Severity | EBA | EBA ref | Post-conv. | Description                                                |
|----------|----------|-----|---------|------------|------------------------------------------------------------|
| CSV-040  | ERROR    | No  | --      | No         | CSV files MUST use UTF-8 encoding. (xBRL-CSV 3.2.1)       |
| CSV-041  | ERROR    | No  | --      | No         | The first row MUST be the header row. No header cell may be empty. (xBRL-CSV 3.2.2) |
| CSV-042  | ERROR    | Yes | --      | No         | All columns defined in the corresponding JSON metadata MUST be present in the CSV header. |
| CSV-043  | ERROR    | No  | --      | No         | Each row MUST contain the same number of fields as the header. |
| CSV-044  | ERROR    | Yes | --      | No         | Key columns MUST contain a value for each reported fact.   |
| CSV-045  | ERROR    | Yes | --      | No         | Special values (`#empty`, `#none`, `#nil`, any value starting with `#`) MUST NOT be used in fact or key columns. |
| CSV-046  | ERROR    | Yes | --      | No         | The "Decimals Suffix" feature MUST NOT be used; decimals MUST come from `parameters.csv`. |
| CSV-047  | ERROR    | No  | --      | No         | Strings containing commas, linefeeds, or double quotes MUST be enclosed in double quotes, with internal double quotes escaped by doubling. (xBRL-CSV 3.2.1) |
| CSV-048  | ERROR    | Yes | --      | No         | Data tables for reported templates (filing indicator = true) MUST exist. |
| CSV-049  | WARNING  | Yes | --      | No         | Data tables for non-reported templates (filing indicator = false) SHOULD NOT exist. |

### 2.6 Fact-level Validation

| Rule ID  | Severity | EBA | EBA ref | Post-conv. | Description                                                |
|----------|----------|-----|---------|------------|------------------------------------------------------------|
| CSV-050  | ERROR    | Yes | 2.19    | No         | A fact MUST NOT be reported as `#nil`. (nilUsed)           |
| CSV-051  | ERROR    | Yes | 2.19    | No         | A fact MUST NOT be reported as `#empty`. (emptyUsed)       |
| CSV-052  | ERROR    | Yes | 2.16    | No         | Duplicate business facts (same concept, same dimensions) across tables are allowed only as complete duplicates (identical value and decimals). Inconsistent duplicates MUST NOT appear. (duplicateFactXBRL-CSV) |

### 2.7 Taxonomy Conformance

| Rule ID  | Severity | EBA | EBA ref | Post-conv. | Description                                                |
|----------|----------|-----|---------|------------|------------------------------------------------------------|
| CSV-060  | ERROR    | No  | --      | No         | All metric references in data tables MUST be defined in the taxonomy for the referenced entry point. |
| CSV-061  | ERROR    | No  | --      | No         | All dimension columns MUST correspond to dimensions defined in the taxonomy. |
| CSV-062  | ERROR    | No  | --      | No         | All dimension member values MUST be valid members for their respective dimension as defined in the taxonomy. |

### 2.8 Entity Identification

| Rule ID        | Severity | EBA | EBA ref | Post-conv. | Description                                          |
|----------------|----------|-----|---------|------------|------------------------------------------------------|
| EBA-ENTITY-001 | ERROR    | Yes | 2.8     | No        | The `entityID` parameter scheme MUST be one of the accepted schemes (`http://standards.iso.org/iso/17442` for LEI, `https://eurofiling.info/eu/rs` for qualified identifiers). (inappropriateScheme) |
| EBA-ENTITY-002 | ERROR    | Yes | 2.8     | No        | The `entityID` parameter value MUST follow the reporting subject conventions (LEI format, consolidation suffix, etc.). (unacceptableIdentifier) |

### 2.9 Decimals Accuracy

| Rule ID     | Severity | EBA | EBA ref | Post-conv. | Description                                               |
|-------------|----------|-----|---------|------------|-----------------------------------------------------------|
| EBA-DEC-001 | ERROR    | Yes | 2.18    | No        | Monetary facts: decimals MUST be >= -4 (from 01/04/2025; >= -6 for FP, ESG, Pillar3, REM_DBM modules). |
| EBA-DEC-002 | ERROR    | Yes | 2.18    | No        | Percentage facts: decimals MUST be >= 4.                 |
| EBA-DEC-003 | ERROR    | Yes | 2.18    | No        | Integer facts: decimals MUST be 0.                       |
| EBA-DEC-004 | WARNING  | Yes | 2.18    | No        | Decimals SHOULD be a realistic indication of accuracy (not excessively high). |

### 2.10 Currency Rules

| Rule ID     | Severity | EBA | EBA ref | Post-conv. | Description                                               |
|-------------|----------|-----|---------|------------|-----------------------------------------------------------|
| EBA-CUR-001 | ERROR    | Yes | 3.1     | No        | All monetary facts without CCA dimension MUST use a single "reporting currency". (multipleReportingCurrencies) |
| EBA-CUR-002 | ERROR    | Yes | 3.1     | No        | Facts with CCA dimension MUST be expressed in their currency of denomination. (currencyOfDenomination) |
| EBA-CUR-003 | ERROR    | Yes | 3.1     | No        | For facts with CUS or CUA dimension, the currency MUST be consistent with the dimension value. (inconsistentCurrencyUnitAndDimension) |

### 2.11 Non-monetary Numeric Values

| Rule ID      | Severity | EBA | EBA ref | Post-conv. | Description                                              |
|--------------|----------|-----|---------|------------|----------------------------------------------------------|
| EBA-UNIT-001 | ERROR    | Yes | 3.2     | Yes        | Non-monetary numeric values MUST use the "pure" unit. (pureUnitNotUsedForMonetaryValue) |
| EBA-UNIT-002 | ERROR    | Yes | 3.2     | Yes        | Rates, percentages and ratios MUST use decimal notation (e.g. 0.0931 not 9.31). (useDecimalFractions) |

### 2.12 Decimal Representation

| Rule ID     | Severity | EBA | EBA ref | Post-conv. | Description                                               |
|-------------|----------|-----|---------|------------|-----------------------------------------------------------|
| EBA-REP-001 | ERROR    | Yes | 3.3     | Yes        | Numeric facts MUST be expressed in specified units without scaling. Values MUST NOT be truncated to fit the decimals setting. (reportValuesAsKnownAndUnscaled) |

### 2.13 Additional Checks

| Rule ID    | Severity | EBA | EBA ref | Post-conv. | Description                                                |
|------------|----------|-----|---------|------------|------------------------------------------------------------|
| EBA-2.16.1 | ERROR   | Yes | 2.16    | Yes        | No multi-unit fact sets. (factsDifferingOnlyByUnit)        |
| EBA-2.24   | ERROR   | Yes | 2.24    | Yes        | Monetary units MUST be basic ISO 4217, no scaling.         |

### 2.14 Guidance

| Rule ID        | Severity | EBA | EBA ref | Post-conv. | Description                                          |
|----------------|----------|-----|---------|------------|------------------------------------------------------|
| EBA-GUIDE-002  | WARNING  | Yes | 3.4     | Yes        | Namespace prefixes SHOULD mirror canonical prefixes. (notRecommendedNamespacePrefix) |
| EBA-GUIDE-004  | WARNING  | Yes | 3.4     | Yes        | String values SHOULD be as short as possible. (excessiveStringLength) |
| EBA-GUIDE-007  | WARNING  | Yes | 3.4     | Yes        | String facts and domain values SHOULD NOT start/end with whitespace. (leadingOrTrailingSpacesInText) |

---

## 3. Submission Package Naming Rules

**Scope:** File naming conventions for EBA report submissions (ZIP archives and
their contents). These rules apply to both xBRL-XML and xBRL-CSV submissions
when validating the submission package.

The EBA requires submission files to follow a specific naming structure:
`ReportSubject_Country_FrameworkCodeModuleVersion_Module_ReferenceDate_CreationTimestamp.zip`

See EBA Filing Rules v5.7, "File naming structure for remittance to the EBA"
(pp. 57-61).

### 3.1 Overall File Name Structure

| Rule ID       | Severity | EBA | EBA ref       | Description                                                                    |
|---------------|----------|-----|---------------|--------------------------------------------------------------------------------|
| EBA-NAME-001  | ERROR    | Yes | File naming   | The submission ZIP file name MUST follow the pattern `ReportSubject_Country_FrameworkCodeModuleVersion_Module_ReferenceDate_CreationTimestamp.zip` (exactly six underscore-separated components plus extension). |

### 3.2 Report Subject

| Rule ID       | Severity | EBA | EBA ref       | Description                                                                    |
|---------------|----------|-----|---------------|--------------------------------------------------------------------------------|
| EBA-NAME-010  | ERROR    | Yes | File naming   | For modules with `_con`/`_ind` in the name (or before reference date 31/12/2022): the ReportSubject MUST be the LEI (individual/consolidated) or LEI + `.CRDLIQSUBGRP` (liquidity subgroup). |
| EBA-NAME-011  | ERROR    | Yes | File naming   | For modules without `_con`/`_ind` (from reference date 31/12/2022): individual reports MUST use LEI + `.IND`, consolidated MUST use LEI + `.CON`, liquidity subgroup MUST use LEI + `.CRDLIQSUBGRP`. |
| EBA-NAME-012  | ERROR    | Yes | File naming   | For country-level aggregate reports: the ReportSubject MUST be the ISO country code (two capital letters) + `000` + the aggregation type suffix (`.MEMSTAAGGALL`, `.MEMSTAAGGCRDCREINS`, `.MEMSTAAGGINVFIR`). |
| EBA-NAME-013  | ERROR    | Yes | File naming   | For authority-level aggregate reports: the ReportSubject MUST be the authority code (agreed with EBA) + `.AUTALL` (e.g. for MREL Decisions). |
| EBA-NAME-014  | ERROR    | Yes | File naming   | For MICA reports: the ReportSubject MUST be IssuerID-TokenID + `.IND`. |

### 3.3 Country

| Rule ID       | Severity | EBA | EBA ref       | Description                                                                    |
|---------------|----------|-----|---------------|--------------------------------------------------------------------------------|
| EBA-NAME-020  | ERROR    | Yes | File naming   | The Country component MUST be a valid ISO 3166-1 alpha-2 country code in uppercase (e.g. `DE`, `IT`, `FR`). |

### 3.4 Framework Code and Module Version

| Rule ID       | Severity | EBA | EBA ref       | Description                                                                    |
|---------------|----------|-----|---------------|--------------------------------------------------------------------------------|
| EBA-NAME-030  | ERROR    | Yes | File naming   | The FrameworkCodeModuleVersion MUST be the DPM/XBRL framework code in uppercase followed by the module version as a 6-digit number `XXYYZZ` (e.g. `COREP020001` for COREP taxonomy 2.0.1: XX=02, YY=00, ZZ=01). |

### 3.5 Module

| Rule ID       | Severity | EBA | EBA ref       | Description                                                                    |
|---------------|----------|-----|---------------|--------------------------------------------------------------------------------|
| EBA-NAME-040  | ERROR    | Yes | File naming   | The Module component MUST be the taxonomy module name in uppercase without underscores (e.g. `corep_lcr_con` becomes `COREPLCRCON`). For liquidity subgroup reports, it MUST be the relevant consolidated module name in uppercase (e.g. `COREPLCRDACON`). |

### 3.6 Reference Date

| Rule ID       | Severity | EBA | EBA ref       | Description                                                                    |
|---------------|----------|-----|---------------|--------------------------------------------------------------------------------|
| EBA-NAME-050  | ERROR    | Yes | File naming   | The ReferenceDate component MUST be in `YYYY-MM-DD` format (e.g. `2025-12-31`). |

### 3.7 Creation Timestamp

| Rule ID       | Severity | EBA | EBA ref       | Description                                                                    |
|---------------|----------|-----|---------------|--------------------------------------------------------------------------------|
| EBA-NAME-060  | ERROR    | Yes | File naming   | The CreationTimestamp component MUST be in `YYYYMMDDhhmmssfff` format (e.g. `20250327095525486`). |

### 3.8 Inner Content Naming

| Rule ID       | Severity | EBA | EBA ref       | Description                                                                    |
|---------------|----------|-----|---------------|--------------------------------------------------------------------------------|
| EBA-NAME-070  | ERROR    | Yes | File naming   | (XML) The ZIP MUST contain exactly one `.xbrl` file whose base name matches the ZIP file name (with `.xbrl` extension instead of `.zip`). |
| EBA-NAME-071  | ERROR    | Yes | File naming   | (CSV) The root folder inside the ZIP MUST be named identically to the ZIP file (without the `.zip` extension). |
