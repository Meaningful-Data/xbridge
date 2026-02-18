"""EBA-NAME-001..EBA-NAME-070: Submission package naming rules.

These rules validate the file naming convention required by the
EBA Filing Rules v5.7.  They apply to both bare .xbrl files and
ZIP archives.  EBA-NAME-070 is ZIP-only.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple
from zipfile import BadZipFile, ZipFile

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Expected number of underscore-separated components in the file name.
_COMPONENT_COUNT = 6

# Reference date format: YYYY-MM-DD
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Creation timestamp: YYYYMMDDhhmmssfff (17 digits)
_TIMESTAMP_RE = re.compile(r"^\d{17}$")

# Framework code + 6-digit version (e.g. COREP020001)
_FRAMEWORK_VERSION_RE = re.compile(r"^[A-Z]+\d{6}$")

# LEI: exactly 20 alphanumeric characters.
_LEI_RE = re.compile(r"^[A-Z0-9]{20}$")

# Known report-subject suffixes.
_LEI_SUFFIXES = frozenset({".IND", ".CON", ".CRDLIQSUBGRP"})
_COUNTRY_AGG_SUFFIXES = frozenset({".MEMSTAAGGALL", ".MEMSTAAGGCRDCREINS", ".MEMSTAAGGINVFIR"})

# ISO 3166-1 alpha-2 country codes (comprehensive).
_ISO_3166_ALPHA2 = frozenset(
    {
        "AD",
        "AE",
        "AF",
        "AG",
        "AI",
        "AL",
        "AM",
        "AO",
        "AQ",
        "AR",
        "AS",
        "AT",
        "AU",
        "AW",
        "AX",
        "AZ",
        "BA",
        "BB",
        "BD",
        "BE",
        "BF",
        "BG",
        "BH",
        "BI",
        "BJ",
        "BL",
        "BM",
        "BN",
        "BO",
        "BQ",
        "BR",
        "BS",
        "BT",
        "BV",
        "BW",
        "BY",
        "BZ",
        "CA",
        "CC",
        "CD",
        "CF",
        "CG",
        "CH",
        "CI",
        "CK",
        "CL",
        "CM",
        "CN",
        "CO",
        "CR",
        "CU",
        "CV",
        "CW",
        "CX",
        "CY",
        "CZ",
        "DE",
        "DJ",
        "DK",
        "DM",
        "DO",
        "DZ",
        "EC",
        "EE",
        "EG",
        "EH",
        "ER",
        "ES",
        "ET",
        "FI",
        "FJ",
        "FK",
        "FM",
        "FO",
        "FR",
        "GA",
        "GB",
        "GD",
        "GE",
        "GF",
        "GG",
        "GH",
        "GI",
        "GL",
        "GM",
        "GN",
        "GP",
        "GQ",
        "GR",
        "GS",
        "GT",
        "GU",
        "GW",
        "GY",
        "HK",
        "HM",
        "HN",
        "HR",
        "HT",
        "HU",
        "ID",
        "IE",
        "IL",
        "IM",
        "IN",
        "IO",
        "IQ",
        "IR",
        "IS",
        "IT",
        "JE",
        "JM",
        "JO",
        "JP",
        "KE",
        "KG",
        "KH",
        "KI",
        "KM",
        "KN",
        "KP",
        "KR",
        "KW",
        "KY",
        "KZ",
        "LA",
        "LB",
        "LC",
        "LI",
        "LK",
        "LR",
        "LS",
        "LT",
        "LU",
        "LV",
        "LY",
        "MA",
        "MC",
        "MD",
        "ME",
        "MF",
        "MG",
        "MH",
        "MK",
        "ML",
        "MM",
        "MN",
        "MO",
        "MP",
        "MQ",
        "MR",
        "MS",
        "MT",
        "MU",
        "MV",
        "MW",
        "MX",
        "MY",
        "MZ",
        "NA",
        "NC",
        "NE",
        "NF",
        "NG",
        "NI",
        "NL",
        "NO",
        "NP",
        "NR",
        "NU",
        "NZ",
        "OM",
        "PA",
        "PE",
        "PF",
        "PG",
        "PH",
        "PK",
        "PL",
        "PM",
        "PN",
        "PR",
        "PS",
        "PT",
        "PW",
        "PY",
        "QA",
        "RE",
        "RO",
        "RS",
        "RU",
        "RW",
        "SA",
        "SB",
        "SC",
        "SD",
        "SE",
        "SG",
        "SH",
        "SI",
        "SJ",
        "SK",
        "SL",
        "SM",
        "SN",
        "SO",
        "SR",
        "SS",
        "ST",
        "SV",
        "SX",
        "SY",
        "SZ",
        "TC",
        "TD",
        "TF",
        "TG",
        "TH",
        "TJ",
        "TK",
        "TL",
        "TM",
        "TN",
        "TO",
        "TR",
        "TT",
        "TV",
        "TW",
        "TZ",
        "UA",
        "UG",
        "UM",
        "US",
        "UY",
        "UZ",
        "VA",
        "VC",
        "VE",
        "VG",
        "VI",
        "VN",
        "VU",
        "WF",
        "WS",
        "YE",
        "YT",
        "ZA",
        "ZM",
        "ZW",
        # Additional codes used in EBA context.
        "EU",
        "XK",
    }
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _split_stem(ctx: ValidationContext) -> Optional[Tuple[str, List[str]]]:
    """Split the file stem into underscore-separated components.

    Returns ``(stem, parts)`` or *None* if the stem is empty.
    """
    stem = ctx.file_path.stem
    if not stem:
        return None
    return stem, stem.split("_")


def _is_aggregate_subject(subject: str) -> bool:
    """Return True if the report subject looks like an aggregate or MICA pattern."""
    for suffix in _COUNTRY_AGG_SUFFIXES:
        if subject.endswith(suffix):
            return True
    if subject.endswith(".AUTALL"):
        return True
    # MICA: IssuerID-TokenID.IND (contains hyphen)
    return bool(subject.endswith(".IND") and "-" in subject)


def _has_con_ind_module(module_component: str) -> bool:
    """Heuristic: check if the uppercase module name came from a name with _con/_ind."""
    return module_component.endswith("CON") or module_component.endswith("IND")


# ---------------------------------------------------------------------------
# EBA-NAME-001: Overall file name structure
# ---------------------------------------------------------------------------


@rule_impl("EBA-NAME-001")
def check_file_name_structure(ctx: ValidationContext) -> None:
    """Validate the file name has exactly 6 underscore-separated components."""
    parsed = _split_stem(ctx)
    if parsed is None:
        return

    stem, parts = parsed
    if len(parts) != _COMPONENT_COUNT:
        ctx.add_finding(
            location=f"filename:{ctx.file_path.name}",
            context={
                "detail": (
                    f"expected {_COMPONENT_COUNT} underscore-separated components, "
                    f"found {len(parts)}: '{stem}'"
                )
            },
        )


# ---------------------------------------------------------------------------
# EBA-NAME-010: ReportSubject — LEI for con/ind modules (or old dates)
# ---------------------------------------------------------------------------


@rule_impl("EBA-NAME-010")
def check_report_subject_lei(ctx: ValidationContext) -> None:
    """Validate ReportSubject is a LEI or LEI.CRDLIQSUBGRP for con/ind modules."""
    parsed = _split_stem(ctx)
    if parsed is None:
        return
    stem, parts = parsed
    if len(parts) != _COMPONENT_COUNT:
        return  # EBA-NAME-001 covers this

    subject, module, ref_date = parts[0], parts[3], parts[4]

    # Condition: module has _con/_ind OR reference date < 2022-12-31.
    if not _has_con_ind_module(module) and not ref_date < "2022-12-31":
        return  # Rule 011 applies instead

    if _is_aggregate_subject(subject):
        return  # Rules 012–014 handle aggregates

    # Valid: plain LEI (20 chars) or LEI.CRDLIQSUBGRP.
    if _LEI_RE.match(subject):
        return
    if subject.endswith(".CRDLIQSUBGRP"):
        lei_part = subject[: -len(".CRDLIQSUBGRP")]
        if _LEI_RE.match(lei_part):
            return

    ctx.add_finding(
        location=f"filename:{ctx.file_path.name}",
        context={
            "detail": (
                f"ReportSubject '{subject}' is not a valid LEI "
                f"(20 alphanumeric chars) or LEI.CRDLIQSUBGRP"
            )
        },
    )


# ---------------------------------------------------------------------------
# EBA-NAME-011: ReportSubject — LEI with suffix for newer modules
# ---------------------------------------------------------------------------


@rule_impl("EBA-NAME-011")
def check_report_subject_lei_suffix(ctx: ValidationContext) -> None:
    """Validate ReportSubject has .IND/.CON/.CRDLIQSUBGRP suffix."""
    parsed = _split_stem(ctx)
    if parsed is None:
        return
    stem, parts = parsed
    if len(parts) != _COMPONENT_COUNT:
        return

    subject, module, ref_date = parts[0], parts[3], parts[4]

    # Condition: module does NOT have _con/_ind AND date >= 2022-12-31.
    if _has_con_ind_module(module) or ref_date < "2022-12-31":
        return  # Rule 010 applies instead

    if _is_aggregate_subject(subject):
        return  # Rules 012–014 handle aggregates

    for suffix in _LEI_SUFFIXES:
        if subject.endswith(suffix):
            lei_part = subject[: -len(suffix)]
            if _LEI_RE.match(lei_part):
                return  # Valid
            ctx.add_finding(
                location=f"filename:{ctx.file_path.name}",
                context={
                    "detail": (
                        f"ReportSubject '{subject}': LEI part '{lei_part}' "
                        f"is not a valid 20-char alphanumeric identifier"
                    )
                },
            )
            return

    ctx.add_finding(
        location=f"filename:{ctx.file_path.name}",
        context={
            "detail": (
                f"ReportSubject '{subject}' must end with "
                f".IND, .CON, or .CRDLIQSUBGRP for module '{module}'"
            )
        },
    )


# ---------------------------------------------------------------------------
# EBA-NAME-012: ReportSubject — country-level aggregates
# ---------------------------------------------------------------------------


@rule_impl("EBA-NAME-012")
def check_report_subject_country_aggregate(ctx: ValidationContext) -> None:
    """Validate country aggregate ReportSubject: CC000 + aggregation suffix."""
    parsed = _split_stem(ctx)
    if parsed is None:
        return
    stem, parts = parsed
    if len(parts) != _COMPONENT_COUNT:
        return

    subject = parts[0]

    matched_suffix = None
    for suffix in _COUNTRY_AGG_SUFFIXES:
        if subject.endswith(suffix):
            matched_suffix = suffix
            break
    if matched_suffix is None:
        return  # Not a country aggregate

    prefix = subject[: -len(matched_suffix)]
    if len(prefix) != 5 or not prefix[:2].isalpha() or prefix[2:] != "000":
        ctx.add_finding(
            location=f"filename:{ctx.file_path.name}",
            context={
                "detail": (
                    f"Country aggregate ReportSubject '{subject}': "
                    f"prefix '{prefix}' must be 2-letter country code + '000'"
                )
            },
        )
    elif prefix[:2].upper() not in _ISO_3166_ALPHA2:
        ctx.add_finding(
            location=f"filename:{ctx.file_path.name}",
            context={
                "detail": (
                    f"Country aggregate ReportSubject '{subject}': "
                    f"'{prefix[:2]}' is not a valid ISO 3166-1 alpha-2 code"
                )
            },
        )


# ---------------------------------------------------------------------------
# EBA-NAME-013: ReportSubject — authority-level aggregates
# ---------------------------------------------------------------------------


@rule_impl("EBA-NAME-013")
def check_report_subject_authority_aggregate(ctx: ValidationContext) -> None:
    """Validate authority aggregate ReportSubject: code + .AUTALL."""
    parsed = _split_stem(ctx)
    if parsed is None:
        return
    stem, parts = parsed
    if len(parts) != _COMPONENT_COUNT:
        return

    subject = parts[0]
    if not subject.endswith(".AUTALL"):
        return

    authority_code = subject[: -len(".AUTALL")]
    if not authority_code or not authority_code.replace(".", "").isalnum():
        ctx.add_finding(
            location=f"filename:{ctx.file_path.name}",
            context={
                "detail": (
                    f"Authority aggregate ReportSubject '{subject}': "
                    f"authority code must be non-empty"
                )
            },
        )


# ---------------------------------------------------------------------------
# EBA-NAME-014: ReportSubject — MICA reports
# ---------------------------------------------------------------------------


@rule_impl("EBA-NAME-014")
def check_report_subject_mica(ctx: ValidationContext) -> None:
    """Validate MICA ReportSubject: IssuerID-TokenID.IND."""
    parsed = _split_stem(ctx)
    if parsed is None:
        return
    stem, parts = parsed
    if len(parts) != _COMPONENT_COUNT:
        return

    subject = parts[0]
    if not subject.endswith(".IND") or "-" not in subject:
        return  # Not a MICA pattern

    base = subject[: -len(".IND")]
    dash_pos = base.find("-")
    issuer = base[:dash_pos]
    token = base[dash_pos + 1 :]

    if not issuer or not token:
        ctx.add_finding(
            location=f"filename:{ctx.file_path.name}",
            context={
                "detail": (
                    f"MICA ReportSubject '{subject}': IssuerID and TokenID must both be non-empty"
                )
            },
        )


# ---------------------------------------------------------------------------
# EBA-NAME-020: Country component
# ---------------------------------------------------------------------------


@rule_impl("EBA-NAME-020")
def check_country_code(ctx: ValidationContext) -> None:
    """Validate the Country component is ISO 3166-1 alpha-2."""
    parsed = _split_stem(ctx)
    if parsed is None:
        return
    stem, parts = parsed
    if len(parts) != _COMPONENT_COUNT:
        return

    country = parts[1]
    if country not in _ISO_3166_ALPHA2:
        ctx.add_finding(
            location=f"filename:{ctx.file_path.name}",
            context={"detail": (f"'{country}' is not a valid ISO 3166-1 alpha-2 country code")},
        )


# ---------------------------------------------------------------------------
# EBA-NAME-030: Framework code + module version
# ---------------------------------------------------------------------------


@rule_impl("EBA-NAME-030")
def check_framework_version(ctx: ValidationContext) -> None:
    """Validate FrameworkCodeModuleVersion format: CODE + 6-digit version."""
    parsed = _split_stem(ctx)
    if parsed is None:
        return
    stem, parts = parsed
    if len(parts) != _COMPONENT_COUNT:
        return

    fwk = parts[2]
    if not _FRAMEWORK_VERSION_RE.match(fwk):
        ctx.add_finding(
            location=f"filename:{ctx.file_path.name}",
            context={
                "detail": (
                    f"'{fwk}' does not match the expected pattern: "
                    f"uppercase framework code + 6-digit version XXYYZZ"
                )
            },
        )


# ---------------------------------------------------------------------------
# EBA-NAME-040: Module component
# ---------------------------------------------------------------------------


@rule_impl("EBA-NAME-040")
def check_module_name(ctx: ValidationContext) -> None:
    """Validate Module component is uppercase alphanumeric."""
    parsed = _split_stem(ctx)
    if parsed is None:
        return
    stem, parts = parsed
    if len(parts) != _COMPONENT_COUNT:
        return

    module = parts[3]
    if not module.isupper() or not module.isalnum():
        ctx.add_finding(
            location=f"filename:{ctx.file_path.name}",
            context={
                "detail": (
                    f"Module component '{module}' must be uppercase "
                    f"alphanumeric (no underscores or special characters)"
                )
            },
        )


# ---------------------------------------------------------------------------
# EBA-NAME-050: Reference date
# ---------------------------------------------------------------------------


@rule_impl("EBA-NAME-050")
def check_reference_date(ctx: ValidationContext) -> None:
    """Validate ReferenceDate is in YYYY-MM-DD format."""
    parsed = _split_stem(ctx)
    if parsed is None:
        return
    stem, parts = parsed
    if len(parts) != _COMPONENT_COUNT:
        return

    date_str = parts[4]
    if not _DATE_RE.match(date_str):
        ctx.add_finding(
            location=f"filename:{ctx.file_path.name}",
            context={"detail": (f"ReferenceDate '{date_str}' does not match YYYY-MM-DD format")},
        )


# ---------------------------------------------------------------------------
# EBA-NAME-060: Creation timestamp
# ---------------------------------------------------------------------------


@rule_impl("EBA-NAME-060")
def check_creation_timestamp(ctx: ValidationContext) -> None:
    """Validate CreationTimestamp is in YYYYMMDDhhmmssfff format (17 digits)."""
    parsed = _split_stem(ctx)
    if parsed is None:
        return
    stem, parts = parsed
    if len(parts) != _COMPONENT_COUNT:
        return

    ts = parts[5]
    if not _TIMESTAMP_RE.match(ts):
        ctx.add_finding(
            location=f"filename:{ctx.file_path.name}",
            context={
                "detail": (
                    f"CreationTimestamp '{ts}' does not match YYYYMMDDhhmmssfff format (17 digits)"
                )
            },
        )


# ---------------------------------------------------------------------------
# EBA-NAME-070: Inner .xbrl file matches ZIP name (ZIP-only, XML-only)
# ---------------------------------------------------------------------------


@rule_impl("EBA-NAME-070")
def check_inner_xbrl_name(ctx: ValidationContext) -> None:
    """Validate that the ZIP contains exactly one .xbrl matching the ZIP name."""
    if ctx.zip_path is None:
        return  # Not a ZIP — skip

    zip_stem = ctx.zip_path.stem
    expected_xbrl = f"{zip_stem}.xbrl"

    try:
        with ZipFile(ctx.zip_path) as zf:
            entries = zf.namelist()
    except BadZipFile:
        return  # ZIP errors handled elsewhere

    xbrl_files = [e for e in entries if e.lower().endswith((".xbrl", ".xml")) and "/" not in e]

    if len(xbrl_files) != 1:
        ctx.add_finding(
            location=f"zip:{ctx.zip_path.name}",
            context={"detail": (f"expected exactly one .xbrl file, found {len(xbrl_files)}")},
        )
        return

    actual_name = xbrl_files[0]
    if actual_name != expected_xbrl:
        ctx.add_finding(
            location=f"zip:{ctx.zip_path.name}",
            context={
                "detail": (
                    f"inner file '{actual_name}' does not match expected name '{expected_xbrl}'"
                )
            },
        )
