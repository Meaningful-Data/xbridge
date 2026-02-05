# xbridge Validation Rules -- Enumeration

**Version:** 0.1 (Draft)
**Date:** 2026-02-05
**Parent document:** [validation_specification.md](validation_specification.md)

This document enumerates all individual validation rules. Each rule has a unique
identifier, a severity, a human-readable description, and a source reference.

Rules are grouped by **domain** rather than by execution layer. The parent
specification describes *when* each rule runs depending on the input format and
EBA flag settings.

---

## 1. XML Instance Rules (XML-\*)

**Scope:** Structural checks on xBRL-XML instances.

### 1.1 XML Well-formedness and Encoding

| Rule ID  | Severity | Description                                                              |
|----------|----------|--------------------------------------------------------------------------|
| XML-001  | ERROR    | The file MUST be well-formed XML.                                        |
| XML-002  | ERROR    | The file MUST use UTF-8 encoding. (EBA 1.4 / encodingNotUtf8)           |

### 1.2 Root Element

| Rule ID  | Severity | Description                                                              |
|----------|----------|--------------------------------------------------------------------------|
| XML-003  | ERROR    | The root element MUST be `xbrli:xbrl`.                                   |

### 1.3 Schema Reference (schemaRef)

| Rule ID  | Severity | Description                                                              |
|----------|----------|--------------------------------------------------------------------------|
| XML-010  | ERROR    | Exactly one `link:schemaRef` element MUST be present. (EBA 1.5a / multipleSchemaRefs) |
| XML-011  | ERROR    | The `schemaRef` `@xlink:href` MUST contain `/mod/` and end with `.xsd`. (xbridge existing check) |
| XML-012  | ERROR    | The `schemaRef` MUST resolve to a known entry point URL. (EBA 1.5b / inappropriateSchemaRef) |

### 1.4 Filing Indicators

| Rule ID  | Severity | Description                                                              |
|----------|----------|--------------------------------------------------------------------------|
| XML-020  | ERROR    | At least one `find:fIndicators` element MUST be present.                 |
| XML-021  | ERROR    | At least one filing indicator (positive or negative) MUST exist. (EBA 1.6d / missingFilingIndicators) |
| XML-022  | ERROR    | Positive filing indicators MUST be present for all reported templates. (EBA 1.6a / missingPositiveFilingIndicator) |
| XML-023  | ERROR    | Negative filing indicators MUST be present for all unreported templates. (EBA 1.6b / missingNegativeFilingIndicator) |
| XML-024  | ERROR    | Filing indicator values MUST match the label resources in the taxonomy. (EBA 1.6.3 / invalidFilingIndicatorValue) |
| XML-025  | ERROR    | No duplicate filing indicators for the same reporting unit. (EBA 1.6.1 / duplicateFilingIndicator) |
| XML-026  | ERROR    | The context referenced by filing indicators MUST NOT contain xbrli:segment or xbrli:scenario. (EBA 1.6c / invalidContextForFilingIndicator) |
| XML-027  | ERROR    | Business facts MUST NOT appear exclusively in non-reported templates. (EBA 1.7.1 / reportedFactAssociatedWithNoPositiveFilingIndicator) |

### 1.5 Context Structure

| Rule ID  | Severity | Description                                                              |
|----------|----------|--------------------------------------------------------------------------|
| XML-030  | ERROR    | All `xbrli:period` date elements MUST be `xs:date` (no dateTime, no timezone). (EBA 2.10 / periodWithTimeContent, periodWithTimezone) |
| XML-031  | ERROR    | All xbrl periods MUST be instants (not durations). (EBA 2.13 / nonInstantPeriodUsed) |
| XML-032  | ERROR    | All xbrl periods MUST refer to the same reference date. (EBA 2.13 / multiplePeriodsUsed) |
| XML-033  | ERROR    | All `xbrli:identifier` content and `@scheme` MUST be identical across contexts. (EBA 2.9 / multipleIdentifiers) |
| XML-034  | ERROR    | `xbrli:segment` elements MUST NOT be used. (EBA 2.14 / segmentUsed)     |
| XML-035  | ERROR    | `xbrli:scenario` children MUST only be `xbrldi:explicitMember` and/or `xbrldi:typedMember`. (EBA 2.15 / scenarioContainsNonDimensionContent) |

