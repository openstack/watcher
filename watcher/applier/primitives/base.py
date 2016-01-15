# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
A :ref:`Primitive <primitive_definition>` is the component that carries out a
certain type of atomic :ref:`Actions <action_definition>` on a given
:ref:`Managed resource <managed_resource_definition>` (nova, swift, neutron,
glance,..). A :ref:`Primitive <primitive_definition>` is a part of the
:ref:`Watcher Applier <watcher_applier_definition>` module.

For example, there can be a :ref:`Primitive <primitive_definition>` which is
responsible for creating a snapshot of a given instance on a Nova compute node.
This :ref:`Primitive <primitive_definition>` knows exactly how to send
the appropriate commands to Nova for this type of
:ref:`Actions <action_definition>`.
"""

import abc
import six

from watcher.applier import promise


@six.add_metaclass(abc.ABCMeta)
class BasePrimitive(object):
    def __init__(self):
        self._input_parameters = None
        self._applies_to = None

    @property
    def input_parameters(self):
        return self._input_parameters

    @input_parameters.setter
    def input_parameters(self, p):
        self._input_parameters = p

    @property
    def applies_to(self):
        return self._applies_to

    @applies_to.setter
    def applies_to(self, a):
        self._applies_to = a

    @promise.Promise
    @abc.abstractmethod
    def execute(self):
        raise NotImplementedError()

    @promise.Promise
    @abc.abstractmethod
    def undo(self):
        raise NotImplementedError()
