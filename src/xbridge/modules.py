"""Module with the classes related to modules, containing the "instructions" for the conversion."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import urljoin, urlparse
from zipfile import ZipFile

import pandas as pd


class Module:
    """Class representing an XBRL Module.

    It has attributes like code, url, and tables whose main function is to operate with the
    module and return properties like a specific table from the JSON file used as input,
    an object, a dictionary using the attributes as keys, a module object from a part of
    preprocessed JSON file and the variables that are present in it.

    It is used when taxonomies are loaded to collect the information associated to the tables
    belonging to the module.

    :param code: The code of the XBRL module.

    :param url: The module reference within the taxonomy.

    :param tables: The tables that form the module.

    """

    def __init__(
        self,
        code: Optional[str] = None,
        url: Optional[str] = None,
        tables: Optional[List[Table]] = None,
    ) -> None:
        self.code: Optional[str] = code
        self.url: Optional[str] = url
        self._tables: List[Table] = tables if tables is not None else []
        self.taxonomy_module_path: Optional[str] = None
        self.module_json_setup: Optional[Dict[str, Any]] = None

        if url is None:
            url = ""

        url_split = url.split("/")

        if len(url_split) == 12:
            self.taxonomy_architecture = "2.0"
            self.framework_code = url_split[7]
            self.framework_version = f"{url_split[8]}_{url_split[9]}"
        elif len(url_split) == 13:
            self.taxonomy_architecture = "1.0"
            self.framework_code = url_split[8]
            self.framework_version = f"{url_split[9]}_{url_split[10]}"

        else:
            raise ValueError(f"Invalid taxonomy architecture: {len(url_split)}")

    @property
    def dim_dom_file_name(self) -> str:
        if self.taxonomy_architecture == "1.0":
            return "dim_dom_mapping.json"
        elif self.taxonomy_architecture == "2.0":
            return f"dim_dom_mapping_{self.framework_version.split('_')[-1]}.json"
        else:
            raise ValueError(f"Invalid taxonomy architecture: {self.taxonomy_architecture}")

    @property
    def tables(self) -> List[Table]:
        """Returns the :obj:`tables <xbridge.taxonomy.Table>` defined in the JSON file for the
        :obj:`module <xbridge.taxonomy.Module>`"""
        return self._tables

    @property
    def architecture(self) -> str:
        return self.tables[0].architecture

    @staticmethod
    def is_relative_url(url: str) -> bool:
        parsed_url = urlparse(url)
        # A URL is considered relative if it lacks a scheme and a netloc
        return not parsed_url.scheme and not parsed_url.netloc

    def _get_all_table_paths(self) -> None:
        """Returns the path to the table in the taxonomy"""
        if not self.module_json_setup:
            return
        tables_paths = []

        original_path = self.taxonomy_module_path

        extends = self.module_json_setup["documentInfo"].get("extends", [])

        for table in extends:
            if self.is_relative_url(table) and original_path is not None:
                tables_paths.append(urljoin(original_path, table))
            else:
                tables_paths.append(table)

        self.tables_paths = tables_paths

    def get_module_setup(self, zip_file: ZipFile) -> None:
        """Reads the json entry point for the module and extracts the setup"""
        if not self.taxonomy_module_path:
            return
        bin_read = zip_file.read(self.taxonomy_module_path)
        self.module_json_setup = json.loads(bin_read.decode("utf-8"))

    def extract_tables(self, zip_file: ZipFile) -> None:
        """Extracts the :obj:`tables <xbridge.taxonomy.Table>` in the JSON files for the
        :obj:`modules <xbridge.taxonomy.Module>` in the taxonomy"""
        self._tables = []

        for table_path in self.tables_paths:
            if "FilingIndicators.json" in table_path or "FootNotes.json" in table_path:
                continue
            table = Table.from_taxonomy(zip_file, table_path, self.module_json_setup["tables"])  # type: ignore[index]

            self.tables.append(table)

    def get_table(self, table_code: str) -> Table:
        """Returns a :obj:`table <xbridge.taxonomy.Table>` object with the given code"""
        for table in self.tables:
            if getattr(table, "code_name", "") == table_code:
                return table
        raise ValueError(f"Table {table_code} not found in module {self.code}")

    def to_dict(self) -> Dict[str, Any]:
        """Returns a dictionary"""
        return {
            "code": self.code,
            "url": self.url,
            "architecture": self.architecture,
            "tables": [tab.to_dict() for tab in self.tables],
        }

    @classmethod
    def from_taxonomy(cls, zip_file: ZipFile, json_file_path: str) -> Module:
        """Returns a :obj:`module <xbridge.taxonomy.Module>` object from a part of the JSON file"""
        module_code = Path(json_file_path).stem

        obj = cls(code=module_code, url=f"http://{json_file_path}")

        obj.taxonomy_module_path = json_file_path

        obj.get_module_setup(zip_file)
        obj._get_all_table_paths()
        obj.extract_tables(zip_file)

        return obj

    @classmethod
    def from_serialized(cls, input_path: Union[str, Path]) -> Module:
        """Returns a :obj:`module <xbridge.taxonomy.Module>` object from a JSON file"""
        input_path = input_path if isinstance(input_path, Path) else Path(input_path)
        with open(input_path, "r", encoding="UTF-8") as fl:
            module_dict = json.load(fl)

        tables = module_dict.pop("tables")
        tables = [Table.from_dict(table) for table in tables]
        module_dict.pop("architecture")

        obj = cls(**module_dict, tables=tables)

        return obj

    @property
    def variables_location(self) -> Dict[str, List[str]]:
        """Returns a dictionary with the :obj:`variables <xbridge.taxonomy.Variable>`
        and the :obj:`tables <xbridge.taxonomy.Table>` where they are present
        """
        variables = {}
        for table in self.tables:
            if table.code is None:
                continue
            for variable in table.variables:
                if variable.code is None:
                    continue
                if variable.code not in variables:
                    variables[variable.code] = [table.code]
                else:
                    variables[variable.code].append(table.code)
        return variables

    @property
    def repeated_variables(self) -> Dict[str, List[str]]:
        """Returns a dictionary with the :obj:`variables <xbridge.taxonomy.Variable>` and the
        :obj:`tables <xbridge.taxonomy.Table>` where they are present, if they are repeated
        """
        result: Dict[str, List[str]] = {}
        for k, v in self.variables_location.items():
            if len(v) > 1:
                result[k] = v
        return result

    def __repr__(self) -> str:
        return f"<Module - {self.code}>"


class Table:
    """Class representing an XBRL :obj:`table <xbridge.taxonomy.Table>` as defined in the JSON file.

    Its properties allow to return open keys, variables and attributes
    from the :obj:`table <xbridge.taxonomy.Table>`.
    It can also generate a
    variable dataframe or work with one already created.
    Finally, it can return a dictionary using its attributes or a
    :obj:`Table <xbridge.taxonomy.Table>` object from the preprocessed JSON file.

    It is used when module is loaded to collect the information associated
    to the variables and open keys belonging to the table.

    :param code: The code of the table.

    :param url: The table reference within the module.

    :param open_keys: Open key contained in the table.

    :param variables: the variables that belongs to the table.

    :param attributes: attributes related to the variables that can be extracted from the table.

    :param input_zip_path: Path to the file used as table.
    """

    def __init__(
        self,
        code: Optional[str] = None,
        url: Optional[str] = None,
        open_keys: Optional[List[str]] = None,
        variables: Optional[List[Variable]] = None,
        attributes: Optional[List[str]] = None,
        input_zip_path: Optional[str] = None,
        architecture: Optional[str] = None,
        columns: Optional[List[dict[str, Any]]] = None,
        open_keys_mapping: Optional[Dict[str, str]] = None,
    ) -> None:
        self.table_zip_path: Optional[str] = input_zip_path
        self.code: Optional[str] = code
        self.url: Optional[str] = url
        self._open_keys: List[str] = open_keys if open_keys else []
        self._variables: List[Variable] = variables if variables else []
        self._attributes: List[str] = attributes if attributes else []
        self._variable_df: Optional[pd.DataFrame] = None
        self._open_keys_mapping: Dict[str, str] = open_keys_mapping if open_keys_mapping else {}
        self.columns: List[dict[str, Any]] = columns if columns else []
        self.architecture: str = architecture if architecture else "datapoints"
        self.table_setup_json: Dict[str, Any] = {}

    @property
    def open_keys(self) -> List[str]:
        """Returns the open keys for the :obj:`table <xbridge.taxonomy.Table>`"""
        return self._open_keys

    @property
    def variables(self) -> List[Variable]:
        """Returns the :obj:`variable <xbridge.taxonomy.Variable>` for the
        :obj:`table <xbridge.taxonomy.Table>`"""
        return self._variables

    @property
    def attributes(self) -> List[str]:
        """Returns the attributes for the :obj:`table <xbridge.taxonomy.Table>`"""
        return self._attributes

    @property
    def variable_columns(self) -> Set[str]:
        """Returns the columns for the :obj:`variable <xbridge.taxonomy.Variable>` dataframe"""
        if self.variable_df is None:
            return set()
        cols = set(self.variable_df.columns)
        cols.remove("datapoint")
        return cols

    @property
    def variable_df(self) -> Optional[pd.DataFrame]:
        """Returns a dataframe with the :obj:`variable <xbridge.taxonomy.Variable>`
        and extensional context

        """
        return self._variable_df

    def generate_variable_df(self) -> None:
        """Returns a dataframe with the :obj:`variable <xbridge.taxonomy.Variable>`
        and extensional context"""
        variables = []

        if self.architecture == "datapoints":
            for variable in self.variables:
                variable_info = {}
                for dim_k, dim_v in variable.dimensions.items():
                    if dim_k not in ("unit", "decimals"):
                        variable_info[dim_k] = dim_v.split(":")[1]
                if "concept" in variable.dimensions:
                    variable_info["metric"] = variable.dimensions["concept"].split(":")[1]
                    del variable_info["concept"]

                if variable.code is None:
                    continue

                variable_info["datapoint"] = variable.code
                variables.append(copy.copy(variable_info))
        elif self.architecture == "headers":
            for column in self.columns:
                variable_info = {"datapoint": column["variable_id"]}
                if "dimensions" in column:
                    for dim_k, dim_v in column["dimensions"].items():
                        if dim_k == "concept":
                            variable_info["metric"] = dim_v.split(":")[1]
                        elif dim_k not in ("unit", "decimals"):
                            variable_info[dim_k.split(":")[1]] = dim_v.split(":")[1]
                variables.append(copy.copy(variable_info))

        self._variable_df = pd.DataFrame(variables)

    def extract_open_keys(self) -> None:
        """Extracts the open keys for the :obj:`table <xbridge.taxonomy.Table>`"""
        self._open_keys = []
        self._attributes = []

        table_template = self.table_setup_json["tableTemplates"][self.code]

        if self.architecture == "datapoints":
            for column_name in table_template.get("columns", []):
                if column_name == "unit":
                    self._attributes.append(column_name)

                elif column_name not in ("datapoint", "factValue"):
                    self._open_keys.append(column_name)
        elif self.architecture == "headers":
            for dim_id, column_ref in table_template["dimensions"].items():
                dim_code = dim_id.split(":")[1]
                self._open_keys.append(dim_code)
                self._open_keys_mapping[dim_code] = column_ref[2:]

    def extract_variables(self) -> None:
        """Extract the :obj:`variable <xbridge.taxonomy.Variable>` for the
        :obj:`table <xbridge.taxonomy.Table>`"""
        self._variables = []

        if self.code in self.table_setup_json["tableTemplates"]:
            variables_dict = self.table_setup_json["tableTemplates"][self.code]["columns"][
                "datapoint"
            ]["propertyGroups"]

            for elto_k, elto_v in variables_dict.items():
                datapoint = Variable.from_taxonomy(elto_k, elto_v)
                self._variables.append(datapoint)

    def extract_columns(self) -> List[dict[str, Any]]:
        """Extract the columns for the :obj:`table <xbridge.taxonomy.Table>`"""
        result = []

        for column_code, setup in self.table_setup_json["tableTemplates"][self.code][
            "columns"
        ].items():
            variable_id = (
                setup["eba:documentation"]["KeyVariableID"]
                if "KeyVariableID" in setup["eba:documentation"]
                else setup["eba:documentation"]["FactVariableID"]
            )
            col_setup = {
                "code": column_code,
                "variable_id": variable_id,
            }
            if "dimensions" in setup:
                col_setup["dimensions"] = setup["dimensions"]

            result.append(col_setup)

        return result

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary for the :obj:`table <xbridge.taxonomy.Table>`"""
        result = {
            "code": self.code,
            "url": self.url,
            "architecture": self.architecture,
            "open_keys": self.open_keys,
        }

        if self.architecture == "datapoints":
            result["variables"] = [var.to_dict() for var in self.variables]  # type: ignore[misc]
            result["attributes"] = self.attributes

        elif self.architecture == "headers":
            result["open_keys_mapping"] = self._open_keys_mapping  # type: ignore[assignment]
            result["columns"] = self.columns  # type: ignore[assignment]

        return result

    def get_table_code(self) -> Optional[str]:
        """Returns the code of the table"""
        return self.code

    @staticmethod
    def check_taxonomy_architecture(table_dict: dict[str, Any]) -> str:
        """Checks the taxonomy architecture

        Returns datapoints if the architecture of the
        CSV follows the pattern: datapont,factValue

        Returns headers if the architecture of the
        CSV follows the new DORA pattern: 0010,0020,...
        """
        table_template = table_dict["tableTemplates"]
        if len(table_template) > 1:
            raise ValueError("More than one table template found")
        table_def = table_template[list(table_template.keys())[0]]
        if "datapoint" in table_def["columns"]:
            return "datapoints"
        else:
            return "headers"

    @classmethod
    def from_taxonomy(
        cls, zip_file: ZipFile, table_path: str, module_setup_json: dict[str, Any]
    ) -> Table:
        """Returns a :obj:`table <xbridge.taxonomy.Table>`
        object from a part of the preprocessed JSON file"""
        obj = cls()
        obj.table_zip_path = table_path

        bin_read = zip_file.read(table_path)
        obj.table_setup_json = json.loads(bin_read.decode("utf-8"))

        templates = obj.table_setup_json["tableTemplates"]
        if len(templates) > 1:
            raise ValueError(f"More than one table template found in {table_path}")
        obj.code = list(templates.keys())[0]

        architecture = cls.check_taxonomy_architecture(obj.table_setup_json)
        obj.architecture = architecture

        for table_setup in module_setup_json.values():
            if table_setup["template"] == obj.code:
                obj.url = table_setup["url"]

        obj.extract_open_keys()

        if architecture == "datapoints":
            obj.extract_variables()
        elif architecture == "headers":
            obj.columns = obj.extract_columns()

        return obj

    @classmethod
    def from_dict(cls, table_dict: dict[str, Any]) -> Table:
        """Returns a :obj:`table <xbridge.taxonomy.Table>` object from a dictionary"""
        if table_dict["architecture"] == "datapoints":
            variables = table_dict.pop("variables")
            variables = [Variable.from_dict(variable) for variable in variables]

            obj = cls(**table_dict, variables=variables)
            obj.generate_variable_df()
        elif table_dict["architecture"] == "headers":
            obj = cls(**table_dict)
            obj.generate_variable_df()

        return obj

    def __repr__(self) -> str:
        return f"<Table - {self.code}>"


