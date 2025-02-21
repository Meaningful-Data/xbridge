"""Module with the classes related to XBRL-XML instance files."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Union

import pandas as pd
from lxml import etree


class Instance:
    """Class representing an XBRL XML instance file.
    Its attributes are the characters contained in the XBRL files.
    Each property returns one of these attributes.

    :param path: File path to be used

    """

    def __init__(self, path: Optional[Union[str, bytes, etree._ElementTree]] = None) -> None:
        if path is None:
            raise ValueError("Must provide a path to XBRL file.")
        if isinstance(path, (str, bytes)):
            self.path = path
            self.root = etree.parse(self.path).getroot()
        else:
            raise TypeError("Unsupported type for 'path' argument.")

        self._facts_list_dict: Optional[List[Dict[str, Any]]] = None
        self._df: Optional[pd.DataFrame] = None
        self._facts: Optional[List[Fact]] = None
        self._contexts: Optional[Dict[str, Context]] = None
        self._module_code: Optional[str] = None
        self._module_ref: Optional[str] = None
        self._entity: Optional[str] = None
        self._period: Optional[str] = None
        self._filing_indicators: Optional[List[FilingIndicator]] = None
        self._base_currency: Optional[str] = None
        self._units: Optional[Dict[str, str]] = None
        self._base_currency_unit: Optional[str] = None
        self._pure_unit: Optional[str] = None
        self._decimals_monetary: Optional[int] = None
        self._decimals_percentage: Optional[int] = None
        self._decimals_monetary_set: Set[Optional[str]] = set()
        self._decimals_percentage_set: Set[Optional[str]] = set()
        self._identifier_prefix: Optional[str] = None

        self.parse()

    @property
    def namespaces(self) -> Dict[Optional[str], str]:
        """Returns the `namespaces
        <https://www.xbrl.org/guidance/xbrl-glossary/#2-other-terms-in-technical-or
        -common-use:~:text=calculation%20tree.-,Namespace,-A%20namespace%20>`_
        is of the instance file.
        """
        return self.root.nsmap

    @property
    def contexts(self) -> Optional[Dict[str, Context]]:
        """Returns the :obj:`Context <xbridge.xml_instance.Context>` of the instance file."""
        return self._contexts

    @property
    def facts(self) -> Optional[List[Fact]]:
        """Returns the `facts
        <https://www.xbrl.org/guidance/xbrl-glossary/#:
        ~:text=accounting%20standards%20body.-,Fact,-A%20fact%20is>`_ of the instance file."""
        return self._facts

    @property
    def facts_list_dict(self) -> Optional[List[Dict[str, Any]]]:
        """Returns a list of dictionaries with the `facts <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=accounting%20standards%20body.-,Fact,-A%20fact%20is>`_
        of the instance file.
        """
        return self._facts_list_dict

    @property
    def filing_indicators(self) -> Optional[List[FilingIndicator]]:
        """Returns the filing indicators of the instance file."""
        return self._filing_indicators

    def get_facts_list_dict(self) -> None:
        """Generates a list of dictionaries with the `facts <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=accounting%20standards%20body.-,Fact,-A%20fact%20is>`_
        of the instance file.
        """
        if self.facts is None or self.contexts is None:
            return
        result: List[Dict[str, Any]] = []
        for fact in self.facts:
            fact_dict = fact.__dict__()

            context_id = fact_dict.pop("context", None)

            if context_id is not None:
                context = self.contexts[context_id].__dict__()
                fact_dict.update(context)

            result.append(fact_dict)

        self._facts_list_dict = result

    @property
    def module_code(self) -> Optional[str]:
        """Returns the module name of the instance file."""
        return self._module_code

    @property
    def module_ref(self) -> Optional[str]:
        """Returns the module reference of the instance file."""
        return self._module_ref

    @property
    def instance_df(self) -> Optional[pd.DataFrame]:
        """Returns a pandas DataFrame with the `facts <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=accounting%20standards%20body.-,Fact,-A%20fact%20is>`_
        of the instance file.
        """
        return self._df

    def to_df(self) -> None:
        """Generates a pandas DataFrame with the `facts <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=accounting%20standards%20body.-,Fact,-A%20fact%20is>`_
        of the instance file.
        """
        if self.facts_list_dict is None:
            return
        df = pd.DataFrame.from_dict(self.facts_list_dict)  # type: ignore[call-overload]
        df_columns = list(df.columns)
        ##Workaround
        # Dropping period an entity columns because in current EBA architecture,
        # they have to be the same for all the facts. (Performance reasons)
        if "period" in df_columns:
            df.drop(columns=["period"], inplace=True)
        if "entity" in df_columns:
            df.drop(columns=["entity"], inplace=True)
        self._df = df

    @property
    def identifier_prefix(self) -> str:
        """Returns the identifier prefix of the instance file."""
        if not self._identifier_prefix:
            raise ValueError("No identifier prefix found.")
        entity_prefix_mapping = {
            "https://eurofiling.info/eu/rs": "rs",
            "http://standards.iso.org/iso/17442": "lei",
        }

        return entity_prefix_mapping[self._identifier_prefix]

    @property
    def entity(self) -> str:
        """Returns the entity of the instance file."""
        if not self._entity:
            raise ValueError("No entity found in the instance.")
        return f"{self.identifier_prefix}:{self._entity}"

    @property
    def period(self) -> Optional[str]:
        """Returns the period of the instance file"""
        return self._period

    @property
    def units(self) -> Optional[Dict[str, str]]:
        """Returns the units of the instance file"""
        return self._units

    @property
    def base_currency(self) -> Optional[str]:
        """Returns the base currency of the instance file"""
        return self._base_currency

    def parse(self) -> None:
        """Parses the XML file into the library objects."""
        try:
            self.get_units()
            self.get_contexts()
            self.get_facts()
            self.get_module_code()
            self.get_filing_indicators()
        except etree.XMLSyntaxError:
            raise ValueError("Invalid XML format")
        except Exception as e:
            raise ValueError(f"Error parsing instance: {str(e)}")

        # TODO: Validate that all the assumptions about the EBA instances are correct
        # Should be an optional parameter (to avoid performance issues when it is known
        # that the assumptions are correct)
        # - Validate that there is only one entity
        # - Validate that there is only one period
        # - Validate that all the facts have the same currency

    def get_contexts(self) -> None:
        """Extracts :obj:`Context <xbridge.xml_instance.Context>` from the XML instance file."""
        contexts: Dict[str, Context] = {}
        for context in self.root.findall(
            "{http://www.xbrl.org/2003/instance}context",
            self.namespaces,  # type: ignore[arg-type]
        ):
            context_object = Context(context)
            contexts[context_object.id] = context_object

        self._contexts = contexts

        first_ctx = self.root.find("{http://www.xbrl.org/2003/instance}context", self.namespaces)  # type: ignore[arg-type]
        if first_ctx is not None:
            entity_elem = first_ctx.find("{http://www.xbrl.org/2003/instance}entity")
            if entity_elem is not None:
                ident_elem = entity_elem.find("{http://www.xbrl.org/2003/instance}identifier")
                if ident_elem is not None:
                    self._identifier_prefix = ident_elem.attrib.get("scheme")

    def get_facts(self) -> None:
        """Extracts `facts <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=accounting%20standards%20body.-,Fact,-A%20fact%20is>`_
        from the XML instance file.
        """
        facts = []
        for child in self.root:
            facts_prefixes = []
            for prefix, ns in self.root.nsmap.items():
                if (
                    "http://www.eba.europa.eu/xbrl/crr/dict/met" in ns
                    or "http://www.eba.europa.eu/xbrl/crr/dict/dim" in ns
                ):
                    facts_prefixes.append(prefix)

            if child.prefix in facts_prefixes:
                fact = Fact(child)
                if fact.unit == self._base_currency_unit:
                    self._decimals_monetary_set.add(fact.decimals)
                if fact.unit == self._pure_unit:
                    self._decimals_percentage_set.add(fact.decimals)
                facts.append(Fact(child))

        self._facts = facts
        self.get_facts_list_dict()
        self.to_df()

    def get_module_code(self) -> None:
        """Extracts the module name from the XML instance file."""
        for child in self.root:
            if child.prefix == "link":
                value: str = child.attrib["{http://www.w3.org/1999/xlink}href"]  # type: ignore[assignment]
                self._module_ref = value
                split_value = value.split("/mod/")[1].split(".xsd")[0]
                self._module_code = split_value
                break

    def get_filing_indicators(self) -> None:
        """Extracts `filing <https://www.xbrl.org/guidance/xbrl-glossary/#2-other-terms-in-technical-or-common-use:~:text=data%20point.-,Filing,-The%20file%20or>`_
        indicators from the XML instance file.
        """
        node_f_indicators = self.root.find(
            "{http://www.eurofiling.info/xbrl/ext/filing-indicators}fIndicators"
        )
        if node_f_indicators is None:
            return
        all_ind = node_f_indicators.findall(
            "{http://www.eurofiling.info/xbrl/ext/filing-indicators}filingIndicator"
        )
        filing_indicators: List[FilingIndicator] = []
        for fil_ind in all_ind:
            filing_indicators.append(FilingIndicator(fil_ind))

        if filing_indicators:
            self._filing_indicators = filing_indicators
            first_fil_ind = filing_indicators[0]
            if self._contexts and first_fil_ind.context in self._contexts:
                fil_ind_context = self._contexts[first_fil_ind.context]
                self._entity = fil_ind_context.entity
                self._period = fil_ind_context.period

    def get_units(self) -> None:
        """Extracts the base currency of the instance"""
        units: Dict[str, str] = {}
        for unit in self.root.findall("{http://www.xbrl.org/2003/instance}unit"):
            unit_name: str = unit.attrib["id"]  # type: ignore[assignment]
            measure = unit.find("{http://www.xbrl.org/2003/instance}measure")
            if measure is None or measure.text is None:
                continue
            unit_value: str = measure.text
            ##Workaround
            # We are assuming that currencies always start as iso4217
            if unit_value[:8].lower() == "iso4217:":  # noqa: SIM102
                ##Workaround
                # For the XBRL-CSV, we assume one currency for the whole instance
                # We take the first currency we find, because we assume that,
                # in the current EBA architecture, all the facts have the same currency
                if self._base_currency is None:
                    self._base_currency = unit_value
                    self._base_currency_unit = unit_name
            if unit_value in ["xbrli:pure", "pure"]:
                self._pure_unit = unit_name
            units[unit_name] = unit_value

        self._units = units

    # TODO: For this to be more efficient, check it once all contexts are loaded.
    def validate_entity(self, context: str) -> None:
        """Validates that a certain :obj:`Context <xbridge.xml_instance.Context>`
        does not add a second entity
        (i.e., the instance contains data only for one entity).
        """
        if getattr(self, "_entity", None) is None:
            self._entity = context
        if self._entity != context:
            raise ValueError("The instance has more than one entity")

    @property
    def decimals_percentage(self) -> Optional[int]:
        """Returns the single value for percentage values in the instance."""
        if not self._decimals_percentage_set:
            return None
        max_val = (
            max(int(d) for d in self._decimals_percentage_set if d and d.isdigit())
            if any(d and d.isdigit() for d in self._decimals_percentage_set)
            else None
        )
        return max_val

    @property
    def decimals_monetary(self) -> Optional[int]:
        """Returns the single value for monetary values in the instance."""
        if len(self._decimals_monetary_set) == 0:
            return None
        decimal_values = [d for d in self._decimals_monetary_set if d]
        max_reported = max(decimal_values)
        if max_reported:
            # Workaround
            # We are assuming that the maximum number of decimals for monetary values
            # is 2, in practice. We found cases with higher numbers for some values,
            # and that causes problems in the CSV output, because the maximum was
            # applying.
            return min(int(max_reported), 2)
        return None


class Scenario:
    """Class for the scenario of a :obj:`Context <xbridge.xml_instance.Context>`.
    It parses the XML node with the
    scenario created and gets a value that fits with the scenario created from the XML node.
    """

    def __init__(self, scenario_xml: etree._Element | None = None) -> None:
        self.scenario_xml = scenario_xml
        self.dimensions: Dict[str, str] = {}

        self.parse()

    def parse(self) -> None:
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
                dimension_raw = child.attrib.get("dimension")
                if not dimension_raw:
                    continue
                dimension = dimension_raw.split(":")[1]
                value = self.get_value(child)
                value = value.split(":")[1] if ":" in value else value
                self.dimensions[dimension] = value

    @staticmethod
    def get_value(child_scenario: etree._Element) -> str:
        """Gets the value for `dimension <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=a%20taxonomy.-,Dimension,-A%20qualifying%20characteristic>`_
        from the XML node with the scenario.
        """
        if list(child_scenario):
            first_child = list(child_scenario)[0]
            return first_child.text or ""
        return child_scenario.text or ""

    def __repr__(self) -> str:
        return f"Scenario(dimensions={self.dimensions})"


class Context:
    """Context class.

    Class for the context of a
    `fact <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=accounting%20standards%20body.-,Fact,-A%20fact%20is>`_.
    Its attributes are id, entity, period and scenario.

    Returns a dictionary which has as keys the entity and the period.
    """

    def __init__(self, context_xml: etree._Element) -> None:
        self.context_xml = context_xml

        self._id: Optional[str] = None
        self._entity: Optional[str] = None
        self._period: Optional[str] = None
        self._scenario: Optional[Scenario] = None

        self.parse()

    @property
    def id(self) -> str:
        """Returns the id of the :obj:`Context <xbridge.xml_instance.Context>`."""
        if self._id is None:
            raise ValueError("No context ID found.")
        return self._id

    @property
    def entity(self) -> str:
        """Returns the entity of the :obj:`Context <xbridge.xml_instance.Context>`."""
        if self._entity is None:
            raise ValueError("No entity found in Context.")
        return self._entity

    @property
    def period(self) -> str:
        """Returns the period of the :obj:`Context <xbridge.xml_instance.Context>`."""
        if self._period is None:
            raise ValueError("No period found in Context.")
        return self._period

    @property
    def scenario(self) -> Scenario:
        """Returns the scenario of the :obj:`Context <xbridge.xml_instance.Context>`."""
        if self._scenario is None:
            raise ValueError("No scenario found in Context.")
        return self._scenario

    def parse(self) -> None:
        """Parses the XML node with the :obj:`Context <xbridge.xml_instance.Context>`."""
        self._id = self.context_xml.attrib["id"]  # type: ignore[assignment]

        entity_elem = self.context_xml.find("{http://www.xbrl.org/2003/instance}entity")
        if entity_elem is not None:
            ident = entity_elem.find("{http://www.xbrl.org/2003/instance}identifier")
            if ident is not None and ident.text is not None:
                self._entity = ident.text

        period_elem = self.context_xml.find("{http://www.xbrl.org/2003/instance}period")
        if period_elem is not None:
            instant = period_elem.find("{http://www.xbrl.org/2003/instance}instant")
            if instant is not None and instant.text is not None:
                self._period = instant.text

        scenario_elem = self.context_xml.find("{http://www.xbrl.org/2003/instance}scenario")
        self._scenario = Scenario(scenario_elem)

    def __repr__(self) -> str:
        return (
            f"Context(id={self.id}, entity={self.entity}, "
            f"period={self.period}, scenario={self.scenario})"
        )

    def __dict__(self) -> Dict[str, Any]:  # type: ignore[override]
        result = {"entity": self.entity, "period": self.period}

        for key, value in self.scenario.dimensions.items():
            result[key] = value

        return result


class Fact:
    """Class for the `facts
    <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=accounting%20standards%20body.-,Fact,-A%20fact%20is>`_
    of an instance. Returns the facts of the instance with information such as the value,
    its decimals, :obj:`Context <xbridge.xml_instance.Context>` and units.
    """

    def __init__(self, fact_xml: etree._Element) -> None:
        self.fact_xml = fact_xml
        self.metric: str | None = None
        self.value: str | None = None
        self.decimals: str | None = None
        self.context: str | None = None
        self.unit: str | None = None

        self.parse()

    def parse(self) -> None:
        """Parse the XML node with the `fact <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=accounting%20standards%20body.-,Fact,-A%20fact%20is>`_."""
        self.metric = self.fact_xml.tag
        self.value = self.fact_xml.text
        self.decimals = self.fact_xml.attrib.get("decimals")
        self.context = self.fact_xml.attrib.get("contextRef")
        self.unit = self.fact_xml.attrib.get("unitRef")

    def __dict__(self) -> Dict[str, Any]:  # type: ignore[override]
        metric_clean = ""
        if self.metric:
            metric_clean = self.metric.split("}")[1] if "}" in self.metric else self.metric

        return {
            "metric": metric_clean,
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
    """Class for the `filing
    <https://www.xbrl.org/guidance/xbrl-glossary/#2-other-terms-in-technical-or-common-use:~:
    text=data%20point.-,Filing,-The%20file%20or>`_ indicator of an instance.
    Returns the filing Indicator value and also a table with a
    :obj:`Context <xbridge.xml_instance.Context>`
    """

    def __init__(self, filing_indicator_xml: etree._Element) -> None:
        self.filing_indicator_xml = filing_indicator_xml
        self.value: bool | None = None
        self.table: str | None = None
        self.context: str | None = None

        self.parse()

    def parse(self) -> None:
        """Parse the XML node with the filing indicator."""
        value = self.filing_indicator_xml.attrib.get(
            "{http://www.eurofiling.info/xbrl/ext/filing-indicators}filed"
        )
        if value:
            self.value = value == "true"
        else:
            self.value = True
        self.table = self.filing_indicator_xml.text
        self.context = self.filing_indicator_xml.attrib.get("contextRef")

    def __dict__(self) -> Dict[str, Any]:  # type: ignore[override]
        return {
            "value": self.value,
            "table": self.table,
            "context": self.context,
        }

    def __repr__(self) -> str:
        return f"FilingIndicator(value={self.value}, table={self.table}, context={self.context})"
