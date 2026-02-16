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

The library currently supports **EBA Taxonomy version 4.2** and includes support for DORA (Digital Operational Resilience Act) CSV conversion.

Key Features
============

* **XBRL-XML to XBRL-CSV Conversion**: Seamlessly convert XBRL-XML instance files to XBRL-CSV format
* **Command-Line Interface**: Quick conversions without writing code using the ``xbridge`` CLI
* **Python API**: Programmatic conversion for integration with other tools and workflows
* **EBA Taxonomy 4.2 Support**: Built for the latest EBA taxonomy specification
* **DORA CSV Conversion**: Support for Digital Operational Resilience Act reporting
* **Standalone Validation API**: Validate XBRL-XML and XBRL-CSV files against structural and EBA rules
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

    # Advanced usage with validation options
    convert_instance(
        instance_path="path/to/instance.xbrl",
        output_path="path/to/output",
        headers_as_datapoints=True,
        validate_filing_indicators=True,
        strict_validation=False
    )

What's New
==========

**Version 1.5.2rc2**

* Fixed ``baseCurrency`` parameter handling: now only included when present in the source instance
* Fixed filing indicators parsing to handle multiple ``find:fIndicators`` blocks in a single XBRL instance

**Version 1.5.0**

* Support for "0" and "1" values in filing indicators
* Structured warnings for easier integration
* Custom exceptions with detailed error information
* Configurable filing indicator strictness
* EBA Taxonomy 4.2 support

See the `CHANGELOG <https://github.com/Meaningful-Data/xbridge/blob/main/CHANGELOG.md>`_ for complete version history.

Documentation Contents
======================

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   quickstart.rst
   faq.rst

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   technical_notes.rst

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
