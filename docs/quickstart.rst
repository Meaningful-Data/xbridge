Quickstart Guide
================

This guide will help you get started with XBridge quickly. By the end of this tutorial, you'll be able to convert XBRL-XML files to XBRL-CSV format.

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

Your First Conversion
---------------------

XBridge offers two ways to convert files: using the **command-line interface (CLI)** or the **Python API**. Choose the method that best fits your workflow.

Method 1: Command-Line Interface (Recommended for Quick Use)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The CLI is the fastest way to convert files without writing any code.

**Step 1: Prepare Your Files**

You need:

1. An XBRL-XML instance file (e.g., ``instance.xbrl``)
2. (Optional) A directory for output

**Step 2: Run the Conversion**

Convert with default settings (output goes to same directory as input):

.. code-block:: bash

    xbridge instance.xbrl

Convert with custom output directory:

.. code-block:: bash

    xbridge instance.xbrl --output-path output/

Convert with additional options:

.. code-block:: bash

    xbridge instance.xbrl --output-path output/ --no-strict-validation

**CLI Options:**

- ``--output-path PATH``: Output directory (default: same as input file)
- ``--headers-as-datapoints``: Treat headers as datapoints (default: False)
- ``--strict-validation``: Raise errors on validation failures (default: True)
- ``--no-strict-validation``: Emit warnings instead of errors
- ``-h, --help``: Show help message

**Example with All Options:**

.. code-block:: bash

    xbridge instance.xbrl \
        --output-path ./converted \
        --headers-as-datapoints \
        --no-strict-validation

Method 2: Python API (Recommended for Integration)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use the Python API when you need programmatic control or integration with other code.

**Step 1: Prepare Your Files**

You need:

1. An XBRL-XML instance file (e.g., ``instance.xbrl``)
2. A directory for output (e.g., ``output/``)

Create the output directory:

.. code-block:: bash

    mkdir output

**Step 2: Basic Conversion**

Create a Python script ``convert.py``:

.. code-block:: python

    from xbridge.api import convert_instance

    # Convert XBRL-XML to XBRL-CSV
    output_file = convert_instance(
        instance_path="instance.xbrl",
        output_path="output"
    )

    print(f"Conversion complete! Output: {output_file}")

Run the script:

.. code-block:: bash

    python convert.py

The output will be a ZIP file containing:

- CSV files for each reported table
- Filing indicators
- Parameters
- Metadata

Step 3: Extract and Examine the Output
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extract the ZIP file:

.. code-block:: bash

    unzip output/instance.zip -d output/extracted

Examine the structure:

.. code-block:: bash

    tree output/extracted

You'll see:

.. code-block:: text

    output/extracted/
    ├── META-INF/
    │   └── reports.json
    ├── reports/
    │   ├── table_1.csv
    │   ├── table_2.csv
    │   └── ...
    ├── filing-indicators.csv
    └── parameters.csv

Common Use Cases
----------------

Use Case 1: Convert with Validation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Enable filing indicator validation to ensure data integrity:

.. code-block:: python

    from xbridge.api import convert_instance

    output = convert_instance(
        instance_path="instance.xbrl",
        output_path="output",
        validate_filing_indicators=True,  # Enable validation
        strict_validation=True  # Raise errors on issues
    )

Use Case 2: Handle Validation Warnings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you want to continue despite validation issues:

.. code-block:: python

    import logging
    from xbridge.api import convert_instance

    # Set up logging to see warnings
    logging.basicConfig(level=logging.WARNING)

    output = convert_instance(
        instance_path="instance.xbrl",
        output_path="output",
        validate_filing_indicators=True,
        strict_validation=False  # Emit warnings instead of errors
    )

Use Case 3: Inspect Instance Before Converting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Load and inspect an instance to understand its contents:

.. code-block:: python

    from xbridge.api import load_instance, convert_instance

    # Load the instance
    instance = load_instance("instance.xbrl")

    # Inspect
    print(f"Entity: {instance.entity}")
    print(f"Period: {instance.period}")
    print(f"Total facts: {len(instance.facts)}")
    print(f"Total contexts: {len(instance.contexts)}")

    # If everything looks good, convert
    if len(instance.facts) > 0:
        output = convert_instance("instance.xbrl", "output")
        print(f"Converted: {output}")
    else:
        print("No facts found, skipping conversion")

