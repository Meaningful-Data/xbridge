"""Module with the classes related to XBRL-XML instance files."""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, Dict, List, Optional, Union
from zipfile import ZipFile

import pandas as pd
from lxml import etree

from xbridge.exceptions import (
    FilingIndicatorValueError,
    IdentifierPrefixWarning,
    SchemaRefValueError,
)

# Cache namespace → CSV prefix derivations to avoid repeated string work during parse
_namespace_prefix_cache: Dict[str, str] = {}


def _derive_csv_prefix(namespace_uri: str) -> Optional[str]:
    """Derive the fixed CSV prefix from a namespace URI using the EBA convention."""
    if not namespace_uri:
        return None

    cached = _namespace_prefix_cache.get(namespace_uri)
    if cached is not None:
        return cached

    cleaned = namespace_uri.rstrip("#/")
    if "#" in namespace_uri:
        segment = namespace_uri.rsplit("#", 1)[-1]
    else:
        segment = cleaned.rsplit("/", 1)[-1] if "/" in cleaned else cleaned

    if not segment:
        return None

    prefix = f"eba_{segment}"
    _namespace_prefix_cache[namespace_uri] = prefix
    return prefix


def _derive_metric_prefix(namespace_uri: str) -> Optional[str]:
    """
    Derive the CSV prefix for metrics from a namespace URI.

    For metrics, we preserve version suffixes in the prefix:
    - http://www.eba.europa.eu/xbrl/crr/dict/met -> eba_met
    - http://www.eba.europa.eu/xbrl/crr/dict/met/3.5 -> eba_met_3.5
    - http://www.eba.europa.eu/xbrl/crr/dict/met/4.0 -> eba_met_4.0
    """
    if not namespace_uri:
        return None

    cached = _namespace_prefix_cache.get(f"metric:{namespace_uri}")
    if cached is not None:
        return cached

    cleaned = namespace_uri.rstrip("#/")

    # Split the URI into path segments
    segments = cleaned.split("/")

    # Find the 'met' (metrics) segment and check if there's a version after it
    prefix = None
    for i, segment in enumerate(segments):
        if segment == "met":
            # Check if there's a version suffix (e.g., "3.5", "4.0")
            if i + 1 < len(segments):
                version = segments[i + 1]
                prefix = f"eba_met_{version}"
            else:
                prefix = "eba_met"
            break

    # If we didn't find 'met', fall back to the standard logic
    if prefix is None:
        prefix = _derive_csv_prefix(namespace_uri)

    if prefix:
        _namespace_prefix_cache[f"metric:{namespace_uri}"] = prefix

    return prefix


def _normalize_namespaced_value(
    value: Optional[str], nsmap: Dict[Optional[str], str]
) -> Optional[str]:
    """
    Normalize a namespaced value (e.g., 'dom:qAE' or '{uri}qAE') to the CSV prefix convention.
    Returns the original value if no namespace can be resolved.
    """
    if value is None:
        return None

    # Clark notation: {uri}local
    if value.startswith("{") and "}" in value:
        uri, local = value[1:].split("}", 1)
        derived = _derive_csv_prefix(uri)
        return f"{derived}:{local}" if derived else value

    # Prefixed notation: prefix:local
    if ":" in value:
        potential_prefix, local = value.split(":", 1)
        namespace_uri = nsmap.get(potential_prefix)
        if namespace_uri:
            derived = _derive_csv_prefix(namespace_uri)
            return f"{derived}:{local}" if derived else value

    return value


def _normalize_metric_value(value: Optional[str], nsmap: Dict[Optional[str], str]) -> Optional[str]:
    """
    Normalize a metric namespaced value to the CSV prefix convention.
    For metrics, we preserve version suffixes (e.g., eba_met_3.5, eba_met_4.0).
    Returns the original value if no namespace can be resolved.
    """
    if value is None:
        return None

    # Clark notation: {uri}local
    if value.startswith("{") and "}" in value:
        uri, local = value[1:].split("}", 1)
        derived = _derive_metric_prefix(uri)
        return f"{derived}:{local}" if derived else value

    # Prefixed notation: prefix:local
    if ":" in value:
        potential_prefix, local = value.split(":", 1)
        namespace_uri = nsmap.get(potential_prefix)
        if namespace_uri:
            derived = _derive_metric_prefix(namespace_uri)
            return f"{derived}:{local}" if derived else value

    return value


