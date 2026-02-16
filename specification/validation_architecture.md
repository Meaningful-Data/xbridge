# xbridge Validation Module — Architecture

**Version:** 0.1 (Draft)
**Date:** 2026-02-16
**Parent document:** [validation_specification.md](validation_specification.md)

This document describes the technical architecture of the xbridge validation
module. It complements the functional specification
([validation_specification.md](validation_specification.md)) and the rule
catalogue ([validations_enumeration.md](validations_enumeration.md)) with
implementation-level design decisions.

---

## 1. Rule Registry

All validation rules are declared in a single, editable JSON file:

```
src/xbridge/validation/registry.json
```

The registry is the **single source of truth** for rule metadata. Behavioural
changes — adjusting severity, toggling the EBA flag, changing messages, or
disabling rules (by removing their entries) — are made by editing this file
without touching implementation code.

### 1.1 Registry Entry Schema

Each entry in the registry array represents one rule:

```json
{
  "code": "EBA-DEC-001",
  "message": "Monetary facts: decimals MUST be >= {min_decimals}.",
  "severity": "ERROR",
  "xml": true,
  "csv": true,
  "eba": true,
  "post_conversion": false,
  "eba_ref": "2.18"
}
```

| Field              | Type                     | Description |
|--------------------|--------------------------|-------------|
| `code`             | `str`                    | Unique rule identifier (e.g. `"XML-001"`, `"CSV-012"`, `"EBA-DEC-001"`). |
| `message`          | `str`                    | Human-readable template. Supports `{placeholder}` syntax filled from the finding context dict at runtime. |
| `severity`         | `"ERROR"` \| `"WARNING"` \| `"INFO"` | Default severity level (see §1.4 of the specification). |
| `xml`              | `bool`                   | `true` if the rule applies to `.xbrl` input. |
| `csv`              | `bool`                   | `true` if the rule applies to `.zip` input. |
| `eba`              | `bool`                   | `true` if the rule only runs when the `eba` parameter is `True`. |
| `post_conversion`  | `bool`                   | `true` = rule survives post-conversion mode; `false` = skipped. Only meaningful when `csv` is `true`. |
| `eba_ref`          | `str` \| `null`          | EBA Filing Rules v5.7 section reference, or `null` for non-EBA rules. |

### 1.2 Format Applicability

- **XML-only rules** (`XML-*` codes): `xml: true`, `csv: false`.
- **CSV-only rules** (`CSV-*` codes): `xml: false`, `csv: true`.
- **Shared EBA rules** (`EBA-*` codes that appear in both rule sets):
  `xml: true`, `csv: true`. These rules require format-specific
  implementations (see §3.2).

For XML-only rules, the `post_conversion` field is irrelevant (never
evaluated) and conventionally set to `false`.

### 1.3 Format-Specific Severity Overrides

Most shared rules have identical severity across formats. In the rare case
where a rule's severity differs between XML and CSV (e.g. `EBA-UNIT-002` is
`WARNING` in XML but `ERROR` in CSV, reflecting the SHOULD vs MUST distinction
in the specification), the registry supports an optional override field:

```json
{
  "code": "EBA-UNIT-002",
  "message": "Rates, percentages and ratios SHOULD use decimal notation.",
  "severity": "WARNING",
  "xml": true,
  "csv": true,
  "eba": true,
  "post_conversion": true,
  "eba_ref": "3.2",
  "csv_severity": "ERROR",
  "csv_message": "Rates, percentages and ratios MUST use decimal notation."
}
```

| Override field   | Type                     | Description |
|------------------|--------------------------|-------------|
| `csv_severity`   | `"ERROR"` \| `"WARNING"` \| `"INFO"` \| absent | If present, overrides `severity` when running in CSV context. |
| `csv_message`    | `str` \| absent          | If present, overrides `message` when running in CSV context. |

These override fields are optional. When absent, the base `severity` and
`message` apply to all formats. This keeps the common case clean (one entry,
no overrides) while handling the edge cases explicitly.

### 1.4 Operational Changes via the Registry

The following changes can be made by editing `registry.json` alone:

| Change | How |
|--------|-----|
| Adjust severity | Change the `severity` (or `csv_severity`) value. |
| Disable a rule | Remove the entry entirely, or set both `xml` and `csv` to `false`. |
| Enable/disable EBA gating | Toggle the `eba` field. |
| Toggle post-conversion survival | Toggle the `post_conversion` field. |
| Edit the user-facing message | Modify the `message` (or `csv_message`) template. |
| Add a new rule | Add an entry; if no implementation exists yet, the rule is silently skipped. |

