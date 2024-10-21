"""
    Module with the classes related to XBRL-XML instance files.
"""

import pandas as pd
from lxml import etree


class Instance:
    """Class representing an XBRL XML instance file. Its attributes are the characters contained in the XBRL files.
    Each property returns one of these attributes.

    :param path: File path to be used

    """

    def __init__(self, path: str = None):
        self.path = path
        self.root = etree.parse(self.path).getroot()

        self._facts_list_dict = None
        self._df = None
        self._facts = None
        self._contexts = None
        self._module_code = None
        self._module_ref = None
        self._entity = None
        self._period = None
        self._filing_indicators = None
        self._base_currency = None
        self._units = None
        self._base_currency_unit = None
        self._pure_unit = None
        self._decimals_monetary = None
        self._decimals_percentage = None
        self._decimals_monetary_set = set()
        self._decimals_percentage_set = set()
        self._identifier_prefix = None

        self.parse()

    @property
    def namespaces(self):
        """Returns the `namespaces <https://www.xbrl.org/guidance/xbrl-glossary/#2-other-terms-in-technical-or-common-use:~:text=calculation%20tree.-,Namespace,-A%20namespace%20>`_ is of the instance file."""
        return self.root.nsmap

    @property
    def contexts(self):
        """Returns the :obj:`Context <xbridge.xml_instance.Context>` of the instance file."""
        return self._contexts

    @property
    def facts(self):
        """Returns the `facts <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=accounting%20standards%20body.-,Fact,-A%20fact%20is>`_ of the instance file."""
        return self._facts

    @property
    def facts_list_dict(self):
        """Returns a list of dictionaries with the `facts <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=accounting%20standards%20body.-,Fact,-A%20fact%20is>`_
        of the instance file."""
        return self._facts_list_dict

    @property
    def filing_indicators(self):
        """Returns the filing indicators of the instance file."""
        return self._filing_indicators

    def get_facts_list_dict(self):
        """Generates a list of dictionaries with the `facts <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=accounting%20standards%20body.-,Fact,-A%20fact%20is>`_
        of the instance file."""
        result = []
        for fact in self.facts:
            fact_dict = fact.__dict__()

            context_id = fact_dict.pop("context")

            if context_id is not None:
                context = self.contexts[context_id].__dict__()
                fact_dict.update(context)

            result.append(fact_dict)

        self._facts_list_dict = result

    @property
    def module_code(self):
        """Returns the module name of the instance file."""
        return self._module_code

    @property
    def module_ref(self):
        """Returns the module reference of the instance file."""
        return self._module_ref

    @property
    def instance_df(self):
        """Returns a pandas DataFrame with the `facts <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=accounting%20standards%20body.-,Fact,-A%20fact%20is>`_
        of the instance file."""
        return self._df

    def to_df(self):
        """Generates a pandas DataFrame with the `facts <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=accounting%20standards%20body.-,Fact,-A%20fact%20is>`_
        of the instance file."""
        self._df = pd.DataFrame.from_dict(self.facts_list_dict)
        df_columns = list(self._df.columns)
        ##Workaround
        # Dropping period an entity columns because in current EBA architecture,
        # they have to be the same for all the facts. (Performance reasons)
        if "period" in df_columns:
            del self._df["period"]
        if "entity" in df_columns:
            del self._df["entity"]

    @property
    def identifier_prefix(self):
        """Returns the identifier prefix of the instance file."""
        entity_prefix_mapping = {
            "https://eurofiling.info/eu/rs": "rs",
            "http://standards.iso.org/iso/17442": "lei"}

        return entity_prefix_mapping[self._identifier_prefix]


    @property
    def entity(self):
        """Returns the entity of the instance file."""
        return f"{self.identifier_prefix}:{self._entity}"


    @property
    def period(self):
        """Returns the period of the instance file"""
        return self._period

    @property
    def units(self):
        """Returns the units of the instance file"""
        return self._units

    @property
    def base_currency(self):
        """Returns the base currency of the instance file"""
        return self._base_currency

    def parse(self):
        """Parses the XML file into the library objects."""

        self.get_units()
        self.get_contexts()
        self.get_facts()
        self.get_module_code()
        self.get_filing_indicators()

        # TODO: Validate that all the assumptions about the EBA instances are correct
        # Should be an optional parameter (to avoid performance issues when it is known
        # that the assumptions are correct)
        # - Validate that there is only one entity
        # - Validate that there is only one period
        # - Validate that all the facts have the same currency

    def get_contexts(self):
        """Extracts :obj:`Context <xbridge.xml_instance.Context>` from the XML instance file."""

        contexts = {}
        for context in self.root.findall(
            "{http://www.xbrl.org/2003/instance}context", self.namespaces
        ):
            context_object = Context(context)
            contexts[context_object.id] = context_object

        self._contexts = contexts

        self._identifier_prefix = self.root.find(
            "{http://www.xbrl.org/2003/instance}context", self.namespaces
        ).find("{http://www.xbrl.org/2003/instance}entity").\
            find("{http://www.xbrl.org/2003/instance}identifier").\
                attrib.get("scheme")

    def get_facts(self):
        """Extracts `facts <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=accounting%20standards%20body.-,Fact,-A%20fact%20is>`_
        from the XML instance file."""
        facts = []
        for child in self.root:
            facts_prefixes = list(self.root.nsmap.keys())[
                list(self.root.nsmap.values()).index(
                    "http://www.eba.europa.eu/xbrl/crr/dict/met"
                )
            ]
            if child.prefix == facts_prefixes:
                fact = Fact(child)
                if fact.unit == self._base_currency_unit:
                    self._decimals_monetary_set.add(fact.decimals)
                if fact.unit == self._pure_unit:
                    self._decimals_percentage_set.add(fact.decimals)
                facts.append(Fact(child))

        self._facts = facts
        self.get_facts_list_dict()
        self.to_df()

    def get_module_code(self):
        """Extracts the module name from the XML instance file."""

        for child in self.root:
            if child.prefix == "link":
                value = child.attrib["{http://www.w3.org/1999/xlink}href"]
                self._module_ref = value
                value = value.split("/mod/")[1].split(".xsd")[0]
                self._module_code = value
                break

    def get_filing_indicators(self):
        """Extracts `filing <https://www.xbrl.org/guidance/xbrl-glossary/#2-other-terms-in-technical-or-common-use:~:text=data%20point.-,Filing,-The%20file%20or>`_
        indicators from the XML instance file."""
        filing_indicators = []
        for fil_ind in self.root.find(
            "{http://www.eurofiling.info/xbrl/ext/filing-indicators}fIndicators"
        ).findall(
            "{http://www.eurofiling.info/xbrl/ext/filing-indicators}filingIndicator"
        ):
            filing_indicators.append(FilingIndicator(fil_ind))

        self._filing_indicators = filing_indicators
        first_fil_ind = filing_indicators[0]
        fil_ind_context = self.contexts[first_fil_ind.context]
        self._entity = fil_ind_context.entity
        self._period = fil_ind_context.period

    def get_units(self):
        """Extracts the base currency of the instance"""
        units = {}
        for unit in self.root.findall("{http://www.xbrl.org/2003/instance}unit"):
            unit_name = unit.attrib["id"]
            unit_value = unit.find("{http://www.xbrl.org/2003/instance}measure").text
            ##Workaround
            # We are assuming that currencies always start as iso4217
            if unit_value[:8].lower() == "iso4217:":
                ##Workaround
                # For the XBRL-CSV, we assume one currency for the whole instance
                # We take the first currency we find, because we assume that,
                # in the current EBA architecture, all the facts have the same currency
                self._base_currency = unit_value
                self._base_currency_unit = unit_name
            if unit_value in ["xbrli:pure", "pure"]:
                self._pure_unit = unit_name
            units[unit_name] = unit_value

        self._units = units

    # TODO: For this to be more efficient, check it once all contexts are loaded.
    def validate_entity(self, context):
        """Validates that a certain :obj:`Context <xbridge.xml_instance.Context>` does not add a second entity
        (i.e., the instance contains data only for one entity)."""
        if getattr(self, "_entity", None) is None:
            self._entity = context
        if self._entity != context:
            raise ValueError("The instance has more than one entity")

    @property
    def decimals_percentage(self):
        "Returns the single value for percentage values in the instance."
        return (
            max(self._decimals_percentage_set)
            if len(self._decimals_percentage_set) > 0
            else None
        )

    @property
    def decimals_monetary(self):
        "Returns the single value for monetary values in the instance."
        max_reported = (
            max(self._decimals_monetary_set)
            if len(self._decimals_monetary_set) > 0
            else None
        )
        if max_reported:
            ##Workaround
            # We are assuming that the maximum number of decimals for monetary values
            # is 2, in practice. We found cases with higher numbers for some values,
            # and that causes problems in the CSV output, because the maximum was
            # applying.
            return min(int(max_reported), 2)
        return None