class Instance:
    """
    Abstract class representing an XBRL instance file.
    Its attributes are the characters contained in the XBRL files.
    """

    @classmethod
    def from_path(cls, path: Union[str, Path]) -> Instance:
        path = Path(path)

        if path.suffix in [".xml", ".xbrl"]:
            return XmlInstance(path)
        elif path.suffix == ".zip":
            return CsvInstance(path)
        else:
            raise ValueError(f"Unsupported file extension: {path.suffix}")

    def __init__(self, path: Optional[Union[str, Path]] = None) -> None:
        if path is None:
            raise ValueError("Must provide a path to XBRL file.")
        try:
            path_str = os.fspath(path)  # acepta str y PathLike
        except TypeError:
            raise TypeError("Unsupported type for 'path' argument.")
        if not isinstance(path_str, str):
            raise TypeError("Unsupported type for 'path' argument.")

        self.path = Path(path)
        self._module_code: Optional[str] = None
        self._module_ref: Optional[str] = None
        self._entity: Optional[str] = None
        self._period: Optional[str] = None
        self._filing_indicators: Optional[List[FilingIndicator]] = None
        self._base_currency: Optional[str] = None
        self._units: Optional[Dict[str, str]] = {}
        self._base_currency_unit: Optional[str] = None
        self._pure_unit: Optional[str] = None
        self._integer_unit: Optional[str] = None
        self._identifier_prefix: Optional[str] = None
        self.root: Optional[etree._Element] = None
        self._contexts: Optional[Dict[str, Context]] = None
        self._facts: Optional[List[Fact]] = None
        self._facts_list_dict: Optional[List[Dict[str, Any]]] = None
        self._df: Optional[pd.DataFrame] = None
        self._table_files: Optional[set[Path]] = None
        self._root_folder: Optional[str] = None
        self._report_file: Optional[Path] = None

    @property
    def namespaces(self) -> Dict[Optional[str], str]:
        """Returns the `namespaces
        <https://www.xbrl.org/guidance/xbrl-glossary/#2-other-terms-in-technical-or
        -common-use:~:text=calculation%20tree.-,Namespace,-A%20namespace%20>`_
        is of the instance file.
        """
        if self.root is None:
            raise AttributeError("XML root not loaded.")
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
    def table_files(self) -> set[Path]:
        """
        Returns the :obj:`TableFiles <xbridge.xml_instance.TableFiles>`
        """
        return set()

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
        df = pd.DataFrame(self.facts_list_dict)
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

        if self._identifier_prefix not in entity_prefix_mapping:
            warnings.warn(
                (
                    f"{self._identifier_prefix} is not a known identifier prefix. "
                    "Default 'rs' will be used."
                ),
                category=IdentifierPrefixWarning,
                stacklevel=2,
            )
            return "rs"

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

    @property
    def temp_dir_path(self) -> Optional[Path]:
        return None

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
        except SchemaRefValueError:
            raise  # Let SchemaRefValueError propagate as-is
        except FilingIndicatorValueError:
            raise  # Let FilingIndicatorValueError propagate as-is
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
        if self.root is None:
            raise AttributeError("XML root not loaded.")

        contexts: Dict[str, Context] = {}
        namespaces: Dict[str, str] = {key or "": value for key, value in self.namespaces.items()}
        for context in self.root.findall(
            "{http://www.xbrl.org/2003/instance}context",
            namespaces,
        ):
            context_object = Context(context)
            contexts[context_object.id] = context_object

        self._contexts = contexts

        first_ctx = self.root.find("{http://www.xbrl.org/2003/instance}context", namespaces)
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
        if self.root is None:
            raise AttributeError("XML root not loaded.")

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
                facts.append(Fact(child))

        self._facts = facts
        self.get_facts_list_dict()
        self.to_df()

    def get_module_code(self) -> None:
        """Extracts the module name from the XML instance file."""
        if self.root is None:
            raise AttributeError("XML root not loaded.")

        schema_refs = []
        for child in self.root:
            if child.prefix == "link":
                href_attr = "{http://www.w3.org/1999/xlink}href"
                if href_attr not in child.attrib:
                    continue
                raw_value = child.attrib[href_attr]
                value = str(raw_value)
                schema_refs.append(value)

        # Validate that only one schemaRef exists
        if len(schema_refs) == 0:
            return  # No schema reference found, module_ref will remain None

        if len(schema_refs) > 1:
            raise SchemaRefValueError(
                (
                    "Multiple schemaRef elements found in the XBRL instance. "
                    f"Only one schemaRef is expected, but {len(schema_refs)} "
                    f"were found: {schema_refs}. "
                    "This may indicate an invalid XBRL-XML file."
                ),
                offending_value=schema_refs,
            )

        # Process the single schema reference
        value = schema_refs[0]
        self._module_ref = value

        # Validate href format and extract module code
        if "/mod/" not in value:
            raise SchemaRefValueError(
                (
                    "Invalid href format in schemaRef. Expected href to contain '/mod/' "
                    f"but got: '{value}'. Please verify the XBRL-XML file contains a "
                    "valid schema reference."
                ),
                offending_value=value,
            )

        split_parts = value.split("/mod/")
        if len(split_parts) < 2:
            raise SchemaRefValueError(
                (
                    "Invalid href format in schemaRef. Could not extract module name "
                    f"from: '{value}'. Expected format: 'http://.../mod/[module_name].xsd'"
                ),
                offending_value=value,
            )

        module_part = split_parts[1]
        if ".xsd" not in module_part:
            raise SchemaRefValueError(
                (
                    "Invalid href format in schemaRef. Expected href to end with '.xsd' "
                    f"but got: '{value}'. Please verify the XBRL-XML file contains a valid "
                    "schema reference."
                ),
                offending_value=value,
            )

        xsd_split = module_part.split(".xsd")
        self._module_code = xsd_split[0]

    def get_filing_indicators(self) -> None:
        """Extracts `filing <https://www.xbrl.org/guidance/xbrl-glossary/#2-other-terms-in-technical-or-common-use:~:text=data%20point.-,Filing,-The%20file%20or>`_
        indicators from the XML instance file.
        """
        if self.root is None:
            raise AttributeError("XML root not loaded.")

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
        if self.root is None:
            raise AttributeError("XML root not loaded.")

        units: Dict[str, str] = {}
        for unit in self.root.findall("{http://www.xbrl.org/2003/instance}unit"):
            unit_id = unit.attrib["id"]
            unit_name = str(unit_id)
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
            if unit_value in ["xbrli:integer", "integer"]:
                self._integer_unit = unit_name
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