---

## 2. Module Structure

```
src/xbridge/validation/
├── __init__.py              # Public API: validate(), ValidationResult, Severity
├── _models.py               # RuleDefinition, ValidationResult, Severity
├── _registry.py             # rule_impl decorator, get_rule_impl(), load_registry()
├── _engine.py               # Rule selection logic, execution loop
├── _context.py              # ValidationContext passed to rule functions
├── registry.json            # The editable rule registry
└── rules/                   # Rule implementations (one file per specification section)
    ├── __init__.py           # Imports all submodules to trigger decorator registration
    ├── xml_wellformedness.py # XML-001, XML-002, XML-003
    ├── xml_schema_ref.py     # XML-010, XML-012
    ├── xml_filing_indicators.py  # XML-020 – XML-026
    ├── xml_context.py        # XML-030 – XML-035
    ├── xml_facts.py          # XML-040 – XML-043
    ├── xml_units.py          # XML-050
    ├── xml_document.py       # XML-060 – XML-069
    ├── xml_taxonomy.py       # XML-070 – XML-072
    ├── csv_package.py        # CSV-001 – CSV-004
    ├── csv_metadata.py       # CSV-010 – CSV-016
    ├── csv_parameters.py     # CSV-020 – CSV-026
    ├── csv_filing_indicators.py  # CSV-030 – CSV-035
    ├── csv_data_tables.py    # CSV-040 – CSV-049
    ├── csv_facts.py          # CSV-050 – CSV-052
    ├── csv_taxonomy.py       # CSV-060 – CSV-062
    ├── eba_entity.py         # EBA-ENTITY-001, EBA-ENTITY-002  (shared)
    ├── eba_decimals.py       # EBA-DEC-001 – EBA-DEC-004       (shared)
    ├── eba_currency.py       # EBA-CUR-001 – EBA-CUR-003       (shared)
    ├── eba_units.py          # EBA-UNIT-001, EBA-UNIT-002       (shared)
    ├── eba_representation.py # EBA-REP-001                      (shared)
    ├── eba_additional.py     # EBA-2.5, EBA-2.16.1, EBA-2.24, EBA-2.25, EBA-2.26
    └── eba_guidance.py       # EBA-GUIDE-001 – EBA-GUIDE-007
```

### 2.1 File-to-Section Mapping

Each rule implementation file corresponds to one section of the
[validations_enumeration.md](validations_enumeration.md):

| File | Enumeration section | Rules |
|------|---------------------|-------|
| `xml_wellformedness.py` | §1.1 Well-formedness, §1.2 Root Element | XML-001, XML-002, XML-003 |
| `xml_schema_ref.py` | §1.3 Schema Reference | XML-010, XML-012 |
| `xml_filing_indicators.py` | §1.4 Filing Indicators | XML-020 – XML-026 |
| `xml_context.py` | §1.5 Context Structure | XML-030 – XML-035 |
| `xml_facts.py` | §1.6 Fact Structure | XML-040 – XML-043 |
| `xml_units.py` | §1.7 Unit Structure | XML-050 |
| `xml_document.py` | §1.8 Document-level Checks | XML-060 – XML-069 |
| `xml_taxonomy.py` | §1.9 Taxonomy Conformance | XML-070 – XML-072 |
| `csv_package.py` | §2.1 Report Package Structure | CSV-001 – CSV-004 |
| `csv_metadata.py` | §2.2 Metadata File | CSV-010 – CSV-016 |
| `csv_parameters.py` | §2.3 Parameters File | CSV-020 – CSV-026 |
| `csv_filing_indicators.py` | §2.4 Filing Indicators File | CSV-030 – CSV-035 |
| `csv_data_tables.py` | §2.5 Data Table CSV Files | CSV-040 – CSV-049 |
| `csv_facts.py` | §2.6 Fact-level Validation | CSV-050 – CSV-052 |
| `csv_taxonomy.py` | §2.7 Taxonomy Conformance | CSV-060 – CSV-062 |
| `eba_entity.py` | §1.10 / §2.8 Entity Identification | EBA-ENTITY-001, EBA-ENTITY-002 |
| `eba_decimals.py` | §1.11 / §2.9 Decimals Accuracy | EBA-DEC-001 – EBA-DEC-004 |
| `eba_currency.py` | §1.12 / §2.10 Currency Rules | EBA-CUR-001 – EBA-CUR-003 |
| `eba_units.py` | §1.13 / §2.11 Non-monetary Numeric Values | EBA-UNIT-001, EBA-UNIT-002 |
| `eba_representation.py` | §1.14 / §2.12 Decimal Representation | EBA-REP-001 |
| `eba_additional.py` | §1.15 / §2.13 Additional Checks | EBA-2.5, EBA-2.16.1, EBA-2.24, EBA-2.25, EBA-2.26 |
| `eba_guidance.py` | §1.16 / §2.14 Guidance | EBA-GUIDE-001 – EBA-GUIDE-007 |

