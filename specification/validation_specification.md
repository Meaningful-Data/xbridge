# xbridge Validation Module -- Specification

**Version:** 0.3 (Draft)
**Date:** 2026-02-16

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
| `eba`              | `True` \| `False`  | When `True`, additionally runs EBA-specific rules.     |
| `post_conversion`  | `True` \| `False`  | *(CSV only)* When `True`, skips all structural, format, and taxonomy checks that are guaranteed by xbridge's converter, keeping only EBA semantic checks. Has no effect for `.xbrl` files. |

This yields the following effective combinations:

| File        | `eba`   | `post_conversion` | Rules applied                                          | Typical use case |
|-------------|---------|-------------------|--------------------------------------------------------|------------------|
| `.xbrl`     | `False` | --                 | XML rules (EBA = No)                                  | Basic XBRL structural check. |
| `.xbrl`     | `True`  | --                 | All XML rules                                         | Full EBA validation of an xBRL-XML file.   |
| `.zip`      | `False` | `False`            | CSV rules (EBA = No)                                  | Standard xBRL-CSV structural check.        |
| `.zip`      | `True`  | `False`            | All CSV rules                                         | Full EBA validation of a standalone xBRL-CSV package. |
| `.zip`      | `True`  | `True`             | EBA semantic checks only (Post-conv. = Yes)           | EBA compliance check after xbridge conversion. |

### 1.3 Rule Organization

Rules are organized into two sets based on the input format. Each rule carries
attributes that control when it is executed. See
[validations_enumeration.md](validations_enumeration.md) for the full list.

| Rule set              | Prefixes          | Applies when               |
|-----------------------|-------------------|----------------------------|
| XML Instance Rules    | `XML-*`, `EBA-*`  | `.xbrl` file               |
| CSV Package Rules     | `CSV-*`, `EBA-*`  | `.zip` file                |

Each rule has the following attributes:

| Attribute      | Values   | Meaning                                                                 |
|----------------|----------|-------------------------------------------------------------------------|
| **EBA**        | Yes / No | When Yes, the rule only runs if the `eba` parameter is `True`.          |
| **EBA ref**    | Section  | Cross-reference to the EBA Filing Rules v5.7 section.                   |
| **Post-conv.** | Yes / No | *(CSV only)* When No, the rule is skipped if `post_conversion` is `True`. |

Key points:

- **XML** and **CSV** rules are mutually exclusive -- they are selected by the
  file extension.
- Within each set, rules with `EBA = No` always run. Rules with `EBA = Yes`
  only run when the `eba` parameter is `True`.
- EBA-specific rules keep the `EBA-` prefix in their rule identifiers for
  traceability (e.g. `EBA-ENTITY-001`, `EBA-DEC-001`).
- Format-independent EBA rules (entity identification, decimals accuracy,
  currency, etc.) appear in **both** rule sets with format-appropriate checks.

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
RuleId:       str     -- unique identifier, e.g. "XML-001", "CSV-012", "EBA-DEC-001"
Severity:     ERROR | WARNING | INFO
RuleSet:      xml | csv
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
  ├─ file ends with ".xbrl" → ruleset = XML
  │
  └─ file ends with ".zip"  → ruleset = CSV

  For each rule in the selected ruleset:
    ├─ rule.eba = Yes  AND  eba = False          → SKIP
    ├─ ruleset = CSV  AND  rule.post_conv = No  AND  post_conversion = True  → SKIP
    └─ Otherwise                                  → RUN
```

### 2.2 Post-conversion Redundancy

When xbridge converts an XML file to CSV, it first validates the XML input and
then generates the CSV output. A subsequent validation of the CSV output should
not repeat checks that are guaranteed by construction:

- **Structural and format checks** (sections 2.1–2.6): xbridge generates
  correct package structure, metadata, parameters, filing indicators, data
  tables, and fact-level encoding. These are redundant.
- **Taxonomy conformance** (section 2.7): already validated on the XML source.
- **Logical checks already applied to XML** (e.g. entity identification,
  period validity, decimals validity, filing indicator codes): already enforced
  on the XML input.

The `post_conversion` flag controls this. When set to `True`, all CSV rules
with **Post-conv. = No** are skipped. In practice, this means sections 2.1–2.7
are skipped entirely. From the EBA semantic checks (sections 2.8–2.14), only
the rules explicitly marked **Post-conv. = Yes** in the enumeration are
executed — specifically the unit, representation, additional, and guidance
checks from sections 2.11–2.14. Entity identification (§2.8), decimals
accuracy (§2.9), and currency rules (§2.10) are also skipped because they were
already enforced on the XML input.

---

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
