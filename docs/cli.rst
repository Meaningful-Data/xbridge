Command-Line Interface
======================

XBridge provides a command-line interface for quick conversions and validation without writing code.

Usage
-----

.. code-block:: bash

    xbridge INPUT_FILE [OPTIONS]
    xbridge validate INPUT_FILE [OPTIONS]

Arguments
---------

**Positional Arguments:**

``input_file``
    Path to the input XBRL-XML file (required)

**Optional Arguments:**

``--output-path PATH``
    Output directory path. If not specified, the output will be saved in the same directory as the input file.

``--headers-as-datapoints``
    Treat headers as datapoints in the output. Default is False.

``--strict-validation``
    Raise errors on validation failures. This is the default behavior.

``--no-strict-validation``
    Emit warnings instead of errors for validation failures. Use this to continue processing despite orphaned facts.

``-h, --help``
    Show help message and exit.

CLI Examples
------------

Basic conversion (output to same directory as input):

.. code-block:: bash

    xbridge instance.xbrl

Specify output directory:

.. code-block:: bash

    xbridge instance.xbrl --output-path ./converted

Continue with warnings instead of errors:

.. code-block:: bash

    xbridge instance.xbrl --no-strict-validation

Include headers as datapoints:

.. code-block:: bash

    xbridge instance.xbrl --headers-as-datapoints

Combine multiple options:

.. code-block:: bash

    xbridge instance.xbrl \
        --output-path ./output \
        --headers-as-datapoints \
        --no-strict-validation

Batch processing with shell:

.. code-block:: bash

    # Convert all XBRL files in a directory
    for file in instances/*.xbrl; do
        xbridge "$file" --output-path converted/
    done

Validate Command
----------------

The ``validate`` subcommand checks XBRL instance files against structural and regulatory rules without performing conversion.

.. code-block:: bash

    xbridge validate INPUT_FILE [OPTIONS]

**Positional Arguments:**

``input_file``
    Path to the XBRL file (``.xbrl``, ``.xml``, or ``.zip``) (required)

**Optional Arguments:**

``--eba``
    Enable EBA-specific validation rules (entity format, decimal precision, currency checks, etc.). Default is False.

``--post-conversion``
    Skip structural checks guaranteed by xbridge's converter. Only meaningful for ``.zip`` (CSV) files. Default is False.

``--json``
    Output findings as JSON instead of human-readable text. Useful for integration with other tools.

``-h, --help``
    Show help message and exit.

Validate Examples
-----------------

Basic validation:

.. code-block:: bash

    xbridge validate instance.xbrl

Enable EBA-specific rules:

.. code-block:: bash

    xbridge validate instance.xbrl --eba

Validate an XBRL-CSV package:

.. code-block:: bash

    xbridge validate report.zip --eba

Validate converter output (skip structural checks):

.. code-block:: bash

    xbridge validate output.zip --eba --post-conversion

Get JSON output for tooling integration:

.. code-block:: bash

    xbridge validate instance.xbrl --eba --json

The validate command exits with code **0** when no errors are found, and **1** when at least one ERROR-level finding is present.
