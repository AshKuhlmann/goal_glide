# Configuration file for the Sphinx documentation builder.

import os
import sys

sys.path.insert(0, os.path.abspath('..'))

project = 'Goal Glide'
author = 'Goal Glide Developers'

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
    'goal_glide.cli',
    'goal_glide.tui',
    'goal_glide.services.pomodoro',
]

templates_path = ['_templates']
exclude_patterns = []

html_theme = 'alabaster'
suppress_warnings = ['autodoc.mocked_object']
