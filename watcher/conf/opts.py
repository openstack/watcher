# Copyright 2016 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
This is the single point of entry to generate the sample configuration
file for Watcher. It collects all the necessary info from the other modules
in this package. It is assumed that:

* every other module in this package has a 'list_opts' function which
  return a dict where
  * the keys are strings which are the group names
  * the value of each key is a list of config options for that group
* the watcher.conf package doesn't have further packages with config options
* this module is only used in the context of sample file generation
"""

import importlib
import os
import pkgutil

LIST_OPTS_FUNC_NAME = "list_opts"


def list_opts():
    """Grouped list of all the Watcher-specific configuration options

    :return: A list of ``(group, [opt_1, opt_2])`` tuple pairs, where ``group``
             is either a group name as a string or an OptGroup object.
    """
    opts = list()
    module_names = _list_module_names()
    imported_modules = _import_modules(module_names)
    for mod in imported_modules:
        opts.extend(mod.list_opts())
    return opts


def _list_module_names():
    module_names = []
    package_path = os.path.dirname(os.path.abspath(__file__))
    for __, modname, ispkg in pkgutil.iter_modules(path=[package_path]):
        if modname == "opts" or ispkg:
            continue
        else:
            module_names.append(modname)
    return module_names


def _import_modules(module_names):
    imported_modules = []
    for modname in module_names:
        mod = importlib.import_module("watcher.conf." + modname)
        if not hasattr(mod, LIST_OPTS_FUNC_NAME):
            msg = "The module 'watcher.conf.%s' should have a '%s' "\
                  "function which returns the config options." % \
                  (modname, LIST_OPTS_FUNC_NAME)
            raise Exception(msg)
        else:
            imported_modules.append(mod)
    return imported_modules