class CsvInstance(Instance):
    """
    Class representing an XBRL CSV instance file.
    Its attributes are the characters contained in the XBRL files.
    Each property returns one of these attributes.
    :param path: File path to be used
    """

    def __init__(self, path: Union[str, Path]) -> None:
        super().__init__(path)

        self._temp_dir_path: Optional[Path] = None
        self._parameters_file: Optional[Path] = None
        self._filing_indicators_file: Optional[Path] = None
        self._table_files: Optional[set[Path]] = None

        self.parse()

    @property
    def parameters_file(self) -> Optional[Path]:
        """Returns the parameters file."""
        return self._parameters_file

    @property
    def filing_indicators_file(self) -> Optional[Path]:
        """Returns the filing indicators file."""
        return self._filing_indicators_file

    @property
    def temp_dir_path(self) -> Optional[Path]:
        """Returns the temporary directory path."""
        return self._temp_dir_path

    @property
    def table_files(self) -> set[Path]:
        """Returns the table files."""
        return self._table_files or set()

    @property
    def root_folder(self) -> str:
        return getattr(self, "_root_folder", Path(self.path).stem)

    def parse(self) -> None:
        """Parses the XBRL-CSV into the library objects."""
        temp_dir = mkdtemp()
        tmp = Path(temp_dir)

        with ZipFile(self.path, "r") as zip_ref:
            zip_ref.extractall(tmp)

        inner_dirs = [p for p in tmp.iterdir() if p.is_dir()]
        base = inner_dirs[0] if len(inner_dirs) == 1 else tmp

        self._root_folder = base.name if base != tmp else self.path.stem
        self._temp_dir_path = base

        with ZipFile(self.path, "r") as zip_ref:
            zip_ref.extractall(self._temp_dir_path)

        self._report_file = base / "reports" / "report.json"
        with open(self._report_file, "r") as f:
            extends = json.load(f)["documentInfo"]["extends"]
            if len(extends) > 1:
                raise ValueError("More than one extension in the report.json file")
            mod = extends[0]
            if mod.endswith(".json"):
                mod = mod.replace(".json", ".xsd")
            if mod.startswith("http://") or mod.startswith("https://"):
                self._module_ref = mod
            else:
                self._module_ref = "http://" + mod.lstrip("/")

        self._parameters_file = base / "reports" / "parameters.csv"
        self._filing_indicators_file = base / "reports" / "FilingIndicators.csv"
        reports_dir = base / "reports"
        self._table_files = set(reports_dir.glob("*.csv")) - {
            self._parameters_file,
            self._filing_indicators_file,
        }


