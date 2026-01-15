XBridge (eba-xbridge)
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

.. image:: https://img.shields.io/github/actions/workflow/status/Meaningful-Data/xbridge/testing.yml?branch=main
   :target: https://github.com/Meaningful-Data/xbridge/actions
   :alt: Build status

Overview
========

XBridge is a Python library for converting XBRL-XML files into XBRL-CSV files using the EBA (European Banking Authority) taxonomy. It provides a simple, reliable way to transform regulatory reporting data from XML format to CSV format.

The library supports **EBA Taxonomy version 4.2**, as published on the 14th January 2026 and includes support for DORA (Digital Operational Resilience Act) CSV conversion. The library must be updated with each new EBA taxonomy version release.

Key Features
============

* **XBRL-XML to XBRL-CSV Conversion**: Seamlessly convert XBRL-XML instance files to XBRL-CSV format
* **Command-Line Interface**: Quick conversions without writing code using the ``xbridge`` CLI
* **Python API**: Programmatic conversion for integration with other tools and workflows
* **EBA Taxonomy 4.2 Support**: Built for the latest EBA taxonomy specification
* **DORA CSV Conversion**: Support for Digital Operational Resilience Act reporting
* **Configurable Validation**: Flexible filing indicator validation with strict or warning modes
* **Decimal Handling**: Intelligent decimal precision handling with configurable options
* **Type Safety**: Fully typed codebase with MyPy strict mode compliance
* **Python 3.9+**: Supports Python 3.9 through 3.13

Prerequisites
=============

* **Python**: 3.9 or higher
* **7z Command-Line Tool**: Required for loading compressed taxonomy files (7z or ZIP format)

  * On Ubuntu/Debian: ``sudo apt-get install p7zip-full``
  * On macOS: ``brew install p7zip``
  * On Windows: Download from `7-zip.org <https://www.7-zip.org/>`_

Installation
============

Install XBridge from PyPI using pip:

.. code-block:: bash

    pip install eba-xbridge

For development installation, see `CONTRIBUTING.md <CONTRIBUTING.md>`_.

Quick Start
===========

XBridge offers two ways to convert XBRL-XML files to XBRL-CSV: a command-line interface (CLI) for quick conversions, and a Python API for programmatic use.

Command-Line Interface
----------------------

The CLI provides a quick way to convert files without writing code:

.. code-block:: bash

    # Basic conversion (output to same directory as input)
    xbridge instance.xbrl

    # Specify output directory
    xbridge instance.xbrl --output-path ./output

    # Continue with warnings instead of errors
    xbridge instance.xbrl --no-strict-validation

    # Include headers as datapoints
    xbridge instance.xbrl --headers-as-datapoints

**CLI Options:**

* ``--output-path PATH``: Output directory (default: same as input file)
* ``--headers-as-datapoints``: Treat headers as datapoints (default: False)
* ``--strict-validation``: Raise errors on validation failures (default: True)
* ``--no-strict-validation``: Emit warnings instead of errors

For more CLI options, run ``xbridge --help``.

Python API - Basic Conversion
------------------------------

Convert an XBRL-XML instance file to XBRL-CSV using the Python API:

.. code-block:: python

    from xbridge.api import convert_instance

    # Basic conversion
    input_path = "path/to/instance.xbrl"
    output_path = "path/to/output"

    convert_instance(input_path, output_path)

The converted XBRL-CSV files will be saved as a ZIP archive in the output directory.

Python API - Advanced Usage
----------------------------

Customize the conversion with additional parameters:

.. code-block:: python

    from xbridge.api import convert_instance

    # Conversion with custom options
    convert_instance(
        instance_path="path/to/instance.xbrl",
        output_path="path/to/output",
        headers_as_datapoints=True,  # Treat headers as datapoints
        validate_filing_indicators=True,  # Validate filing indicators
        strict_validation=False,  # Emit warnings instead of errors for orphaned facts
    )

Python API - Handling Warnings
------------------------------

XBridge emits structured warnings that can be filtered or turned into errors from your code.
The most common ones are:

* ``IdentifierPrefixWarning``: Unknown entity identifier prefix; XBridge falls back to ``rs``.
* ``FilingIndicatorWarning``: Filing indicator inconsistencies; some facts are excluded.

To capture these warnings when using ``convert_instance``:

.. code-block:: python

    import warnings
    from xbridge.api import convert_instance
    from xbridge.exceptions import XbridgeWarning, FilingIndicatorWarning

    input_path = "path/to/instance.xbrl"
    output_path = "path/to/output"

    with warnings.catch_warnings(record=True) as caught:
        # Ensure all xbridge warnings are captured
        warnings.simplefilter("always", XbridgeWarning)

        zip_path = convert_instance(
            instance_path=input_path,
            output_path=output_path,
            validate_filing_indicators=True,
            strict_validation=False,  # Warnings instead of errors for orphaned facts
        )

    filing_warnings = [
        w for w in caught if issubclass(w.category, FilingIndicatorWarning)
    ]
    for w in filing_warnings:
        print(f"Filing indicator warning: {w.message}")

To treat all XBridge warnings as errors:

.. code-block:: python

    import warnings
    from xbridge.api import convert_instance
    from xbridge.exceptions import XbridgeWarning

    with warnings.catch_warnings():
        warnings.simplefilter("error", XbridgeWarning)
        convert_instance("path/to/instance.xbrl", "path/to/output")

Loading an Instance
-------------------

Load and inspect an XBRL-XML instance without converting:

.. code-block:: python

    from xbridge.api import load_instance

    instance = load_instance("path/to/instance.xbrl")

    # Access instance properties
    print(f"Entity: {instance.entity}")
    print(f"Period: {instance.period}")
    print(f"Facts count: {len(instance.facts)}")

How XBridge Works
=================

XBridge performs the conversion in several steps:

1. **Load the XBRL-XML instance**: Parse and extract facts, contexts, scenarios, and filing indicators
2. **Load the EBA taxonomy**: Access pre-processed taxonomy modules containing tables and variables
3. **Match and validate**: Join instance facts with taxonomy definitions
4. **Generate CSV files**: Create XBRL-CSV files including:

   * Data tables with facts and dimensions
   * Filing indicators showing reported tables
   * Parameters (entity, period, base currency, decimals)

5. **Package output**: Bundle all CSV files into a ZIP archive

Output Structure
----------------

The output ZIP file contains:

* **META-INF/**: JSON report package metadata
* **reports/**: CSV files for each reported table
* **filing-indicators.csv**: Table reporting indicators
* **parameters.csv**: Report-level parameters

Documentation
=============

Comprehensive documentation is available at `docs.xbridge.meaningfuldata.eu <https://docs.xbridge.meaningfuldata.eu>`_.

The documentation includes:

* **API Reference**: Complete API documentation
* **Quickstart Guide**: Step-by-step tutorials
* **Technical Notes**: Architecture and design details
* **FAQ**: Frequently asked questions

Taxonomy Loading
================

If you need to work with the EBA taxonomy directly, you can load it using:

.. code-block:: bash

    python -m xbridge.taxonomy_loader --input_path path/to/FullTaxonomy.7z

This generates an ``index.json`` file containing module references and pre-processed taxonomy data.

.. warning::
    Loading the taxonomy from a 7z package may take several minutes. Ensure the ``7z`` command is available on your system.

Configuration Options
=====================

convert_instance Parameters
----------------------------

* **instance_path** (str | Path): Path to the XBRL-XML instance file
* **output_path** (str | Path | None): Output directory for CSV files (default: current directory)
* **headers_as_datapoints** (bool): Treat table headers as datapoints (default: False)
* **validate_filing_indicators** (bool): Validate that facts belong to reported tables (default: True)
* **strict_validation** (bool): Raise errors on validation failures; if False, emit warnings (default: True)

Troubleshooting
===============

Common Issues
-------------

**7z command not found**
    Install the 7z command-line tool using your system's package manager (see Prerequisites).

**Taxonomy version mismatch**
    Ensure you're using the correct version of XBridge for your taxonomy version. XBridge 1.5.x supports EBA Taxonomy 4.2.

**Orphaned facts warning/error**
    Facts that don't belong to any reported table. Set ``strict_validation=False`` to continue with warnings instead of errors.

**Decimal precision issues**
    XBridge automatically handles decimal precision from the taxonomy. Check the parameters.csv file for applied decimal settings.

For more issues, see our `FAQ <https://docs.xbridge.meaningfuldata.eu/faq.html>`_ or `open an issue <https://github.com/Meaningful-Data/xbridge/issues>`_.

Contributing
============

We welcome contributions! Please see `CONTRIBUTING.md <CONTRIBUTING.md>`_ for:

* Development setup instructions
* Code style guidelines
* Testing requirements
* Pull request process

Before contributing, please read our `Code of Conduct <CODE_OF_CONDUCT.md>`_.

Changelog
=========

See `CHANGELOG.md <CHANGELOG.md>`_ for a detailed history of changes.

Support
=======

* **Documentation**: https://docs.xbridge.meaningfuldata.eu
* **Issue Tracker**: https://github.com/Meaningful-Data/xbridge/issues
* **Email**: info@meaningfuldata.eu
* **Company**: https://www.meaningfuldata.eu/

Security
========

For security issues, please see our `Security Policy <SECURITY.md>`_.

License
=======

This project is licensed under the Apache License 2.0 - see the `LICENSE <LICENSE>`_ file for details.

Authors & Maintainers
=====================

**MeaningfulData** - https://www.meaningfuldata.eu/

Maintainers:

* Antonio Olleros (antonio.olleros@meaningfuldata.eu)
* Jesus Simon (jesus.simon@meaningfuldata.eu)
* Francisco Javier Hernandez del Caño (javier.hernandez@meaningfuldata.eu)
* Guillermo Garcia Martin (guillermo.garcia@meaningfuldata.eu)

Acknowledgments
===============

This project is designed to work with the European Banking Authority (EBA) taxonomy for regulatory reporting