### 1.6 Fact Structure

| Rule ID  | Severity | Description                                                              |
|----------|----------|--------------------------------------------------------------------------|
| XML-040  | ERROR    | The `@decimals` attribute MUST be used (not `@precision`). (EBA 2.17 / precisionUsed) |
| XML-041  | ERROR    | The `@decimals` value MUST be a valid integer, "INF", or absent for non-numeric. (xbridge existing check) |
| XML-042  | ERROR    | `@xsi:nil` MUST NOT be used on facts. (EBA 2.19 / nilUsed)              |
| XML-043  | ERROR    | String-type facts MUST NOT be empty. (EBA 2.19 / emptyUsed)             |

### 1.7 Unit Structure

| Rule ID  | Severity | Description                                                              |
|----------|----------|--------------------------------------------------------------------------|
| XML-050  | ERROR    | `xbrli:unit` children MUST refer to the XBRL International Unit Type Registry (UTR). (EBA 2.23 / nonUtrUnit) |

### 1.8 Document-level Checks

| Rule ID  | Severity  | Description                                                             |
|----------|-----------|-------------------------------------------------------------------------|
| XML-060  | ERROR     | `@xml:base` MUST NOT appear anywhere in the document. (EBA 2.1 / xmlBaseUsed) |
| XML-061  | ERROR     | `link:linkbaseRef` MUST NOT be used. (EBA 2.4 / linkbaseRefUsed)       |
| XML-062  | ERROR     | `xbrli:forever` MUST NOT be used. (EBA 2.11 / foreverUsed)             |
| XML-063  | ERROR     | `@xsd:schemaLocation` / `@xsd:noNamespaceSchemaLocation` MUST NOT be used. (EBA 1.14 / schemaLocationAttributeUsed) |
| XML-064  | ERROR     | `xi:include` MUST NOT be used. (EBA 1.15 / xIncludeUsed)               |
| XML-065  | WARNING   | The XML standalone declaration SHOULD NOT be used. (EBA 1.13 / standaloneDocumentDeclarationUsed) |
| XML-066  | WARNING   | Unused contexts SHOULD NOT be present. (EBA 2.7a / unusedContext)       |
| XML-067  | WARNING   | Duplicate contexts SHOULD NOT be present. (EBA 2.7b / duplicateContext) |
| XML-068  | WARNING   | Unused units SHOULD NOT be present. (EBA 2.22 / unusedUnit)            |
| XML-069  | WARNING   | Duplicate units SHOULD NOT be present. (EBA 2.21 / duplicateUnit)      |

---

## 2. CSV Report Package Rules (CSV-\*)

**Scope:** Structural and content checks on xBRL-CSV report packages per the
xBRL-CSV 1.0 specification (REC 2021-10-13, errata 2023-04-19).

### 2.1 Report Package Structure

| Rule ID  | Severity | Description                                                              |
|----------|----------|--------------------------------------------------------------------------|
| CSV-001  | ERROR    | The report package MUST be a valid ZIP archive.                          |
| CSV-002  | ERROR    | The ZIP MUST contain `META-INF/reportPackage.json`.                      |
| CSV-003  | ERROR    | `reportPackage.json` `documentType` MUST be `"https://xbrl.org/report-package/2023"`. |
| CSV-004  | ERROR    | The ZIP MUST contain a `reports/` folder with at least `report.json`.    |

### 2.2 Metadata File (report.json)

