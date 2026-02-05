# xbridge Validation Module -- Specification

**Version:** 0.2 (Draft)
**Date:** 2026-02-05

## 1. Overview

This document specifies the validation module for xbridge. The validator operates
on XBRL instance files -- both xBRL-XML and xBRL-CSV formats -- and produces a
structured set of validation results (errors, warnings, informational messages).

The full enumeration of individual validation rules is maintained separately in
[validations_enumeration.md](validations_enumeration.md).

### 1.1 Design Goals

- **Orthogonal parameters:** Input format (XML / CSV) and EBA filing rules
  (on / off) are independent choices. Any combination is valid.
- **Post-conversion awareness:** When a CSV file was produced by xbridge from
  a previously validated XML file, redundant logical checks can be skipped.
- **Actionable output:** Every finding carries a severity, a rule identifier, a
  human-readable message, and a locator pointing to the offending element.

### 1.2 Format Detection and Parameters

The input format is **detected automatically** from the file extension:

| Extension          | Detected format |
|--------------------|-----------------|
| `.xbrl`            | XML             |
| `.zip`             | CSV             |

The caller controls validation behaviour through two optional flags:

| Parameter          | Values             | Meaning                                                |
|--------------------|--------------------|--------------------------------------------------------|
| `eba`              | `True` \| `False`  | When `True`, additionally applies EBA Filing Rules.    |
| `post_conversion`  | `True` \| `False`  | *(CSV only)* When `True`, skips CSV checks that are redundant with XML checks already performed during conversion. Ignored for `.xbrl` files. |

This yields the following effective combinations:

| File        | `eba`   | `post_conversion` | Rules applied                              | Typical use case |
|-------------|---------|--------------------|--------------------------------------------|------------------|
| `.xbrl`     | `False` | --                 | XML-\*                                     | Pre-conversion structural check of an xBRL-XML file. |
| `.xbrl`     | `True`  | --                 | XML-\* + EBA-\*                            | Full EBA validation of an xBRL-XML file.   |
| `.zip`      | `False` | `False`            | CSV-\* (all)                               | Validate a standalone xBRL-CSV package.    |
| `.zip`      | `False` | `True`             | CSV-\* (minus redundant)                   | Validate an xBRL-CSV package produced by xbridge conversion. |
| `.zip`      | `True`  | `False`            | CSV-\* (all) + EBA-\*                      | Full EBA validation of a standalone xBRL-CSV package. |
| `.zip`      | `True`  | `True`             | CSV-\* (minus redundant) + EBA-\*          | Full EBA validation after xbridge conversion. |

### 1.3 Rule Sets

Rules are grouped into three sets. See
[validations_enumeration.md](validations_enumeration.md) for the full list.

| Rule set              | Prefix   | Applies when               |
|-----------------------|----------|----------------------------|
| XML Instance Rules    | `XML-*`  | `.xbrl` file               |
| CSV Package Rules     | `CSV-*`  | `.zip` file                |
| EBA Filing Rules      | `EBA-*`  | `eba = True`               |

Key points:

- **XML-\*** and **CSV-\*** are mutually exclusive -- they are selected by
  the file extension.
- **EBA-\*** is additive -- it runs on top of whichever format-specific set is
  active.
- Many EBA rules are already covered by the format-specific sets (the
  enumeration document marks these as "delegated"). The EBA engine only checks
  the rules that are **not** delegated.

### 1.4 Severity Levels

Following the EBA Filing Rules language conventions (RFC 2119):

| Severity    | Meaning                                                                     |
|-------------|-----------------------------------------------------------------------------|
| `ERROR`     | Violation of a MUST rule. The file is invalid.                              |
| `WARNING`   | Violation of a SHOULD rule. The file is technically acceptable but deviates from best practice. |
| `INFO`      | Informational observation. No rule is violated.                             |

### 1.5 Validation Result Structure

Each individual finding is represented as:

```
RuleId:       str     -- unique identifier, e.g. "XML-001", "CSV-012", "EBA-2.13"
Severity:     ERROR | WARNING | INFO
RuleSet:      xml | csv | eba
Message:      str     -- human-readable description
Location:     str     -- XPath (XML) or file:row:col (CSV) locator
Context:      dict    -- optional key-value bag with offending values, expected values, etc.
```

---

## 2. Architecture

### 2.1 Decision Diagram

```
validate(file, eba=False, post_conversion=False)
  │
  ├─ file ends with ".xbrl" → format = XML
  │    ├─ Run XML-* rules
  │    └─ eba?
  │         └─ Yes → Run EBA-* rules (XML-applicable subset)
  │
  └─ file ends with ".zip" → format = CSV
       ├─ post_conversion?
       │    ├─ False → Run CSV-* rules (all)
       │    └─ True  → Run CSV-* rules (skip redundant; see §2.2)
       └─ eba?
            └─ Yes → Run EBA-* rules (CSV-applicable subset)
```

