Converter
*********
The ``converter`` modules holds the Converter class, which converts XBRL-XML to XBRL-CSV
taking as input taxonomy and instance objects.

Main function is to do an inner join between the XML instance and the preprocessed JSON, to generate an XBRL-CSV file.


.. py:currentmodule:: xbridge.converter

.. autoclass:: Converter
    :members:
    :show-inheritance:
    :undoc-members:

Generating variables:
---------------------

Firstly, variables are generated taking the pre-processed tables that form the modules, which URLs are saved in the ``index.json`` file,
and the instance columns that form the :obj:`XML_instance <xbridge.xml_instance>`. If instance have not got any open keys, variables are not going to be generated.

``Index.json`` will look like this:

.. image:: /images/indexJSON.png
    :width: 400

After that, variables are parsed, cleaning them up and an intersection is done with them and the instance columns. Now, the table is generated.

Converting tables:
------------------

:obj:`Tables <xbridge.taxonomy.Table>` are generated, filling them with the variables generated before, and save in a CSV file. It will contain the variable version IDs.

This tables have to be treatise, so they can be used in the conversion process. This treatment consists in replacing hyphens with dots, so CSV files can be generated.



Converting filing indicators:
-----------------------------

The :obj:`filing indicators <xbridge.xml_instance.FilingIndicator>` show which tables within the module are reported. Reports.json files only indicate XBRL related metadata and the module URL.


Converting parameters:
----------------------

``Parameters`` will contain all info related to entity, period, baseCurrency and decimals contained in the XBRL-XML file.



