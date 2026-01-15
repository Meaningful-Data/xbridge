API Reference
*************

This is the ``API`` module of XBridge, providing the main interface for converting XBRL-XML files to XBRL-CSV format.

.. currentmodule:: xbridge.api




.. seealso::

   For command-line usage, see :doc:`cli`.

Python API
----------


Convert XBRL Instance to CSV
-----------------------------

.. autofunction:: convert_instance

Basic Usage
-----------

Convert an XBRL-XML instance file with default settings:

.. code-block:: python

    from xbridge.api import convert_instance

    # Simple conversion
    result = convert_instance(
        instance_path="data/instance.xbrl",
        output_path="data/output"
    )
    print(f"Conversion complete: {result}")

Advanced Usage Examples
-----------------------

Convert with Custom Options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use all available parameters for fine-grained control:

.. code-block:: python

    from xbridge.api import convert_instance
    from pathlib import Path

    # Advanced conversion with all options
    output_file = convert_instance(
        instance_path=Path("data/regulatory_report.xbrl"),
        output_path=Path("data/converted"),
        headers_as_datapoints=True,  # Include headers as datapoints
        validate_filing_indicators=True,  # Validate orphaned facts
        strict_validation=False  # Emit warnings instead of raising errors
    )

    print(f"Conversion saved to: {output_file}")

Handle Validation Warnings
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use non-strict validation to continue despite orphaned facts:

.. code-block:: python

    import logging
    from xbridge.api import convert_instance

    # Configure logging to see warnings
    logging.basicConfig(level=logging.WARNING)

    # Convert with warnings instead of errors
    try:
        result = convert_instance(
            instance_path="data/instance_with_issues.xbrl",
            output_path="data/output",
            validate_filing_indicators=True,
            strict_validation=False  # Continue despite validation issues
        )
        print(f"Conversion completed with warnings: {result}")
    except Exception as e:
        print(f"Conversion failed: {e}")

Batch Conversion
^^^^^^^^^^^^^^^^

Convert multiple files in a directory:

.. code-block:: python

    from pathlib import Path
    from xbridge.api import convert_instance

    input_dir = Path("data/instances")
    output_dir = Path("data/converted")
    output_dir.mkdir(exist_ok=True)

    # Convert all XBRL files
    for xbrl_file in input_dir.glob("*.xbrl"):
        print(f"Converting {xbrl_file.name}...")
        try:
            output_file = convert_instance(
                instance_path=xbrl_file,
                output_path=output_dir / xbrl_file.stem
            )
            print(f"  ✓ Success: {output_file}")
        except Exception as e:
            print(f"  ✗ Failed: {e}")

Parameters
----------

:param instance_path: Path to the XBRL-XML instance file. Accepts ``str`` or ``pathlib.Path``.

:param output_path: Directory where the converted CSV files will be saved. If ``None``, uses the current directory. Accepts ``str``, ``pathlib.Path``, or ``None``.

:param headers_as_datapoints: If ``True``, table headers are treated as datapoints in the output. Default is ``False``.

:param validate_filing_indicators: If ``True``, validates that all facts belong to reported tables (no orphaned facts). Default is ``True``.

:param strict_validation: If ``True``, raises an error when orphaned facts are detected. If ``False``, emits a warning and continues. Only relevant when ``validate_filing_indicators=True``. Default is ``True``.

:return: ``pathlib.Path`` object pointing to the generated ZIP file containing XBRL-CSV output.

:raises FileNotFoundError: If the instance file doesn't exist.
:raises ValueError: If validation fails and ``strict_validation=True``.
:raises Exception: For other conversion errors (malformed XML, taxonomy issues, etc.).


Load an XBRL-XML Instance
==========================

.. autofunction:: load_instance

Usage Examples
--------------

Basic Instance Loading
^^^^^^^^^^^^^^^^^^^^^^^

Load and inspect an XBRL-XML instance:

.. code-block:: python

    from xbridge.api import load_instance

    # Load instance
    instance = load_instance("data/instance.xbrl")

    # Access instance properties
    print(f"Entity: {instance.entity}")
    print(f"Period: {instance.period}")
    print(f"Number of facts: {len(instance.facts)}")
    print(f"Number of contexts: {len(instance.contexts)}")

Inspect Instance Details
^^^^^^^^^^^^^^^^^^^^^^^^^

Examine facts and contexts in detail:

.. code-block:: python

    from xbridge.api import load_instance

    instance = load_instance("data/regulatory_report.xbrl")

    # Inspect facts
    print(f"Total facts: {len(instance.facts)}")
    for i, fact in enumerate(instance.facts[:5]):  # First 5 facts
        print(f"Fact {i+1}:")
        print(f"  Concept: {fact.concept}")
        print(f"  Value: {fact.value}")
        print(f"  Context: {fact.context_ref}")
        print(f"  Decimals: {fact.decimals}")

    # Inspect contexts
    print(f"\nTotal contexts: {len(instance.contexts)}")
    for context_id, context in list(instance.contexts.items())[:3]:
        print(f"Context {context_id}:")
        print(f"  Entity: {context.entity}")
        print(f"  Period: {context.period}")

Validate Before Conversion
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Load an instance to validate it before conversion:

.. code-block:: python

    from xbridge.api import load_instance, convert_instance
    from pathlib import Path

    instance_path = Path("data/report.xbrl")

    # Load and validate
    try:
        instance = load_instance(instance_path)

        # Check basic requirements
        if not instance.facts:
            raise ValueError("Instance has no facts")

        if not instance.entity:
            raise ValueError("Instance has no entity information")

        print(f"✓ Validation passed")
        print(f"  Entity: {instance.entity}")
        print(f"  Facts: {len(instance.facts)}")

        # Proceed with conversion
        output = convert_instance(instance_path, "data/output")
        print(f"✓ Conversion successful: {output}")

    except Exception as e:
        print(f"✗ Validation or conversion failed: {e}")

Parameters
----------

:param instance_path: Path to the XBRL-XML instance file. Accepts ``str`` or ``pathlib.Path``.

:return: ``Instance`` object containing parsed XBRL data.

:raises FileNotFoundError: If the instance file doesn't exist.
:raises Exception: If the XML is malformed or cannot be parsed.

Return Value
------------

Returns an ``Instance`` object with the following main attributes:

- ``facts``: List of all facts in the instance
- ``contexts``: Dictionary of contexts (key: context ID)
- ``entity``: Entity identifier
- ``period``: Reporting period
- ``filing_indicators``: List of filing indicators
- ``base_currency``: Base currency code

See :doc:`xml_instance` for complete ``Instance`` class documentation