### 2.2 Rules That Appear in Only One Format Set

Some `EBA-*` rules only appear in the XML rule set (not in the CSV rule set):

| Rule | XML | CSV | Reason |
|------|-----|-----|--------|
| EBA-2.5 | Yes | No | XML comments — no CSV equivalent. |
| EBA-2.25 | Yes | No | XML footnotes — no CSV equivalent. |
| EBA-2.26 | Yes | No | Software generator info — XML-specific element. |
| EBA-GUIDE-001 | Yes | No | Unused namespace prefixes — XML-specific. |
| EBA-GUIDE-003 | Yes | No | Unused `@id` on facts — XML-specific. |
| EBA-GUIDE-005 | Yes | No | Namespace declaration position — XML-specific. |
| EBA-GUIDE-006 | Yes | No | Multiple prefixes per namespace — XML-specific. |

These rules have `xml: true, csv: false` in the registry and live in
`eba_additional.py` or `eba_guidance.py` alongside their shared counterparts.
Their implementations only need the XML variant.

---

## 3. Core Components

### 3.1 `_models.py` — Data Classes

Follows existing xbridge conventions: plain Python classes with `__init__`,
property getters, and `from_dict()` / `to_dict()` methods.

#### `Severity`

```python
from enum import Enum

class Severity(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
```

#### `RuleDefinition`

Loaded from a single registry.json entry. Provides access to all registry
fields and resolves format-specific overrides.

```python
class RuleDefinition:
    def __init__(
        self,
        code: str,
        message: str,
        severity: Severity,
        xml: bool,
        csv: bool,
        eba: bool,
        post_conversion: bool,
        eba_ref: str | None,
        csv_severity: Severity | None = None,
        csv_message: str | None = None,
    ) -> None: ...

    def effective_severity(self, rule_set: str) -> Severity:
        """Return csv_severity when rule_set is 'csv' and override exists,
        otherwise return the base severity."""
        ...

    def effective_message(self, rule_set: str) -> str:
        """Return csv_message when rule_set is 'csv' and override exists,
        otherwise return the base message."""
        ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RuleDefinition": ...

    def to_dict(self) -> dict[str, Any]: ...
```

#### `ValidationResult`

Represents a single finding emitted by a rule implementation.

```python
class ValidationResult:
    def __init__(
        self,
        rule_id: str,
        severity: Severity,
        rule_set: str,
        message: str,
        location: str,
        context: dict[str, Any] | None = None,
    ) -> None: ...

    def __repr__(self) -> str: ...

    def to_dict(self) -> dict[str, Any]: ...
```

The fields match the specification §1.5:

| Field | Type | Source |
|-------|------|--------|
| `rule_id` | `str` | `RuleDefinition.code` |
| `severity` | `Severity` | `RuleDefinition.effective_severity(rule_set)` |
| `rule_set` | `str` | `"xml"` or `"csv"` — detected from file extension |
| `message` | `str` | Template from `RuleDefinition.effective_message(rule_set)` with placeholders filled from `context` |
| `location` | `str` | XPath expression (XML) or `file:row:col` locator (CSV) |
| `context` | `dict` | Optional key-value bag: offending values, expected values, etc. |

### 3.2 `_registry.py` — Rule Registration

Links registry entries to implementation functions via a decorator.

#### `@rule_impl` Decorator

```python
def rule_impl(code: str, format: str | None = None) -> Callable:
    """Register a function as the implementation for a rule.

    Args:
        code: The rule code (e.g. "XML-001", "EBA-ENTITY-001").
        format: Optional format qualifier — "xml" or "csv".
                Required for shared rules that need different
                implementations per format.
                Omit for format-specific rules (XML-*, CSV-*).
    """
```

Usage patterns:

```python
# Format-specific rule — no format qualifier needed
@rule_impl("XML-001")
def check_wellformedness(ctx: ValidationContext) -> None:
    ...

# Shared rule — two implementations, one per format
@rule_impl("EBA-ENTITY-001", format="xml")
def check_entity_xml(ctx: ValidationContext) -> None:
    ...

@rule_impl("EBA-ENTITY-001", format="csv")
def check_entity_csv(ctx: ValidationContext) -> None:
    ...
```

#### `get_rule_impl` Lookup

```python
def get_rule_impl(code: str, format: str) -> Callable | None:
    """Look up the implementation function for a rule.

    Resolution order:
      1. Format-specific: (code, format) — e.g. ("EBA-ENTITY-001", "xml")
      2. Generic: (code, None) — e.g. ("XML-001", None)

    Returns None if no implementation is registered.
    """
```

#### `load_registry`

```python
def load_registry() -> list[RuleDefinition]:
    """Load and parse registry.json into a list of RuleDefinition objects."""
```

The registry is loaded once per `validate()` call (not cached at module level)
so that tests can easily substitute modified registries.

### 3.3 `_engine.py` — Orchestration

The engine implements the main validation loop described in specification §2.1.

#### Execution Flow

```
validate(file, eba, post_conversion)
  │
  ├─ 1. Detect format from file extension
  │     .xbrl → rule_set = "xml"
  │     .zip  → rule_set = "csv"
  │
  ├─ 2. Load registry → list[RuleDefinition]
  │
  ├─ 3. Filter rules (see §4 below)
  │
  ├─ 4. Parse input
  │     XML → lxml etree parse (raw bytes preserved for well-formedness check)
  │     CSV → zipfile extraction, JSON/CSV parsing
  │     Reuse XmlInstance / CsvInstance from xbridge.instance (read-only)
  │
  ├─ 5. Load taxonomy module
  │     Resolve entry point → load index.json → Module.from_serialized()
  │     Reuse existing xbridge.modules infrastructure
  │
  ├─ 6. Build ValidationContext
  │
  ├─ 7. For each selected rule:
  │     ├─ Look up implementation via get_rule_impl(code, rule_set)
  │     ├─ If no implementation found → silently skip (incremental development)
  │     ├─ Execute implementation with ValidationContext
  │     └─ Collect findings
  │
  └─ 8. Return list[ValidationResult]
```

Step 4 is structured so that early rules (e.g. XML-001 well-formedness) can
run before full parsing. If a fatal rule fails (e.g. not valid XML), subsequent
rules that depend on a parsed tree are skipped gracefully. The engine handles
this by catching parse exceptions and short-circuiting.

### 3.4 `_context.py` — ValidationContext

Carries all data a rule implementation needs and provides methods to report
findings.

```python
class ValidationContext:
    def __init__(
        self,
        rule_set: str,
        rule_definition: RuleDefinition,
        file_path: Path,
        raw_bytes: bytes,
        xml_instance: XmlInstance | None,
        csv_instance: CsvInstance | None,
        module: Module | None,
    ) -> None: ...

    def add_finding(
        self,
        location: str,
        context: dict[str, Any] | None = None,
        rule_code: str | None = None,
    ) -> None:
        """Report a validation finding.

        The message template from the rule definition is rendered with
        placeholders filled from the context dict.

        Args:
            location: XPath or file:row:col locator.
            context: Optional key-value bag for template placeholders
                     and diagnostic data.
            rule_code: Override code (for rules that emit findings
                       for sub-rules). Defaults to the current
                       rule_definition.code.
        """
```

The `add_finding` method resolves the message template: given a rule with
message `"Monetary facts: decimals MUST be >= {min_decimals}."` and a context
`{"min_decimals": -4}`, the rendered message becomes
`"Monetary facts: decimals MUST be >= -4."`.

---

## 4. Rule Selection Logic

Implements the decision diagram from specification §2.1. Applied during step 3
of the engine flow.

```
For each rule in registry:
  if rule_set == "xml" and not rule.xml     → SKIP
  if rule_set == "csv" and not rule.csv     → SKIP
  if rule.eba and not eba_param             → SKIP
  if rule_set == "csv" and post_conversion
       and not rule.post_conversion         → SKIP
  Otherwise                                 → RUN
```

In pseudocode:

