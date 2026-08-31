XBridge Documentation
#####################

.. image:: https://img.shields.io/pypi/v/eba-xbridge.svg
   :target: https://pypi.org/project/eba-xbridge/
   :alt: PyPI version

.. image:: https://img.shields.io/pypi/pyversions/eba-xbridge.svg
   :target: https://pypi.org/project/eba-xbridge/
   :alt: Python versions

.. image:: https://img.shields.io/github/license/Meaningful-Data/xbridge.svg
   :target: https://github.com/Meaningful-Data/xbridge/blob/main/LICENSE
   :alt: License

Overview
========

**XBridge** is a Python library for converting XBRL-XML files into XBRL-CSV files using the EBA (European Banking Authority) taxonomy. It provides a simple, reliable way to transform regulatory reporting data from XML format to CSV format.

The library currently supports **EBA Taxonomy version 4.2 / 4.2.1 / 4.3 / 4.4 (phase 1, draft)** and includes support for DORA (Digital Operational Resilience Act) CSV conversion.

Key Features
============

* **XBRL-XML to XBRL-CSV Conversion**: Seamlessly convert XBRL-XML instance files to XBRL-CSV format
* **OneGate Envelope Support**: Transparently unwrap XBRL instances delivered inside a OneGate ``XbrlDeclarationReport`` message envelope
* **XBRL-XML and XBRL-CSV Validation**: Validate instance files against structural and EBA regulatory rules, with format-aware rule selection and post-conversion mode
* **Command-Line Interface**: Quick conversions and validation without writing code using the ``xbridge`` CLI
* **Python API**: Programmatic conversion and validation for integration with other tools and workflows
* **EBA Taxonomy 4.2/4.2.1/4.3/4.4 Support**: Built for the latest EBA taxonomy specification
* **DORA CSV Conversion**: Support for Digital Operational Resilience Act reporting
* **Configurable Validation**: Flexible filing indicator validation with strict or warning modes
* **Decimal Handling**: Intelligent decimal precision handling with configurable options
* **Type Safety**: Fully typed codebase with MyPy strict mode compliance
* **Python 3.9+**: Supports Python 3.9 through 3.13

Quick Start
===========

Installation
------------

Install XBridge from PyPI:

.. code-block:: bash

    pip install eba-xbridge

Command-Line Usage
------------------

The fastest way to convert files is using the CLI:

.. code-block:: bash

    # Basic conversion
    xbridge instance.xbrl

    # Specify output directory
    xbridge instance.xbrl --output-path ./output

    # Continue with warnings instead of errors
    xbridge instance.xbrl --no-strict-validation

Validation
----------

Validate XBRL-XML or XBRL-CSV files without converting:

.. code-block:: bash

    # Structural checks
    xbridge validate instance.xbrl

    # Include EBA regulatory rules
    xbridge validate instance.xbrl --eba

    # Validate a CSV package
    xbridge validate report.zip --eba

Python API Usage
----------------

For programmatic use, import and use the Python API:

.. code-block:: python

    from xbridge.api import convert_instance

    # Basic conversion
    convert_instance(
        instance_path="path/to/instance.xbrl",
        output_path="path/to/output"
    )

    # Conversion with pre- and post-conversion validation
    convert_instance(
        instance_path="path/to/instance.xbrl",
        output_path="path/to/output",
        validate=True,
        eba=True,
    )

.. code-block:: python

    from xbridge.validation import validate

    # Standalone validation
    results = validate("path/to/instance.xbrl", eba=True)
    has_errors = any(section["errors"] for section in results.values())

What's New
==========

**Version 2.2.0rc1**

