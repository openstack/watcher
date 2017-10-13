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

from watcher.version import version_string


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

    This directive will then import the docstring and then interpret it.
    """

    # You need to put an import path as an argument for this directive to work
    required_arguments = 1

    def run(self):
        cls_path = self.arguments[0]

        try:
            try:
                cls = importlib.import_module(cls_path)
            except ImportError:
                module_name, cls_name = cls_path.rsplit('.', 1)
                mod = importlib.import_module(module_name)
                cls = getattr(mod, cls_name)
        except Exception as exc:
            raise self.error(exc)

        self.add_object_docstring(cls)

        node = nodes.paragraph()
        node.document = self.state.document
        self.state.nested_parse(self.result, 0, node)
        return node.children


class WatcherFunc(BaseWatcherDirective):
    """Directive to import a value returned by a func into the Watcher doc

    **How to use it**

    # inside your .py file
    class Bar(object):

        def foo(object):
            return foo_string


    # Inside your .rst file
    .. watcher-func:: import.path.to.your.Bar.foo node_classname

    node_classname is decumented here:
    http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html

    This directive will then import the value and then interpret it.
    """

    # You need to put an import path as an argument for this directive to work
    # required_arguments = 1
    # optional_arguments = 1

    option_spec = {'format': rst.directives.unchanged}
    has_content = True

    def run(self):
        if not self.content:
            error = self.state_machine.reporter.error(
                'The "%s" directive is empty; content required.' % self.name,
                nodes.literal_block(self.block_text, self.block_text),
                line=self.lineno)
            return [error]

        func_path = self.content[0]
        try:
            cls_path, func_name = func_path.rsplit('.', 1)
            module_name, cls_name = cls_path.rsplit('.', 1)
            mod = importlib.import_module(module_name)
            cls = getattr(mod, cls_name)
        except Exception as exc:
            raise self.error(exc)

        cls_obj = cls()
        func = getattr(cls_obj, func_name)
        textblock = func()
        if not isinstance(textblock, str):
            textblock = str(textblock)

        self.add_textblock(textblock)

        try:
            node_class = getattr(nodes,
                                 self.options.get('format', 'paragraph'))
        except Exception as exc:
            raise self.error(exc)

        node = node_class()
        node.document = self.state.document
        self.state.nested_parse(self.result, 0, node)
        return [node]


def setup(app):
    app.add_directive('watcher-term', WatcherTerm)
    app.add_directive('watcher-func', WatcherFunc)
    return {'version': version_string}
