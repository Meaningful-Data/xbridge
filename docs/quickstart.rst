Quickstart Guide
================

This guide covers the three main use cases of XBridge:

1. **Convert** XBRL-XML instances to XBRL-CSV format
2. **Validate** XBRL-XML or XBRL-CSV files against structural and EBA regulatory rules
3. **Convert XBRL-CSV architecture** — restructure DORA headers-based CSV packages into standard datapoints format

Prerequisites
-------------

Before you begin, ensure you have:

1. **Python 3.9 or higher** installed

   Check your Python version:

   .. code-block:: bash

       python --version

2. **7z command-line tool** (required for taxonomy loading)

   - **Ubuntu/Debian**:

     .. code-block:: bash

         sudo apt-get install p7zip-full

   - **macOS**:

     .. code-block:: bash

         brew install p7zip

   - **Windows**: Download from `7-zip.org <https://www.7-zip.org/>`_

Installation
------------

Install XBridge using pip:

.. code-block:: bash

    pip install eba-xbridge

Verify the installation:

.. code-block:: bash

    python -c "import xbridge; print(xbridge.__version__)"

Use Case 1: XBRL-XML to XBRL-CSV Conversion
---------------------------------------------

Basic Conversion
^^^^^^^^^^^^^^^^

**CLI:**

.. code-block:: bash

    xbridge instance.xbrl

**Python API:**

.. code-block:: python

    from xbridge.api import convert_instance

    output_file = convert_instance(
        instance_path="instance.xbrl",
        output_path="output"
    )
    print(f"Conversion complete: {output_file}")

Output Structure
^^^^^^^^^^^^^^^^

The output is a ZIP file containing:

.. code-block:: text

    output/instance.zip
    ├── META-INF/
    │   └── reports.json
    ├── reports/
    │   ├── table_1.csv
    │   ├── table_2.csv
    │   └── ...
    ├── filing-indicators.csv
    └── parameters.csv

Conversion Options
^^^^^^^^^^^^^^^^^^

.. csv-table::
   :header: CLI flag | Python parameter | Description
   :widths: 30, 30, 40
   :delim: |

   ``--output-path PATH``|``output_path="path"``|Output directory (default: same folder as input)
   ``--no-strict-validation``|``strict_validation=False``|Emit warnings instead of errors on orphaned facts
   ``--headers-as-datapoints``|``headers_as_datapoints=True``|For DORA tables using headers architecture, output long (datapoints) format instead of wide (headers) format

Validate-Convert-Validate Pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

XBridge can run validation before and after conversion in a single command. Pre-conversion validation catches XML structural and EBA issues before converting; post-conversion validation runs EBA semantic checks on the generated CSV.

**CLI:**

.. code-block:: bash

    # Structural validation only
    xbridge instance.xbrl --validate

    # Include EBA regulatory rules
    xbridge instance.xbrl --validate --eba

**Python API:**

.. code-block:: python

    from xbridge.api import convert_instance
    from xbridge.exceptions import ValidationError

    try:
        output = convert_instance(
            instance_path="instance.xbrl",
            output_path="output",
            validate=True,
            eba=True,
        )
    except ValidationError as e:
        for section in e.results.values():
            for code, findings in section["errors"].items():
                for f in findings:
                    print(f"[{f['severity']}] {f['rule_id']}: {f['message']}")

**Behaviour:**

- **Pre-conversion error**: ``ValidationError`` is raised and conversion does not start.
- **Post-conversion error**: The output ZIP is still written, then ``ValidationError`` is raised. The ``path`` attribute on the exception contains the output file path.

Batch Processing
^^^^^^^^^^^^^^^^

.. code-block:: python

    from pathlib import Path
    from xbridge.api import convert_instance

    input_dir = Path("instances")
    output_dir = Path("converted")
    output_dir.mkdir(exist_ok=True)

    for xbrl_file in input_dir.glob("*.xbrl"):
        try:
            output = convert_instance(xbrl_file, output_dir / xbrl_file.stem)
            print(f"OK: {xbrl_file.name} -> {output}")
        except Exception as e:
            print(f"FAIL: {xbrl_file.name}: {e}")