```python
def select_rules(
    registry: list[RuleDefinition],
    rule_set: str,
    eba: bool,
    post_conversion: bool,
) -> list[RuleDefinition]:
    selected = []
    for rule in registry:
        # Format filter
        if rule_set == "xml" and not rule.xml:
            continue
        if rule_set == "csv" and not rule.csv:
            continue
        # EBA gate
        if rule.eba and not eba:
            continue
        # Post-conversion filter (CSV only)
        if rule_set == "csv" and post_conversion and not rule.post_conversion:
            continue
        selected.append(rule)
    return selected
```

### 4.1 Post-conversion Behaviour

When `post_conversion=True` and the input is CSV, only rules with
`post_conversion: true` survive. Per the enumeration, the surviving rules are:

| Rule | Section |
|------|---------|
| EBA-UNIT-001 | §2.11 Non-monetary Numeric Values |
| EBA-UNIT-002 | §2.11 Non-monetary Numeric Values |
| EBA-REP-001 | §2.12 Decimal Representation |
| EBA-2.16.1 | §2.13 Additional Checks |
| EBA-2.24 | §2.13 Additional Checks |
| EBA-GUIDE-002 | §2.14 Guidance |
| EBA-GUIDE-004 | §2.14 Guidance |
| EBA-GUIDE-007 | §2.14 Guidance |

All other CSV rules (sections §2.1–§2.10) have `post_conversion: false` and
are skipped. The `post_conversion` parameter has no effect on XML validation.

---

## 5. Public API

Exposed from `src/xbridge/validation/__init__.py`:

```python
from xbridge.validation import validate, ValidationResult, Severity

results: list[ValidationResult] = validate(
    file="path/to/instance.xbrl",
    eba=False,
    post_conversion=False,
)
```

### 5.1 `validate()` Signature

```python
def validate(
    file: str | Path,
    eba: bool = False,
    post_conversion: bool = False,
) -> list[ValidationResult]:
    """Validate an XBRL instance file.

    Args:
        file: Path to an .xbrl (XML) or .zip (CSV) file.
        eba: When True, additionally runs EBA-specific rules.
        post_conversion: (CSV only) When True, skips structural and
            format checks guaranteed by xbridge's converter, keeping
            only EBA semantic checks. Has no effect for .xbrl files.

    Returns:
        A list of ValidationResult findings, ordered by rule execution
        sequence. An empty list means no issues were found.
    """
```

This matches the specification §3 API sketch exactly.

### 5.2 Integration with Existing Convert Flow

```python
# 1. Validate XML input
xml_results = validate("input.xbrl", eba=True)
if any(r.severity == Severity.ERROR for r in xml_results):
    ...  # handle errors

# 2. Convert
convert_instance("input.xbrl", output_dir="out/")

# 3. Validate CSV output (post-conversion mode)
csv_results = validate("out/output.zip", eba=True, post_conversion=True)
```

---

## 6. Integration with Existing Code

### 6.1 Reused Components (Read-Only)

The validation module reuses the following existing classes without modifying
them:

| Class | Module | Usage |
|-------|--------|-------|
| `Instance.from_path()` | `xbridge.instance` | Format detection and parsing |
| `XmlInstance` | `xbridge.instance` | Parsed XML tree, contexts, facts, filing indicators |
| `CsvInstance` | `xbridge.instance` | Parsed CSV package, parameters, data tables |
| `Module` | `xbridge.modules` | Taxonomy metadata (entry points, tables, variables, dimensions) |
| `Module.from_serialized()` | `xbridge.modules` | Load pre-processed JSON modules |

### 6.2 No Modifications to Existing Files

The validation module is entirely additive. No existing source file is
modified. The new `src/xbridge/validation/` package is self-contained and
depends on `xbridge.instance` and `xbridge.modules` through their public
interfaces.

### 6.3 Exception Bridging

Existing exceptions (e.g. `SchemaRefValueError`, `FilingIndicatorValueError`)
raised during instance parsing may be caught by rule implementations and
converted into `ValidationResult` findings. For example, the implementation of
`XML-012` (invalid schemaRef) could catch `SchemaRefValueError` and emit a
finding with the appropriate code, severity, and message.

---

## 7. Rule Coverage Summary

Total unique rules in the enumeration: **98**

| Category | Count | Rules |
|----------|-------|-------|
| XML-only format rules | 34 | XML-001 – XML-072 |
| XML-only EBA rules | 7 | EBA-2.5, EBA-2.25, EBA-2.26, EBA-GUIDE-001, -003, -005, -006 |
| CSV-only format rules | 40 | CSV-001 – CSV-062 |
| Shared EBA rules | 17 | EBA-ENTITY-001/002, EBA-DEC-001–004, EBA-CUR-001–003, EBA-UNIT-001/002, EBA-REP-001, EBA-2.16.1, EBA-2.24, EBA-GUIDE-002, -004, -007 |
| **Total unique rules** | **98** | |

