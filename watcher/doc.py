# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
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

from __future__ import unicode_literals

import importlib
import inspect

from docutils import nodes
from docutils.parsers import rst
from docutils import statemachine
from stevedore import extension

from watcher.version import version_info


class BaseWatcherDirective(rst.Directive):

    def __init__(self, name, arguments, options, content, lineno,
                 content_offset, block_text, state, state_machine):
        super(BaseWatcherDirective, self).__init__(
            name, arguments, options, content, lineno,
            content_offset, block_text, state, state_machine)
        self.result = statemachine.ViewList()

    def run(self):
        raise NotImplementedError('Must override run() is subclass.')

    def add_line(self, line, *lineno):
        """Append one line of generated reST to the output."""
        self.result.append(line, rst.directives.unchanged, *lineno)

    def add_textblock(self, textblock):
        for line in textblock.splitlines():
            self.add_line(line)

    def add_object_docstring(self, obj):
        obj_raw_docstring = obj.__doc__ or ""

        # Maybe it's within the __init__
        if not obj_raw_docstring and hasattr(obj, "__init__"):
            if obj.__init__.__doc__:
                obj_raw_docstring = obj.__init__.__doc__

        if not obj_raw_docstring:
            # Raise a warning to make the tests fail wit doc8
            raise self.error("No docstring available for %s!" % obj)

        obj_docstring = inspect.cleandoc(obj_raw_docstring)
        self.add_textblock(obj_docstring)


class WatcherTerm(BaseWatcherDirective):
    """Directive to import an RST formatted docstring into the Watcher glossary

    **How to use it**

    # inside your .py file
    class DocumentedObject(object):
        '''My *.rst* docstring'''


    # Inside your .rst file
    .. watcher-term:: import.path.to.your.DocumentedObject

    This directive will then import the docstring and then interprete it.
    """

    # You need to put an import path as an argument for this directive to work
    required_arguments = 1

    def run(self):
        cls_path = self.arguments[0]

        try:
            cls = importlib.import_module(cls_path)
        except Exception as exc:
            raise self.error(exc)

        self.add_object_docstring(cls)

        node = nodes.paragraph()
        node.document = self.state.document
        self.state.nested_parse(self.result, 0, node)
        return node.children


class DriversDoc(BaseWatcherDirective):
    """Directive to import an RST formatted docstring into the Watcher doc

    This directive imports the RST formatted docstring of every driver declared
    within an entry point namespace provided as argument

    **How to use it**

    # inside your .py file
    class DocumentedClassReferencedInEntrypoint(object):
        '''My *.rst* docstring'''

        def foo(self):
            '''Foo docstring'''

    # Inside your .rst file
    .. drivers-doc:: entrypoint_namespace
       :append_methods_doc: foo

    This directive will then import the docstring and then interprete it.

    Note that no section/sub-section can be imported via this directive as it
    is a Sphinx restriction.
    """

    # You need to put an import path as an argument for this directive to work
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    has_content = False

    option_spec = dict(
        # CSV formatted list of method names whose return values will be zipped
        # together in the given order
        append_methods_doc=lambda opts: [
            opt.strip() for opt in opts.split(",") if opt.strip()],
        # By default, we always start by adding the driver object docstring
        exclude_driver_docstring=rst.directives.flag,
    )

    def run(self):
        ext_manager = extension.ExtensionManager(namespace=self.arguments[0])
        extensions = ext_manager.extensions
        # Aggregates drivers based on their module name (i.e import path)
        classes = [(ext.name, ext.plugin) for ext in extensions]

        for name, cls in classes:
            self.add_line(".. rubric:: %s" % name)
            self.add_line("")

            if "exclude_driver_docstring" not in self.options:
                self.add_object_docstring(cls)
                self.add_line("")

            for method_name in self.options.get("append_methods_doc", []):
                if hasattr(cls, method_name):
                    method = getattr(cls, method_name)
                    method_result = inspect.cleandoc(method)
                    self.add_textblock(method_result())
                    self.add_line("")

        node = nodes.paragraph()
        node.document = self.state.document
        self.state.nested_parse(self.result, 0, node)
        return node.children


def setup(app):
    app.add_directive('drivers-doc', DriversDoc)
    app.add_directive('watcher-term', WatcherTerm)
    return {'version': version_info.version_string()}