class XmlInstance(Instance):
    """
    Class representing an XBRL XML instance file.
    Its attributes are the characters contained in the XBRL files.
    Each property returns one of these attributes.

    :param path: File path to be used

    """

    def __init__(self, path: Union[str, Path]) -> None:
        super().__init__(path)

        self._facts_list_dict = None
        self._facts = None
        self._contexts = None
        self._df = None

        self.root = etree.parse(self.path).getroot()
        self.parse()

    def parse(self) -> None:
        """Parses the XML file into the library objects."""
        try:
            self.root = etree.parse(self.path).getroot()
            self.get_units()
            self.get_contexts()
            self.get_facts()
            self.get_module_code()
            self.get_filing_indicators()
        except etree.XMLSyntaxError:
            raise ValueError("Invalid XML format")
        except SchemaRefValueError:
            raise  # Let SchemaRefValueError propagate as-is
        except FilingIndicatorValueError:
            raise  # Let FilingIndicatorValueError propagate as-is
        except Exception as e:
            raise ValueError(f"Error parsing instance: {str(e)}")

        # TODO: Validate that all the assumptions about the EBA instances are correct
        # Should be an optional parameter (to avoid performance issues when it is known
        # that the assumptions are correct)
        # - Validate that there is only one entity
        # - Validate that there is only one period
        # - Validate that all the facts have the same currency


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
                value = _normalize_namespaced_value(value, child.nsmap) or ""
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
        self._id = str(self.context_xml.attrib["id"])

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
        self.value = _normalize_namespaced_value(self.fact_xml.text, self.fact_xml.nsmap)
        self.decimals = self.fact_xml.attrib.get("decimals")
        self.context = self.fact_xml.attrib.get("contextRef")
        self.unit = self.fact_xml.attrib.get("unitRef")

    def __dict__(self) -> Dict[str, Any]:  # type: ignore[override]
        metric_clean = ""
        if self.metric:
            # Normalize metric using metric-specific logic that preserves version suffixes
            metric_clean = _normalize_metric_value(self.metric, self.fact_xml.nsmap) or ""
            # If still in Clark notation, extract the local name
            if metric_clean.startswith("{") and "}" in metric_clean:
                metric_clean = metric_clean.split("}", 1)[1]

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
        """Parse the XML node with the filing indicator.

        Raises:
            FilingIndicatorValueError: If the filed attribute is not "true", "false", "0", or "1"
        """
        value = self.filing_indicator_xml.attrib.get(
            "{http://www.eurofiling.info/xbrl/ext/filing-indicators}filed"
        )
        if value:
            if value not in ("true", "false", "0", "1"):
                raise FilingIndicatorValueError(
                    f"Invalid filing indicator value: '{value}'. "
                    f"The 'filed' attribute must be either 'true', 'false', '0', or '1'.",
                    offending_value=value,
                )
            self.value = value in ("true", "1")
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
