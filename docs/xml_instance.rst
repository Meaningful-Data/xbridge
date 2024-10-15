*************
XML Instance
*************

The ``xml-instance`` module contains all the classes related to XBRL-XML instance files. It contains the attributes Scenario,
Context and Facts.

The main purpose is to extract and classify the data. In the xbrl file, the basic unit is the fact, form by a unique value and its
decimals (precision), context and currency.

This facts are grouped by a context. In xbrl files, it is represented with an id, and contains info related to the entity and period where facts belongs to.
Also, an attribute named scenario appears related to the context. Its main function is parsing the xml-instance, integrating the dimension of the taxonomy's variable with the context.


.. currentmodule:: xbridge.xml_instance

Instance Class
--------------

.. autoclass:: Instance
    :members:
    :show-inheritance:
    :undoc-members:

Scenario Class
--------------

.. autoclass:: Scenario
    :members:
    :show-inheritance:
    :undoc-members:

Context Class
-------------

.. autoclass:: Context
    :members:
    :show-inheritance:
    :undoc-members:

Fact Class
----------

.. autoclass:: Fact
    :members:
    :show-inheritance:
    :undoc-members:

Filing Indicator Class
----------------------

.. autoclass:: FilingIndicator
    :members:
    :show-inheritance:
    :undoc-members:

