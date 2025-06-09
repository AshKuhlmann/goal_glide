# Configuration file for the Sphinx documentation builder.

project = 'Goal Glide'
author = 'Goal Glide Developers'

import os
import sys
sys.path.insert(0, os.path.abspath('..'))

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.napoleon']
autodoc_mock_imports = [
    'click',
    'rich',
    'tinydb',
    'requests',
    'apscheduler',
    'notify2',
    'textual',
    'jinja2',
    'pandas',
]

templates_path = ['_templates']
exclude_patterns = []

html_theme = 'alabaster'
