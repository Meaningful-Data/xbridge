Command-Line Interface
======================

XBridge provides a command-line interface for quick conversions without writing code.

Usage
-----

.. code-block:: bash

    xbridge INPUT_FILE [OPTIONS]

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