Use Case 4: Batch Processing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Convert multiple XBRL files at once:

.. code-block:: python

    from pathlib import Path
    from xbridge.api import convert_instance

    # Set up directories
    input_dir = Path("instances")
    output_dir = Path("converted")
    output_dir.mkdir(exist_ok=True)

    # Process all XBRL files
    xbrl_files = list(input_dir.glob("*.xbrl"))
    print(f"Found {len(xbrl_files)} files to convert")

    for xbrl_file in xbrl_files:
        print(f"\nConverting: {xbrl_file.name}")
        try:
            output = convert_instance(
                instance_path=xbrl_file,
                output_path=output_dir / xbrl_file.stem,
                strict_validation=False  # Continue on errors
            )
            print(f"  ✓ Success: {output}")
        except Exception as e:
            print(f"  ✗ Failed: {e}")

    print("\nBatch conversion complete!")

Use Case 5: Custom Output Handling
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Process the output programmatically:

.. code-block:: python

    import zipfile
    import csv
    from pathlib import Path
    from xbridge.api import convert_instance

    # Convert
    output_zip = convert_instance(
        instance_path="instance.xbrl",
        output_path="output"
    )

    # Extract and process
    with zipfile.ZipFile(output_zip, 'r') as zf:
        # List all files
        print("Files in archive:")
        for name in zf.namelist():
            print(f"  - {name}")

        # Read parameters
        with zf.open('parameters.csv') as f:
            reader = csv.DictReader(f.read().decode('utf-8').splitlines())
            for row in reader:
                print(f"\nParameters:")
                for key, value in row.items():
                    print(f"  {key}: {value}")

Advanced Configuration
----------------------

Headers as Datapoints
^^^^^^^^^^^^^^^^^^^^^

Include table headers as datapoints in the output:

.. code-block:: python

    from xbridge.api import convert_instance

    output = convert_instance(
        instance_path="instance.xbrl",
        output_path="output",
        headers_as_datapoints=True  # Include headers
    )

Error Handling
^^^^^^^^^^^^^^

Robust error handling for production use:

.. code-block:: python

    from xbridge.api import convert_instance
    from pathlib import Path
    import sys

    def safe_convert(instance_path, output_path):
        """Safely convert with comprehensive error handling."""
        try:
            # Validate inputs
            instance = Path(instance_path)
            if not instance.exists():
                raise FileNotFoundError(f"Instance not found: {instance}")

            if not instance.suffix == ".xbrl":
                raise ValueError(f"Expected .xbrl file, got {instance.suffix}")

            # Convert
            output = convert_instance(
                instance_path=instance,
                output_path=output_path,
                validate_filing_indicators=True,
                strict_validation=False
            )

            return output, None

        except FileNotFoundError as e:
            return None, f"File error: {e}"
        except ValueError as e:
            return None, f"Validation error: {e}"
        except Exception as e:
            return None, f"Unexpected error: {e}"

    # Use the safe function
    result, error = safe_convert("instance.xbrl", "output")

    if error:
        print(f"✗ Conversion failed: {error}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"✓ Conversion succeeded: {result}")

Next Steps
----------

Now that you've completed the quickstart:

1. **Explore the Documentation**: Check the :doc:`cli` and :doc:`api` references
2. **Understand the Architecture**: Learn how XBridge works internally in :doc:`technical_notes`
3. **Check the FAQ**: Find answers to common questions in :doc:`faq`
4. **Explore Examples**: See more examples in the GitHub repository

Troubleshooting
---------------

**ImportError: No module named 'xbridge'**
    XBridge is not installed. Run ``pip install eba-xbridge``

**FileNotFoundError: instance.xbrl not found**
    Check the file path is correct and the file exists

**7z command not found**
    Install the 7z tool (see Prerequisites section)

**Orphaned facts error/warning**
    Some facts don't belong to any reported table. Use ``strict_validation=False`` to continue with warnings

**Very large file processing slowly**
    This is normal for large XBRL files. Consider processing in smaller batches

Getting Help
------------

If you encounter issues:

- **Documentation**: https://docs.xbridge.meaningfuldata.eu
- **GitHub Issues**: https://github.com/Meaningful-Data/xbridge/issues
- **Email**: info@meaningfuldata.eu
- **FAQ**: :doc:`faq`