| Rule ID  | Severity | Description                                                              |
|----------|----------|--------------------------------------------------------------------------|
| CSV-010  | ERROR    | `report.json` MUST be valid JSON.                                        |
| CSV-011  | ERROR    | `documentInfo.documentType` MUST be `"https://xbrl.org/2021/xbrl-csv"`. (xBRL-CSV 3.1.2) |
| CSV-012  | ERROR    | `documentInfo.extends` MUST contain exactly one entry point URL. (xBRL-CSV 3.1.18) |
| CSV-013  | ERROR    | The `extends` URL MUST resolve to a published JSON entry point. (EBA 1.5 CSV / inappropriateTaxonomyRef) |
| CSV-014  | ERROR    | JSON representation constraints MUST be met (no duplicate keys, correct types). (xBRL-CSV 3.1.1) |
| CSV-015  | ERROR    | All namespace prefixes used in dimension values MUST be declared in `documentInfo.namespaces`. (xBRL-CSV 3.1.5.1) |
| CSV-016  | ERROR    | All URI aliases MUST resolve to valid absolute URIs. (xBRL-CSV 1.3)     |

### 2.3 Parameters File (parameters.csv)

| Rule ID  | Severity | Description                                                              |
|----------|----------|--------------------------------------------------------------------------|
| CSV-020  | ERROR    | `parameters.csv` MUST exist in the `reports/` folder.                    |
| CSV-021  | ERROR    | The header row MUST be `name,value`.                                     |
| CSV-022  | ERROR    | `entityID` parameter MUST be present and non-empty.                      |
| CSV-023  | ERROR    | `refPeriod` parameter MUST be present, valid `xs:date`, and without timezone. (EBA 2.10) |
| CSV-024  | ERROR    | `baseCurrency` parameter MUST be present if any fact references base currency. |
| CSV-025  | ERROR    | Decimals parameters MUST be present for each type of metric in the package. |
| CSV-026  | ERROR    | Decimals values MUST be valid integers or "INF".                         |

### 2.4 Filing Indicators File (FilingIndicators.csv)

| Rule ID  | Severity | Description                                                              |
|----------|----------|--------------------------------------------------------------------------|
| CSV-030  | ERROR    | `FilingIndicators.csv` MUST exist in the `reports/` folder.              |
| CSV-031  | ERROR    | The header row MUST be `templateID,reported`.                            |
| CSV-032  | ERROR    | Every `templateID` MUST be a valid filing indicator code from the taxonomy. |
| CSV-033  | ERROR    | `reported` values MUST be boolean (`true` / `false`).                    |
| CSV-034  | ERROR    | A filing indicator MUST be present for each template in the module. (EBA 1.6d) |
| CSV-035  | ERROR    | No duplicate `templateID` entries. (EBA 1.6.1 / duplicateFilingIndicator) |

### 2.5 Data Table CSV Files

| Rule ID  | Severity | Description                                                              |
|----------|----------|--------------------------------------------------------------------------|
| CSV-040  | ERROR    | CSV files MUST use UTF-8 encoding. (xBRL-CSV 3.2.1)                     |
| CSV-041  | ERROR    | The first row MUST be the header row. No header cell may be empty. (xBRL-CSV 3.2.2) |
| CSV-042  | ERROR    | All columns defined in the corresponding JSON metadata MUST be present in the CSV header. (EBA CSV extra rule 2) |
| CSV-043  | ERROR    | Each row MUST contain the same number of fields as the header. (EBA CSV extra rule 3) |
| CSV-044  | ERROR    | Key columns MUST contain a value for each reported fact. (EBA CSV extra rule 4) |
| CSV-045  | ERROR    | Special values (`#empty`, `#none`, `#nil`, any value starting with `#`) MUST NOT be used in fact or key columns. (EBA CSV extra rule 5) |
| CSV-046  | ERROR    | The "Decimals Suffix" feature MUST NOT be used; decimals MUST come from `parameters.csv`. (EBA CSV extra rule 1) |
| CSV-047  | ERROR    | Strings containing commas, linefeeds, or double quotes MUST be enclosed in double quotes, with internal double quotes escaped by doubling. (xBRL-CSV 3.2.1) |
| CSV-048  | ERROR    | Data tables for reported templates (filing indicator = true) MUST exist. |
| CSV-049  | WARNING  | Data tables for non-reported templates (filing indicator = false) SHOULD NOT exist. |

