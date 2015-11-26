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

from watcher.decision_engine.strategy.level import StrategyLevel


@six.add_metaclass(abc.ABCMeta)
class MetaAction(object):
    def __init__(self):
        self._level = StrategyLevel.conservative
        self._priority = 0

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, l):
        self._level = l

    @property
    def priority(self):
        return self._priority

    @priority.setter
    def priority(self, p):
        self._priority = p

    def __str__(self):
        return "  "
