Frequently Asked Questions (FAQ)
=================================

General Questions
-----------------

What is XBridge?
^^^^^^^^^^^^^^^^

XBridge is a Python library that converts XBRL-XML files to XBRL-CSV format using the EBA (European Banking Authority) taxonomy. It's designed for regulatory reporting in the banking and financial sector.

What taxonomy versions does XBridge support?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

XBridge currently supports **EBA Taxonomy version 4.1**. The library must be updated when new taxonomy versions are released.

Is XBridge free and open source?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Yes! XBridge is licensed under the Apache License 2.0, which is a permissive open-source license. You can use it freely in both commercial and non-commercial projects.

What Python versions are supported?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

XBridge supports Python 3.9 through 3.13. We recommend using the latest stable Python version for the best performance and security.

Installation & Setup
--------------------

How do I install XBridge?
^^^^^^^^^^^^^^^^^^^^^^^^^^

Install using pip:

.. code-block:: bash

    pip install eba-xbridge

See the :doc:`quickstart` guide for more details.

Why do I need the 7z command-line tool?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The 7z tool is required to extract the compressed EBA taxonomy files (which are distributed as .7z archives). XBridge uses this tool during taxonomy loading.

**Installation:**

- Ubuntu/Debian: ``sudo apt-get install p7zip-full``
- macOS: ``brew install p7zip``
- Windows: Download from `7-zip.org <https://www.7-zip.org/>`_

Can I use XBridge in a Docker container?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Yes! Here's a minimal Dockerfile:

