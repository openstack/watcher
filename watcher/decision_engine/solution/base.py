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
class Solution(object):
    def __init__(self):
        self._origin = None
        self._model = None
        self._efficiency = 0

    @property
    def efficiency(self):
        return self._efficiency

    @efficiency.setter
    def efficiency(self, e):
        self._efficiency = e

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, m):
        self._model = m

    @property
    def origin(self):
        return self._origin

    @origin.setter
    def origin(self, m):
        self._origin = m

    @abc.abstractmethod
    def add_change_request(self, r):
        raise NotImplementedError(
            "Should have implemented this")  # pragma:no cover

    @abc.abstractproperty
    def meta_actions(self):
        raise NotImplementedError(
            "Should have implemented this")  # pragma:no cover
