"""Sphinx configuration for SaaS Growth Intelligence Platform."""

project = "SaaS Growth Intelligence Platform"
author = "Vijaya Supreetha Gurrala"
copyright = "2026, Vijaya Supreetha Gurrala"

extensions = [
    "myst_parser",
    "sphinx_copybutton",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

templates_path = ["_templates"]
exclude_patterns = ["_build"]

html_theme = "furo"
html_title = "SaaS Growth Analytics — Docs"