### 2.6 Fact-level Validation

| Rule ID  | Severity | Description                                                              |
|----------|----------|--------------------------------------------------------------------------|
| CSV-050  | ERROR    | A fact MUST NOT be reported as `#nil`. (EBA 2.19 / nilUsed)             |
| CSV-051  | ERROR    | A fact MUST NOT be reported as `#empty`. (EBA 2.19 / emptyUsed)         |
| CSV-052  | ERROR    | Duplicate business facts MUST NOT appear (same dimensions, same concept). (EBA 2.16) |
| CSV-053  | ERROR    | Facts MUST NOT appear exclusively in non-reported templates. (EBA 1.7.1) |

---

## 3. EBA Filing Rules (EBA-\*)

**Scope:** Additional constraints imposed by the EBA Filing Rules v5.7
(EBA/XBRL/2025/11). These rules apply to both XML and CSV inputs when the
EBA flag is enabled.

### 3.1 Filing Syntax Rules (EBA Section 1)

| Rule ID    | Severity | Description                                                            |
|------------|----------|------------------------------------------------------------------------|
| EBA-1.1    | WARNING  | xBRL-XML reports SHOULD use `.xbrl` extension. xBRL-CSV reports SHOULD be ZIP archives. |
| EBA-1.4    | ERROR    | UTF-8 encoding MUST be used. (encodingNotUtf8) -- already covered by XML-002 / CSV-040. |
| EBA-1.5    | ERROR    | Entry point MUST be a valid published EBA entry point. -- already covered by XML-012 / CSV-013. |
| EBA-1.9    | ERROR    | The report MUST be valid XBRL 2.1 / Dimensions 1.0 (XML) or xBRL-CSV 1.0 (CSV). (notValidXbrlDocument) |
| EBA-1.10a  | ERROR    | The report MUST be valid with regards to taxonomy validation rules (XBRL Formula). (notValidAccordingToTaxonomyValidationRules) |
| EBA-1.10b  | ERROR    | The report MUST be valid with regards to ITS validation rules. (notValidAccordingToITSValidationRules) |
| EBA-1.11   | ERROR    | Reporters MUST NOT reference extension taxonomies. (inappropriateSchemaRef) |
| EBA-1.12   | ERROR    | Reports MUST be complete (full resubmission, no partial data). (incompleteReport) |

### 3.2 XBRL Report Syntax Rules (EBA Section 2)

Rules already covered by XML-\* or CSV-\* rules are marked as "delegated".