class Scenario:
    """Class for the scenario of a :obj:`Context <xbridge.xml_instance.Context>`. It parses the XML node with the
    scenario created and gets a value that fits with the scenario created from the XML node.
    """

    def __init__(self, scenario_xml=None):
        self.scenario_xml = scenario_xml
        self.dimensions = {}

        self.parse()

    def parse(self):
        """Parses the XML node with the scenario"""
        if self.scenario_xml is not None:
            for child in self.scenario_xml:
                ##Workaround
                # We are dropping the prefixes of the dimensions and the members
                # lxml is not able to work with namespaces in the values of the attributes
                # or the items.
                # On the other hand, we know that there are no potential conflicts because
                # the EBA is not using external properties, and for one property all the
                # items are owned by the same entity.
                dimension = child.attrib["dimension"].split(":")[1]
                value = self.get_value(child)
                value = value.split(":")[1] if ":" in value else value
                self.dimensions[dimension] = value

    @staticmethod
    def get_value(child_scenario):
        """Gets the value for `dimension <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=a%20taxonomy.-,Dimension,-A%20qualifying%20characteristic>`_
        from the XML node with the scenario."""
        if child_scenario.getchildren():
            value = child_scenario.getchildren()[0].text
        else:
            value = child_scenario.text

        return value

    def __repr__(self) -> str:
        return f"Scenario(dimensions={self.dimensions})"