### 2.2 Post-conversion Redundancy

When xbridge converts an XML file to CSV, it first validates the XML input. A
subsequent validation of the CSV output should not repeat checks that were
already applied to the XML source.

The `post_conversion` flag controls this. When set to `True`, the following CSV
rules are **skipped** because their logic was already enforced on the XML input:

| Skipped CSV Rule | Equivalent XML Rule(s) | What is checked                           |
|------------------|------------------------|-------------------------------------------|
| CSV-022          | XML-033                | Entity identifier present and consistent. |
| CSV-023          | XML-030, XML-031       | Period is a valid instant date.            |
| CSV-026          | XML-041                | Decimals values are valid.                 |
| CSV-032          | XML-024                | Filing indicator codes match taxonomy.     |
| CSV-034          | XML-021                | At least one filing indicator present.     |
| CSV-035          | XML-025                | No duplicate filing indicators.            |

All other CSV rules always run regardless of `post_conversion`, because they
validate the CSV artifact itself (package structure, metadata format, data
table syntax, fact-level checks).

The complete redundancy map is also documented in
[validations_enumeration.md](validations_enumeration.md), Section 4.

### 2.3 EBA Rules: Format Applicability

Some EBA rules are format-specific:

- **XML-only EBA rules:** EBA-2.1 (`@xml:base`), EBA-2.4 (`linkbaseRef`),
  EBA-2.17 (`@precision`), EBA-GUIDE-001, EBA-GUIDE-005, EBA-GUIDE-006
  (namespace-related). These are skipped for `.zip` files.

- **CSV-only EBA rules:** EBA-CSV-001 through EBA-CSV-005 (CSV extra rules).
  These are skipped for `.xbrl` files.

- **Format-independent EBA rules:** Entity identification (EBA-ENTITY-\*),
  decimals accuracy (EBA-DEC-\*), currency (EBA-CUR-\*), units
  (EBA-UNIT-\*), decimal representation (EBA-REP-\*), and other
  guidance rules. These apply regardless of format.

### 2.4 Delegation

Many EBA rules overlap with format-specific rules. To avoid duplication, the
EBA engine delegates these checks to the format-specific validators. The
delegation map is documented in the enumeration file (Section 3.2, "Delegated
to" column). The EBA engine only executes rules that are:

1. Not delegated to a format-specific rule, **and**
2. Applicable to the detected input format.


## 3. Public API (Sketch)

```python
from xbridge.validation import validate, ValidationResult

# Format is detected from extension: .xbrl → XML rules, .zip → CSV rules
results: list[ValidationResult] = validate(
    file="path/to/instance.xbrl",    # or path to a .zip CSV package
    eba=False,                         # include EBA filing rules?
    post_conversion=False,             # skip XML-redundant CSV checks?
)

for r in results:
    print(f"[{r.severity}] {r.rule_id}: {r.message} at {r.location}")
```

When integrated with the existing `convert_instance()` flow:

```python
# 1. Validate XML input (format detected from .xbrl extension)
xml_results = validate("input.xbrl", eba=True)
if any(r.severity == "ERROR" for r in xml_results):
    raise ValidationError(xml_results)

# 2. Convert
convert_instance("input.xbrl", output_dir="out/")

# 3. Validate CSV output (format detected from .zip extension)
csv_results = validate("out/output.zip", eba=True, post_conversion=True)
```

---

## 4. Reference Documents

| Document | Location | Version |
|----------|----------|---------|
| XBRL 2.1 Specification | `specification/xbrl/Extensible Business Reporting Language (XBRL) 2.1.mhtml` | REC 2003-12-31, errata 2013-02-20 |
| XBRL Dimensions 1.0 | `specification/xbrl/XBRL Dimensions 1.0.mhtml` | 1.0 |
| xBRL-CSV 1.0 | `specification/xbrl/xBRL-CSV_ CSV representation of XBRL data 1.0.mhtml` | REC 2021-10-13, errata 2023-04-19 |
| EBA Filing Rules | `specification/eba/eba_filing_rules_v5.7_2025_11_24.pdf` | v5.7, November 2025 |


## 5. Taxonomy-less Validation

The validation module does **not** load the full XBRL taxonomy at runtime.
Instead, all taxonomy-derived metadata required for validation (entry points,
filing indicator codes, dimension domains, metric types, etc.) is pre-processed
and shipped as JSON files in `src/xbridge/modules/`. This is the same approach
xbridge already uses for conversion.

This design principle keeps the library fast and self-contained: no network
access, no taxonomy resolution, no XML schema parsing at validation time. If a
validation rule requires additional taxonomy information, the JSON modules are
extended at build time rather than loading the full taxonomy at runtime.


## 6. Out of scope

1. **XBRL Formula validation (EBA 1.10):** Full formula validation requires a
   formula processor. 