| Rule ID    | Severity | Description                                                            | Delegated to |
|------------|----------|------------------------------------------------------------------------|--------------|
| EBA-2.1    | ERROR    | `@xml:base` MUST NOT appear. (xmlBaseUsed)                             | XML-060 |
| EBA-2.2    | ERROR    | Taxonomy reference MUST be absolute URL. (inappropriateSchemaRef)      | XML-012 |
| EBA-2.3    | ERROR    | Only one taxonomy reference per report. (multipleSchemaRefs)           | XML-010 |
| EBA-2.4    | ERROR    | `link:linkbaseRef` MUST NOT be used. (linkbaseRefUsed)                 | XML-061 |
| EBA-2.5    | WARNING  | Comments are ignored; data MUST be in contexts/units/facts.            | -- |
| EBA-2.6    | WARNING  | `@id` SHOULD NOT convey semantics; SHOULD be short.                    | -- |
| EBA-2.7    | WARNING  | Unused/duplicate contexts SHOULD NOT be present.                       | XML-066, XML-067 |
| EBA-2.8    | ERROR    | Entity identifier scheme and value MUST be acceptable. (inappropriateScheme, unacceptableIdentifier) | EBA-specific |
| EBA-2.9    | ERROR    | Single subject per report. (multipleIdentifiers)                       | XML-033 |
| EBA-2.10   | ERROR    | Period dates MUST be xs:date without timezone.                         | XML-030 |
| EBA-2.11   | ERROR    | `xbrli:forever` MUST NOT be used.                                      | XML-062 |
| EBA-2.13   | ERROR    | All periods MUST be instants, same reference date.                     | XML-031, XML-032 |
| EBA-2.14   | ERROR    | `xbrli:segment` MUST NOT be used.                                      | XML-034 |
| EBA-2.15   | ERROR    | `xbrli:scenario` restricted to dimension members only.                 | XML-035 |
| EBA-2.16   | ERROR    | No duplicate business facts. (duplicateFactXBRL-XML)                   | CSV-052 |
| EBA-2.16.1 | ERROR   | No multi-unit fact sets. (factsDifferingOnlyByUnit)                    | EBA-specific |
| EBA-2.17   | ERROR    | `@precision` MUST NOT be used (XML only).                              | XML-040 |
| EBA-2.18   | ERROR    | Decimals accuracy requirements (see table below).                      | EBA-specific |
| EBA-2.19   | ERROR    | `@xsi:nil` and empty values MUST NOT be used.                          | XML-042, CSV-050, CSV-051 |
| EBA-2.21   | WARNING  | Duplicate units SHOULD NOT be present.                                 | XML-069 |
| EBA-2.22   | WARNING  | Unused units SHOULD NOT be present.                                    | XML-068 |
| EBA-2.23   | ERROR    | Units MUST refer to UTR.                                               | XML-050 |
| EBA-2.24   | ERROR    | Monetary units MUST be basic ISO 4217, no scaling.                     | EBA-specific |
| EBA-2.25   | WARNING  | Footnotes are ignored.                                                 | -- |
| EBA-2.26   | WARNING  | Software generator information SHOULD be present.                      | EBA-specific |

### 3.3 Entity Identification (EBA 2.8, 3.6)

| Rule ID    | Severity | Description                                                            |
|------------|----------|------------------------------------------------------------------------|
| EBA-ENTITY-001 | ERROR | The entity identifier `@scheme` MUST be one of the accepted schemes (`http://standards.iso.org/iso/17442` for LEI, `https://eurofiling.info/eu/rs` for qualified identifiers). |
| EBA-ENTITY-002 | ERROR | The entity identifier value MUST follow the reporting subject conventions (LEI format, consolidation suffix, etc.). |

### 3.4 Decimals Accuracy (EBA 2.18)

| Rule ID    | Severity | Description                                                            |
|------------|----------|------------------------------------------------------------------------|
| EBA-DEC-001 | ERROR  | Monetary facts: `@decimals` MUST be >= -4 (from submission date 01/04/2025; >= -6 for FP, ESG, Pillar3, REM_DBM modules). |
| EBA-DEC-002 | ERROR  | Percentage facts: `@decimals` MUST be >= 4.                           |
| EBA-DEC-003 | ERROR  | Integer facts: `@decimals` MUST be 0.                                 |
| EBA-DEC-004 | WARNING | Decimals SHOULD be a realistic indication of accuracy (not excessively high). |

### 3.5 Currency Rules (EBA 3.1)

| Rule ID    | Severity | Description                                                            |
|------------|----------|------------------------------------------------------------------------|
| EBA-CUR-001 | ERROR  | All monetary facts without CCA dimension `eba_CA:x1` (or qAEA `eba_qCA:qx2000`) MUST use a single "reporting currency". (multipleReportingCurrencies) |
| EBA-CUR-002 | ERROR  | Facts with CCA `eba_CA:x1` (or qAEA `eba_qCA:qx2000`) MUST be expressed in their currency of denomination. (currencyOfDenomination) |
| EBA-CUR-003 | ERROR  | For facts with CUS or CUA dimension, the unit currency MUST be consistent with the dimension value. (inconsistentCurrencyUnitAndDimension) |

