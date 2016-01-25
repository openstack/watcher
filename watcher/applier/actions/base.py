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


import abc

import six


@six.add_metaclass(abc.ABCMeta)
class BaseAction(object):
    def __init__(self):
        self._input_parameters = {}
        self._applies_to = ""

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

    @abc.abstractmethod
    def execute(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def revert(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def precondition(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def postcondition(self):
        raise NotImplementedError()
