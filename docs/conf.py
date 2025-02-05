# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

import os
import sys
current_dir = os.path.dirname(__file__)
target_dir = os.path.abspath(os.path.join(current_dir, "../src"))
sys.path.insert(0, target_dir)

# -- Project information -----------------------------------------------------

project = 'LG4X-V2'
copyright = '2022-2025, Julian A. Hochhaus'
author = 'Julian A. Hochhaus'

# The full version, including alpha/beta/rc tags
release = "4.1.1"

sys.path.append(os.path.abspath('exts'))
numfig = True

# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx_toolbox.collapse',
    'sphinx_copybutton',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',  # Add this line to enable intersphinx support
]

napoleon_google_docstring = False

templates_path = ['_templates']

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_logo = "src/logos/logo.png"
html_theme_options = {
    'logo_only': True,
}
html_short_title = project  # Use project variable for consistency
html_favicon = "src/logos/icon.ico"
html_static_path = []

# Enable search functionality (this should be enabled by default)
html_search_language='en'  # Specify language if needed

# Add after importing necessary libraries



# Ensure search functionality is enabled
html_search = True  # Generally true by default; add for clarity