### 3.6 Non-monetary Numeric Values (EBA 3.2)

| Rule ID    | Severity | Description                                                            |
|------------|----------|------------------------------------------------------------------------|
| EBA-UNIT-001 | ERROR  | Non-monetary numeric values MUST use the "pure" unit. (pureUnitNotUsedForMonetaryValue) |
| EBA-UNIT-002 | ERROR  | Rates, percentages and ratios MUST use decimal notation (e.g. 0.0931 not 9.31). (useDecimalFractions) |

### 3.7 Decimal Representation (EBA 3.3)

| Rule ID    | Severity | Description                                                            |
|------------|----------|------------------------------------------------------------------------|
| EBA-REP-001 | ERROR  | Numeric facts MUST be expressed in specified units without scaling. Values MUST NOT be truncated to fit the decimals setting (e.g. 2561000 not 2561 with decimals=-3). (reportValuesAsKnownAndUnscaled) |

### 3.8 Additional Guidance (EBA Section 3)

| Rule ID    | Severity | Description                                                            |
|------------|----------|------------------------------------------------------------------------|
| EBA-GUIDE-001 | WARNING | Unused namespace prefixes SHOULD NOT be declared (XML only). (unusedNamespacePrefix) |
| EBA-GUIDE-002 | WARNING | Namespace prefixes SHOULD mirror canonical prefixes. (notRecommendedNamespacePrefix) |
| EBA-GUIDE-003 | WARNING | Unused `@id` on facts SHOULD NOT be present. (unusedFactId)           |
| EBA-GUIDE-004 | WARNING | String values SHOULD be as short as possible. (excessiveStringLength) |
| EBA-GUIDE-005 | WARNING | Namespace declarations SHOULD be on the document element only (XML). (unexpectedNamespaceDeclarations) |
| EBA-GUIDE-006 | WARNING | Avoid multiple prefix declarations for the same namespace (XML). (multiplePrefixForNamespace) |
| EBA-GUIDE-007 | WARNING | String facts and domain values SHOULD NOT start/end with whitespace. (leadingOrTrailingSpacesInText) |

### 3.9 xBRL-CSV Extra Rules (EBA Filing Rules pp. 64-65)

| Rule ID    | Severity | Description                                                            |
|------------|----------|------------------------------------------------------------------------|
| EBA-CSV-001 | ERROR  | "Decimals Suffix" feature MUST NOT be used. Decimals MUST come from `parameters.csv`. |
| EBA-CSV-002 | ERROR  | No header cell may be empty. All columns from JSON metadata MUST be in the CSV. |
| EBA-CSV-003 | ERROR  | Each row MUST have the same number of fields as the header.            |
| EBA-CSV-004 | ERROR  | Key columns MUST contain a value for each reported fact.               |
| EBA-CSV-005 | ERROR  | Special values (`#empty`, `#none`, `#nil`, any `#`-prefixed value) MUST NOT appear in fact or key columns. |

---

## 4. Redundancy Map: CSV Rules that Mirror XML Rules

When validating a CSV file **after conversion from XML** (i.e. with
`post_conversion = True`), the following CSV checks are redundant because the
equivalent logic was already verified on the XML input. These rules are
**skipped** in post-conversion mode.

| CSV Rule     | Mirrors XML Rule(s)   | What is checked                              |
|--------------|-----------------------|----------------------------------------------|
| CSV-022      | XML-033               | Entity identifier present and consistent.    |
| CSV-023      | XML-030, XML-031      | Period is a valid instant date.               |
| CSV-026      | XML-041               | Decimals values are valid.                    |
| CSV-032      | XML-024               | Filing indicator codes match taxonomy.        |
| CSV-034      | XML-021               | At least one filing indicator present.        |
| CSV-035      | XML-025               | No duplicate filing indicators.               |

All other CSV-\* rules (package structure, metadata, data table format, fact
checks) always run because they validate the CSV artifact itself, which is
newly produced during conversion.