class Context:
    """Class for the context of a `fact <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=accounting%20standards%20body.-,Fact,-A%20fact%20is>`_.
    Its attributes are id, entity, period and scenario. Returns a dictionary which has as keys the entity and the period.
    """

    def __init__(self, context_xml):
        self.context_xml = context_xml

        self._id = None
        self._entity = None
        self._period = None
        self._scenario = None

        self.parse()

    @property
    def id(self):
        """Returns the id of the :obj:`Context <xbridge.xml_instance.Context>`."""
        return self._id

    @property
    def entity(self):
        """Returns the entity of the :obj:`Context <xbridge.xml_instance.Context>`."""
        return self._entity

    @property
    def period(self):
        """Returns the period of the :obj:`Context <xbridge.xml_instance.Context>`."""
        return self._period

    @property
    def scenario(self):
        """Returns the scenario of the :obj:`Context <xbridge.xml_instance.Context>`."""
        return self._scenario

    def parse(self):
        """Parses the XML node with the :obj:`Context <xbridge.xml_instance.Context>`."""
        self._id = self.context_xml.attrib["id"]

        self._entity = (
            self.context_xml.find("{http://www.xbrl.org/2003/instance}entity")
            .find("{http://www.xbrl.org/2003/instance}identifier")
            .text
        )

        self._period = (
            self.context_xml.find("{http://www.xbrl.org/2003/instance}period")
            .find("{http://www.xbrl.org/2003/instance}instant")
            .text
        )

        self._scenario = Scenario(
            self.context_xml.find("{http://www.xbrl.org/2003/instance}scenario")
        )

    def __repr__(self) -> str:
        return (
            f"Context(id={self.id}, entity={self.entity}, "
            f"period={self.period}, scenario={self.scenario})"
        )

    def __dict__(self):
        result = {"entity": self.entity, "period": self.period}

        for key, value in self.scenario.dimensions.items():
            result[key] = value

        return result


class Fact:
    """Class for the `facts <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=accounting%20standards%20body.-,Fact,-A%20fact%20is>`_
    of an instance. Returns the facts of the instance with information such as the value, its decimals, :obj:`Context <xbridge.xml_instance.Context>` and units.
    """

    def __init__(self, fact_xml):
        self.fact_xml = fact_xml
        self.metric = None
        self.value = None
        self.decimals = None
        self.context = None
        self.unit = None

        self.parse()

    def parse(self):
        """Parse the XML node with the `fact <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=accounting%20standards%20body.-,Fact,-A%20fact%20is>`_."""
        self.metric = self.fact_xml.tag
        self.value = self.fact_xml.text
        self.decimals = self.fact_xml.attrib.get("decimals")
        self.context = self.fact_xml.attrib.get("contextRef")
        self.unit = self.fact_xml.attrib.get("unitRef")

    def __dict__(self):
        return {
            "metric": self.metric.split("}")[1],
            "value": self.value,
            "decimals": self.decimals,
            "context": self.context,
            "unit": self.unit,
        }

    def __repr__(self) -> str:
        return (
            f"Fact(metric={self.metric}, value={self.value}, "
            f"decimals={self.decimals}, context={self.context}, "
            f"unit={self.unit})"
        )


class FilingIndicator:
    """Class for the `filing <https://www.xbrl.org/guidance/xbrl-glossary/#2-other-terms-in-technical-or-common-use:~:text=data%20point.-,Filing,-The%20file%20or>`_ indicator of an instance. Returns the filing Indicator value and also a table with a
    :obj:`Context <xbridge.xml_instance.Context>`
    """

    def __init__(self, filing_indicator_xml):
        self.filing_indicator_xml = filing_indicator_xml
        self.value = None
        self.table = None
        self.context = None

        self.parse()

    def parse(self):
        """Parse the XML node with the filing indicator."""
        value = self.filing_indicator_xml.attrib.get(
            "{http://www.eurofiling.info/xbrl/ext/filing-indicators}filed"
        )
        if value:
            self.value = True if value == "true" else False
        else:
            self.value = True
        self.table = self.filing_indicator_xml.text
        self.context = self.filing_indicator_xml.attrib.get("contextRef")

    def __dict__(self):
        return {
            "value": self.value,
            "table": self.table,
            "context": self.context,
        }

    def __repr__(self) -> str:
        return (
            f"FilingIndicator(value={self.value}, "
            f"table={self.table}, context={self.context})"
        )