Use Case 2: Standalone Validation
----------------------------------

Validate XBRL-XML (``.xbrl``) or XBRL-CSV (``.zip``) files for structural and regulatory errors without converting.

CLI Examples
^^^^^^^^^^^^

.. code-block:: bash

    # Structural checks only
    xbridge validate instance.xbrl

    # Include EBA regulatory rules
    xbridge validate instance.xbrl --eba

    # Validate a CSV package
    xbridge validate report.zip --eba

    # Skip structural checks guaranteed by xbridge's converter
    xbridge validate output.zip --eba --post-conversion

    # Machine-readable JSON output
    xbridge validate instance.xbrl --eba --json

Python API Examples
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from xbridge.validation import validate

    results = validate("instance.xbrl", eba=True)

    has_errors = any(section["errors"] for section in results.values())
    if has_errors:
        for section in results.values():
            for code, findings in section["errors"].items():
                for f in findings:
                    print(f"[{f['severity']}] {f['rule_id']}: {f['message']}")
                    print(f"  Location: {f['location']}")
    else:
        print("No errors found.")

**Exit codes** (CLI): ``0`` = no errors, ``1`` = at least one ERROR finding.

.. seealso::

   :doc:`validation`
      Full validation API documentation and architecture.

   :doc:`validation_rules`
      Complete catalogue of all validation rules.

Use Case 3: XBRL-CSV Architecture Conversion
----------------------------------------------

Convert DORA XBRL-CSV files from the **headers** architecture (columns named ``0010``, ``0020``, ..., wide format) to the standard **datapoints** architecture (``datapoint``, ``factValue``, long format).

When to Use
^^^^^^^^^^^

DORA (Digital Operational Resilience Act) reporting modules use a different CSV table layout. XBridge detects this automatically from the taxonomy metadata and converts accordingly.

How It Works
^^^^^^^^^^^^

- **Input**: ``.zip`` file containing XBRL-CSV with headers-based tables
- **Output**: ``.zip`` file with the same data restructured into datapoint-based tables
- The architecture is auto-detected from the taxonomy (``Table.check_taxonomy_architecture()``)

**CLI:**

.. code-block:: bash

    xbridge report.zip --output-path output/

**Python API:**

.. code-block:: python

    from xbridge.api import convert_instance

    output = convert_instance("report.zip", output_path="output")

.. note::

   The ``--headers-as-datapoints`` flag is only relevant when converting **XML** instances that reference a headers-architecture taxonomy — it controls whether the output uses wide (headers) or long (datapoints) format. For CSV-to-CSV conversion, the output is always datapoints architecture.

Next Steps
----------

- :doc:`validation` — full validation API documentation
- :doc:`validation_rules` — complete rules catalogue
- :doc:`cli` — CLI reference
- :doc:`api` — Python API reference

Troubleshooting
---------------

**ImportError: No module named 'xbridge'**
    XBridge is not installed. Run ``pip install eba-xbridge``

**FileNotFoundError: instance.xbrl not found**
    Check the file path is correct and the file exists

**7z command not found**
    Install the 7z tool (see Prerequisites section)

**Orphaned facts error/warning**
    Some facts don't belong to any reported table. Use ``--no-strict-validation`` (CLI) or ``strict_validation=False`` (API) to continue with warnings

**ValidationError raised during conversion**
    Pre-conversion or post-conversion validation found errors. Inspect ``e.results`` for details, or run ``xbridge validate`` separately for a full report

**Very large file processing slowly**
    This is normal for large XBRL files. Consider processing in smaller batches

Getting Help
------------

If you encounter issues:

- **Documentation**: https://docs.xbridge.meaningfuldata.eu
- **GitHub Issues**: https://github.com/Meaningful-Data/xbridge/issues
- **Email**: info@meaningfuldata.eu
