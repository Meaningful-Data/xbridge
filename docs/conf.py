# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
from pathlib import Path

import tomlkit

sys.path.insert(0, os.path.abspath(".."))

# -- Project information -----------------------------------------------------

# The EBA Taxonomy version
rst_prolog = (
    """
.. |eba_version| replace::
 """
    + "4.2"
)

# Get project information from pyproject.toml
version: str = "unknown"
project: str = "eba-xbridge"
description: str = "XBRL-XML to XBRL-CSV converter for EBA Taxonomy (version 4.2)"
copyright: str = "2025 MeaningfulData"
# adopt path to your pyproject.toml
pyproject_toml_file = Path(__file__).parent / "pyproject.toml"
if pyproject_toml_file.exists() and pyproject_toml_file.is_file():
    with pyproject_toml_file.open("r", encoding="utf-8") as f:
        data_toml = tomlkit.load(f)
    tool_section = data_toml.get("tool")
    if tool_section and isinstance(tool_section, dict):
        poetry_section = tool_section.get("poetry")
        if poetry_section and isinstance(poetry_section, dict):
            project = str(poetry_section.get("name", project))
            version = str(poetry_section.get("version", version))
            description = str(poetry_section.get("description", description))

# Other project information

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx_rtd_theme",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosectionlabel",
]

autosectionlabel_prefix_document = True

html_show_sourcelink = False

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#

html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "analytics_id": "",
    "logo_only": False,
    "prev_next_buttons_location": "",
    "style_external_links": True,
    "vcs_pageview_mode": "blob",
    "collapse_navigation": False,
    "sticky_navigation": False,
    "navigation_depth": 4,
    "includehidden": False,
    "titles_only": False,
}