class Variable:
    """Class representing a variable as represented in the JSON files.

    Can return or extract the
    `dimension <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=a%20taxonomy.-,Dimension,-A%20qualifying%20characteristic>`_
    of the :obj:`variable <xbridge.taxonomy.Variable>`,
    create a dictionary using its attributes as keys or return a variable object from the
    preprocessed JSON file.

    :param code: The code of the variable.

    :param dimensions: the `dimensions <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=a%20taxonomy.-,Dimension,-A%20qualifying%20characteristic>`_
        of the variable.

    :param attributes: The attributes related to the variable.

    """

    def __init__(
        self,
        code: Optional[str] = None,
        dimensions: Optional[dict[str, str]] = None,
        attributes: Any = None,
    ) -> None:
        self.code: Optional[str] = code
        self._dimensions: dict[str, str] = dimensions if dimensions else {}
        self._attributes = attributes

    @property
    def dimensions(self) -> dict[str, str]:
        """Returns the `dimensions
        <https://www.xbrl.org/guidance/xbrl-glossary/#:~:text=a%20taxonomy.
        -,Dimension,-A%20qualifying%20characteristic>`_ of a variable"""
        return self._dimensions

    def extract_dimensions(self, datapoint_dict: dict[str, Any]) -> None:
        """Extracts the `dimensions
        <https://www.xbrl.org/guidance/xbrl-glossary/#:~:
        text=a%20taxonomy.-,Dimension,-A%20qualifying%20characteristic>`_ for the variable"""
        self._dimensions = datapoint_dict.get("dimensions", {})
        if "decimals" in datapoint_dict:
            self._attributes = datapoint_dict["decimals"]

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary with the attributes"""
        return {
            "code": self.code,
            "dimensions": self.dimensions,
            "attributes": self._attributes,
        }

    @classmethod
    def from_taxonomy(cls, variable_id: str, variable_dict: dict[str, Any]) -> Variable:
        """Returns a :obj:`variable <xbridge.taxonomy.Variable>`
        object from a part of the preprocessed JSON file
        """
        obj = cls(code=variable_id)
        obj.extract_dimensions(variable_dict)

        return obj

    @classmethod
    def from_dict(cls, variable_dict: dict[str, Any]) -> Variable:
        """Returns a :obj:`variable <xbridge.taxonomy.Variable>` object from a dictionary"""
        modified_dimensions = {}
        for k, v in variable_dict["dimensions"].items():
            if ":" in k:
                k = k.split(":")[1]
                modified_dimensions[k] = v
            else:
                modified_dimensions[k] = v
        modified_dict = variable_dict.copy()
        modified_dict["dimensions"] = modified_dimensions
        obj = cls(**modified_dict)
        return obj

    def __repr__(self) -> str:
        return f"<Variable - {self.code}>"