.. code-block:: dockerfile

    FROM python:3.11-slim

    # Install 7z
    RUN apt-get update && apt-get install -y p7zip-full && rm -rf /var/lib/apt/lists/*

    # Install XBridge
    RUN pip install eba-xbridge

    WORKDIR /app

Can I use XBridge with virtual environments?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Yes, and it's recommended! Create a virtual environment:

.. code-block:: bash

    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install eba-xbridge

Usage Questions
---------------

How do I convert a simple XBRL-XML file?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use the ``convert_instance`` function:

.. code-block:: python

    from xbridge.api import convert_instance

    convert_instance(
        instance_path="instance.xbrl",
        output_path="output"
    )

See :doc:`quickstart` for a complete tutorial.

What's the difference between strict and non-strict validation?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Strict validation** (``strict_validation=True``): Raises an error if orphaned facts are found
- **Non-strict validation** (``strict_validation=False``): Emits a warning but continues processing

Use non-strict mode when you want to process files despite validation issues:

.. code-block:: python

    convert_instance(
        instance_path="instance.xbrl",
        output_path="output",
        strict_validation=False  # Warnings instead of errors
    )

What are orphaned facts?
^^^^^^^^^^^^^^^^^^^^^^^^^

Orphaned facts are data points that don't belong to any of the reported tables according to the filing indicators. This can happen if:

- The filing indicators are incomplete
- Facts reference tables that weren't marked as reported
- There are data quality issues in the source file

How do I batch process multiple files?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Loop through files in a directory:

.. code-block:: python

    from pathlib import Path
    from xbridge.api import convert_instance

    for xbrl_file in Path("instances").glob("*.xbrl"):
        try:
            convert_instance(xbrl_file, "output" / xbrl_file.stem)
            print(f"✓ {xbrl_file.name}")
        except Exception as e:
            print(f"✗ {xbrl_file.name}: {e}")

Can I inspect an instance without converting it?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Yes, use ``load_instance``:

.. code-block:: python

    from xbridge.api import load_instance

    instance = load_instance("instance.xbrl")
    print(f"Entity: {instance.entity}")
    print(f"Facts: {len(instance.facts)}")
    print(f"Period: {instance.period}")

See :doc:`api` for more details.

Output & Results
----------------

What format is the output?
^^^^^^^^^^^^^^^^^^^^^^^^^^^

XBridge produces a ZIP file containing:

- **CSV files** for each reported table (in ``reports/`` directory)
- **filing-indicators.csv**: Lists which tables are reported
- **parameters.csv**: Report-level parameters (entity, period, currency, decimals)
- **META-INF/reports.json**: Metadata in JSON format

How do I extract and read the output?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extract the ZIP file:

.. code-block:: bash

    unzip output/instance.zip -d extracted/

Or programmatically:

.. code-block:: python

    import zipfile
    import csv

    with zipfile.ZipFile("output/instance.zip", 'r') as zf:
        with zf.open('parameters.csv') as f:
            reader = csv.DictReader(f.read().decode('utf-8').splitlines())
            for row in reader:
                print(row)

Can I customize the output format?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

XBridge produces standard XBRL-CSV format as specified by the EBA taxonomy. The format itself is not customizable, but you can:

- Use ``headers_as_datapoints=True`` to include headers as datapoints
- Post-process the CSV files after conversion

Performance Questions
---------------------

How long does conversion take?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Conversion time depends on:

- File size (number of facts)
- System resources (CPU, memory)
- Disk I/O speed

Typical times:

- Small files (<1000 facts): < 1 second
- Medium files (1000-10000 facts): 1-5 seconds
- Large files (>10000 facts): 5-30 seconds

Can I speed up batch processing?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Yes, use parallel processing:

.. code-block:: python

    from concurrent.futures import ProcessPoolExecutor
    from pathlib import Path
    from xbridge.api import convert_instance

    def convert_file(file_path):
        try:
            return convert_instance(file_path, "output" / file_path.stem)
        except Exception as e:
            return f"Error: {e}"

    files = list(Path("instances").glob("*.xbrl"))

    with ProcessPoolExecutor(max_workers=4) as executor:
        results = executor.map(convert_file, files)

    for file, result in zip(files, results):
        print(f"{file.name}: {result}")

Why is taxonomy loading slow?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Loading the EBA taxonomy from a .7z archive can take several minutes because:

- The archive is large (hundreds of MB)
- The 7z extraction is CPU-intensive
- Taxonomy files must be parsed and indexed

This is a one-time operation. Once loaded, the taxonomy is cached.

Error Messages & Troubleshooting
---------------------------------

"FileNotFoundError: instance.xbrl not found"
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The specified XBRL file doesn't exist. Check:

- File path is correct
- File exists at that location
- You're in the correct working directory

"7z command not found"
^^^^^^^^^^^^^^^^^^^^^^

Install the 7z command-line tool (see installation instructions above).

"Orphaned facts detected"
^^^^^^^^^^^^^^^^^^^^^^^^^^

Some facts don't belong to reported tables. Options:

1. Use ``strict_validation=False`` to continue with warnings
2. Fix the filing indicators in your source XBRL file
3. Review the data quality of your instance

"Module 'xbridge' has no attribute 'convert_instance'"
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You're trying to use an incorrect import. Use:

.. code-block:: python

    from xbridge.api import convert_instance  # Correct

Not:

.. code-block:: python

    import xbridge
    xbridge.convert_instance(...)  # Wrong

"lxml.etree.XMLSyntaxError"
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Your XBRL-XML file is malformed. Check:

- File is valid XML
- No corruption during file transfer
- File encoding is correct (usually UTF-8)

"MemoryError"
^^^^^^^^^^^^^

Your system ran out of memory processing a large file. Try:

- Processing smaller files
- Increasing available RAM
- Processing files in batches
- Using a machine with more memory

Development & Contributing
---------------------------

How can I contribute to XBridge?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We welcome contributions! See `CONTRIBUTING.md <https://github.com/Meaningful-Data/xbridge/blob/main/CONTRIBUTING.md>`_ for:

- Development setup
- Code style guidelines
- Testing requirements
- Pull request process

How do I run the tests?
^^^^^^^^^^^^^^^^^^^^^^^^

Clone the repository and run:

.. code-block:: bash

    # Install development dependencies
    pip install -e ".[dev]"

    # Run tests
    pytest

    # Run with coverage
    pytest --cov=xbridge

How do I report a bug?
^^^^^^^^^^^^^^^^^^^^^^

Open an issue on `GitHub <https://github.com/Meaningful-Data/xbridge/issues>`_ with:

- XBridge version
- Python version
- Operating system
- Steps to reproduce
- Error message/stack trace

See our bug report template for details.

Is there a roadmap for future features?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Check the `GitHub Issues <https://github.com/Meaningful-Data/xbridge/issues>`_ page for planned features and enhancements. Feature requests are welcome!

Taxonomy & Standards
--------------------

What is XBRL?
^^^^^^^^^^^^^

XBRL (eXtensible Business Reporting Language) is an international standard for digital business reporting. It's used by regulators worldwide for financial and regulatory reporting.

What is the EBA taxonomy?
^^^^^^^^^^^^^^^^^^^^^^^^^^

The EBA (European Banking Authority) taxonomy is a specific XBRL taxonomy used for banking supervision reporting in the European Union.

Does XBridge support other taxonomies?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Currently, XBridge is specifically designed for the EBA taxonomy version 4.1. Support for other taxonomies would require significant architectural changes.

What is DORA CSV?
^^^^^^^^^^^^^^^^^

DORA (Digital Operational Resilience Act) is an EU regulation. XBridge includes support for DORA-specific CSV conversion requirements.

When will XBridge support the next taxonomy version?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

XBridge is updated when new EBA taxonomy versions are officially released. Watch the `GitHub releases <https://github.com/Meaningful-Data/xbridge/releases>`_ for updates.

Licensing & Commercial Use
---------------------------

Can I use XBridge commercially?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Yes! XBridge is licensed under Apache License 2.0, which allows commercial use. You can:

- Use it in commercial products
- Modify it for your needs
- Distribute it (with proper attribution)

See the `LICENSE <https://github.com/Meaningful-Data/xbridge/blob/main/LICENSE>`_ file for full terms.

Do I need to credit XBridge?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

While not required by the license, we appreciate attribution. You can credit:

- XBridge by MeaningfulData
- Link to https://github.com/Meaningful-Data/xbridge

Can I get commercial support?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Contact MeaningfulData at info@meaningfuldata.eu for commercial support options.

Still Have Questions?
---------------------

If your question isn't answered here:

- **Check the documentation**: https://docs.xbridge.meaningfuldata.eu
- **Search GitHub issues**: https://github.com/Meaningful-Data/xbridge/issues
- **Ask on GitHub Discussions**: https://github.com/Meaningful-Data/xbridge/discussions
- **Email us**: info@meaningfuldata.eu