* **Correct ``baseCurrency`` in multi-currency reports**: the base currency is no longer taken from the first ``iso4217`` unit declared in the instance — a choice that depended on the order of the ``xbrli:unit`` declarations — but from the facts whose datapoint takes its unit from the parameter (``"unit": "$baseCurrency"`` in the taxonomy JSON). Facts of datapoints that report their unit explicitly (``"unit": "$unit"``) hold the breakdown by significant currency and no longer influence the parameter (#123)
* **New exception ``MultipleBaseCurrenciesError``**: an instance whose base-currency facts are reported in more than one currency is erroneous and is no longer converted with an arbitrary currency; the error names the conflicting currencies, their fact counts and an example datapoint (#123)
* **New validation rule EBA-CUR-004** (ERROR, XML): reports the same conflict *before* conversion, so ``validate(..., eba=True)`` and ``convert_instance(..., validate=True, eba=True)`` surface it as a validation error instead of a conversion failure (#123)

**Version 2.1.0**

* **EBA Taxonomy 4.4 Support (phase 1, draft)**: Ten new modules from the 4.4 phase 1 draft — ``ifrs18`` (FINREP under IFRS 18), ``codis``, ``esgdis``, ``findis``, ``gsiidis`` and ``p3dh`` (Pillar 3 disclosures), ``resol1`` / ``resol2`` (resolution planning), ``mrel_decisions`` (MREL) and ``aml_eligibility`` (AMLA)
* **EBA Taxonomy 4.3 Support**: New modules ``aml_ra`` (AMLA risk assessment) and the Third Country Branches framework (``tcb_core``, ``tcb_hu``, ``tcb_liquidity``)
* **Module Applicability Dates**: Every bundled module now records the reference-date range it applies to, exposed on ``Module`` as ``from_date`` / ``to_date``, with the new validation rule **EBA-DATE-001** reporting instances whose reference date falls outside that range (#121)
* **Fact Reconciliation Census**: ``Converter.reconciliation`` accounts for every source fact after a conversion, so silent fact losses are surfaced through ``FactReconciliationWarning`` / ``FactReconciliationError`` (#120)
* **OneGate Envelope Support**: XBRL instances delivered inside a OneGate ``XbrlDeclarationReport`` message envelope are now accepted and transparently unwrapped, so conversion and validation work exactly as for a bare instance. Accepted input formats are defined by an explicit whitelist; unrecognised roots raise ``UnsupportedInstanceFormatError`` (#117)
* **Fixes**: Facts declaring the metric namespace per element are no longer dropped (#118), and ``schemaRef`` detection no longer depends on the literal ``link`` prefix (#119)

**Version 2.0.0rc8**

* **Validation Fix**: Fixed ``Scenario.parse()`` crash on dimension attributes without namespace prefix, which silently prevented taxonomy-based validation rules (XML-070/071/072) from running
* **Validation Engine**: Added fallback ``module_ref`` extraction so taxonomy rules can still execute when ``XmlInstance`` parsing fails

**Version 2.0.0rc3**

* **Validate-Convert-Validate Pipeline**: ``--validate`` / ``--eba`` CLI flags and ``validate=`` / ``eba=`` API parameters for pre- and post-conversion validation
* **EBA Taxonomy 4.2.1**: Added FINREP 4.2.1 (``finrep9dp``) module
* Fixed EBA-CUR-002 incorrectly flagging non-monetary facts
* Fixed incorrect ``R_02.00.a`` filing indicator in the ``rem_bm`` (GL 2022-06) module

**Version 2.0.0rc2**

* **CSV Structural Rules**: CSV-001..CSV-005, CSV-010..CSV-016, CSV-020..CSV-026, CSV-030..CSV-035, CSV-040..CSV-049, CSV-050..CSV-052, CSV-060..CSV-062
* **CSV EBA Rules**: CSV-side implementations for EBA-ENTITY-001/002, EBA-DEC-001..004, EBA-UNIT-001/002, EBA-CUR-003, EBA-2.16.1, EBA-2.24, EBA-GUIDE-002/004/007, EBA-NAME-071
* **Validation Performance**: Shared cache across rules eliminates redundant ZIP I/O (~60-65% faster for CSV validation)
* Fixed ``iso4217:``-prefixed ``baseCurrency`` parameter handling in CSV validation rules

**Version 2.0.0rc1**

* **Standalone Validation API**: New ``xbridge.validation`` module with ``validate()`` function
* **Validation CLI Command**: New ``xbridge validate`` subcommand
* **XML Structural Rules**: XML-001..XML-072
* **EBA Rules**: EBA-ENTITY, EBA-CUR, EBA-UNIT, EBA-DEC, EBA-GUIDE, EBA-NAME, and additional EBA rules

See the `CHANGELOG <https://github.com/Meaningful-Data/xbridge/blob/main/CHANGELOG.md>`_ for complete version history.

Documentation Contents
======================

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   quickstart.rst

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   technical_notes.rst
   validation_rules.rst

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api.rst
   validation.rst
   cli.rst
   converter.rst
   taxonomy_loader.rst
   modules.rst
   xml_instance.rst

.. toctree::
   :maxdepth: 1
   :caption: Additional Resources

   GitHub Repository <https://github.com/Meaningful-Data/xbridge>
   Issue Tracker <https://github.com/Meaningful-Data/xbridge/issues>
   Changelog <https://github.com/Meaningful-Data/xbridge/blob/main/CHANGELOG.md>
   Contributing <https://github.com/Meaningful-Data/xbridge/blob/main/CONTRIBUTING.md>
   Security Policy <https://github.com/Meaningful-Data/xbridge/blob/main/SECURITY.md>

How XBridge Works
=================

XBridge performs the conversion in several steps:

1. **Load the XBRL-XML instance**: Parse and extract facts, contexts, scenarios, and filing indicators
2. **Load the EBA taxonomy**: Access pre-processed taxonomy modules containing tables and variables
3. **Match and validate**: Join instance facts with taxonomy definitions
4. **Generate CSV files**: Create XBRL-CSV files including data tables, filing indicators, and parameters
5. **Package output**: Bundle all CSV files into a ZIP archive

Output Structure
----------------

The output ZIP file contains:

* **META-INF/**: JSON report package metadata
* **reports/**: CSV files for each reported table
* **filing-indicators.csv**: Table reporting indicators
* **parameters.csv**: Report-level parameters (entity, period, currency, decimals)

Support & Contributing
======================

* **Documentation**: https://docs.xbridge.meaningfuldata.eu
* **Issue Tracker**: https://github.com/Meaningful-Data/xbridge/issues
* **Email**: info@meaningfuldata.eu
* **Contributing**: See `CONTRIBUTING.md <https://github.com/Meaningful-Data/xbridge/blob/main/CONTRIBUTING.md>`_

License
=======

XBridge is licensed under the Apache License 2.0. See the `LICENSE <https://github.com/Meaningful-Data/xbridge/blob/main/LICENSE>`_ file for details.

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
