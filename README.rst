Overview
============
XBridge is a Python library which main function is to convert XBRL-XML files into XBRL-CSV files by using EBA's taxonomy.
It works with EBA Taxonomy latest published version (4.1). Library must be updated on each new EBA taxonomy version.

Installation
============

To install the library, run the following command:

.. code:: bash

    pip install eba-xbridge


How XBridge works:
=========================

Firstly, an XBRL-XML file has to be selected to convert it. Then, that XBRL-XML file is input in the following function contained in the ``API`` package:

.. code:: python

  >>> from xbridge.api import convert_instance

  >>> input_path = "data/input"

  >>> output_path = "data/output"

  >>> convert_instance(input_path, output_path)

The sources to do this process are two: The XML-instances and EBA´s taxonomy.

The output is the converted XBRL-CSV file placed in the output_path, as zip format