Effective rules per format:

| Format | Count | Composition |
|--------|-------|-------------|
| XML | 58 | 34 XML-only + 7 XML-only EBA + 17 shared EBA |
| CSV | 57 | 40 CSV-only + 17 shared EBA |

All 98 rules have a corresponding registry entry and are assigned to an
implementation file. Rules without implementations are silently skipped by the
engine, supporting incremental development.

---

## 8. Registry JSON Schema Validation

The registry JSON structure can be validated with a JSON Schema (e.g. during
CI) to catch malformed entries early. A minimal schema for a registry entry:

```json
{
  "type": "object",
  "required": ["code", "message", "severity", "xml", "csv", "eba", "post_conversion", "eba_ref"],
  "properties": {
    "code":             { "type": "string", "pattern": "^(XML|CSV|EBA)-" },
    "message":          { "type": "string", "minLength": 1 },
    "severity":         { "enum": ["ERROR", "WARNING", "INFO"] },
    "xml":              { "type": "boolean" },
    "csv":              { "type": "boolean" },
    "eba":              { "type": "boolean" },
    "post_conversion":  { "type": "boolean" },
    "eba_ref":          { "type": ["string", "null"] },
    "csv_severity":     { "enum": ["ERROR", "WARNING", "INFO"] },
    "csv_message":      { "type": "string" }
  },
  "additionalProperties": false
}
```

Invariants enforced by schema or CI checks:

- Every `code` is unique (no duplicate entries for the same code).
- At least one of `xml` or `csv` is `true` (a rule must apply to at least one
  format).
- `csv_severity` and `csv_message` are only present when `csv` is `true`.
- `post_conversion` is only `true` when `csv` is `true`.

---

## 9. Design Decisions

### 9.1 Why a JSON Registry?

**Alternative considered:** Define rules as Python constants alongside their
implementations.

**Decision:** A separate JSON file because:
- Non-developers (analysts, compliance officers) can review and adjust rule
  attributes without reading Python.
- Severity changes, message edits, and EBA flag toggles are configuration
  changes, not code changes.
- The registry can be validated with JSON Schema in CI.
- The full rule inventory is visible in one place.

### 9.2 Why Not Dataclasses?

The existing xbridge codebase uses plain classes with `__init__` and
`from_dict()` / `to_dict()` methods. The validation module follows this
convention for consistency.

### 9.3 Why Silently Skip Missing Implementations?

Rules can be defined in the registry before their implementations are written.
This supports incremental development: rules are added to the registry first
(establishing the full catalogue), and implementations are filled in one
section at a time. A missing implementation is not an error — it simply means
the rule is not yet enforced.

### 9.4 Why Per-Call Registry Loading?

The registry is loaded from disk on each `validate()` call rather than cached
at module import time. This makes testing straightforward (each test can
provide a modified registry) and avoids stale-cache issues. The registry is
small (~100 entries) and parsing overhead is negligible.

---

## 10. Scope and Next Steps

**This document covers:** The architecture of the validation module — registry
schema, module structure, core components, rule selection logic, and public
API.

**Not covered here:** Individual rule implementations. These will be developed
incrementally, one enumeration section at a time, following the file mapping
in §2.1. Each implementation session will:

1. Write the rule functions in the corresponding `rules/*.py` file.
2. Add the `@rule_impl` decorator registrations.
3. Add corresponding entries to `registry.json`.
4. Write tests for the new rules.

---

## Appendix A. Reference Documents

| Document | Location | Version |
|----------|----------|---------|
| Validation Specification | `specification/validation_specification.md` | 0.3 Draft |
| Validation Rules Enumeration | `specification/validations_enumeration.md` | 0.2 Draft |
| XBRL 2.1 Specification | `specification/xbrl/Extensible Business Reporting Language (XBRL) 2.1.mhtml` | REC 2003-12-31 |
| xBRL-CSV 1.0 | `specification/xbrl/xBRL-CSV_ CSV representation of XBRL data 1.0.mhtml` | REC 2021-10-13 |
| EBA Filing Rules | `specification/eba/eba_filing_rules_v5.7_2025_11_24.pdf` | v5.7, November 2025 |
