# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

from watcher import objects

objects.register_all()

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('../../'))
sys.path.insert(0, os.path.abspath('../'))
sys.path.insert(0, os.path.abspath('./'))

# -- General configuration ----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'oslo_config.sphinxext',
    'sphinx.ext.viewcode',
    'sphinxcontrib.httpdomain',
    'sphinxcontrib.pecanwsme.rest',
    'stevedore.sphinxext',
    'ext.term',
    'ext.versioned_notifications',
    'oslo_config.sphinxconfiggen',
    'openstackdocstheme',
    'sphinx.ext.napoleon',
    'sphinxcontrib.rsvgconverter',
]

wsme_protocols = ['restjson']
config_generator_config_file = [(
    '../../etc/watcher/oslo-config-generator/watcher.conf',
    '_static/watcher')]
sample_config_basename = 'watcher'

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'Watcher'
copyright = 'OpenStack Foundation'

# A list of ignored prefixes for module index sorting.
modindex_common_prefix = ['watcher.']

exclude_patterns = [
    # The man directory includes some snippet files that are included
    # in other documents during the build but that should not be
    # included in the toctree themselves, so tell Sphinx to ignore
    # them when scanning for input files.
    'man/footer.rst',
    'man/general-options.rst',
    'strategies/strategy-template.rst',
    'image_src/plantuml/README.rst',
]

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = True

suppress_warnings = ['app.add_directive']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'native'

# -- Options for man page output --------------------------------------------

# Grouping the document tree for man pages.
# List of tuples 'sourcefile', 'target', u'title', u'Authors name', 'manual'

man_pages = [
    ('man/watcher-api', 'watcher-api', 'Watcher API Server',
     ['OpenStack'], 1),
    ('man/watcher-applier', 'watcher-applier', 'Watcher Applier',
     ['OpenStack'], 1),
    ('man/watcher-db-manage', 'watcher-db-manage',
     'Watcher Db Management Utility', ['OpenStack'], 1),
    ('man/watcher-decision-engine', 'watcher-decision-engine',
     'Watcher Decision Engine', ['OpenStack'], 1),
]

# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
# html_theme_path = ["."]
# html_theme = '_theme'
html_theme = 'openstackdocs'
# html_static_path = ['static']
# html_theme_options = {}

# Output file base name for HTML help builder.
htmlhelp_basename = '%sdoc' % project


#openstackdocstheme options
openstackdocs_repo_name = 'openstack/watcher'
openstackdocs_pdf_link = True
openstackdocs_auto_name = False
openstackdocs_bug_project = 'watcher'
openstackdocs_bug_tag = ''

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass
# [howto/manual]).
latex_documents = [
    ('index',
     'doc-watcher.tex',
     'Watcher Documentation',
     'OpenStack Foundation', 'manual'),
]

# If false, no module index is generated.
latex_domain_indices = False

latex_elements = {
    'makeindex': '',
    'printindex': '',
    'preamble': r'\setcounter{tocdepth}{3}',
}

# Disable usage of xindy https://bugzilla.redhat.com/show_bug.cgi?id=1643664
latex_use_xindy = False
# Example configuration for intersphinx: refer to the Python standard library.
# intersphinx_mapping = {'http://docs.python.org/': None}
