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

from watcher.decision_engine.api.strategy.strategy import StrategyLevel


class MetaAction(object):
    def __init__(self):
        self.level = StrategyLevel.conservative
        self.priority = 0

    def get_level(self):
        return self.level

    def set_level(self, level):
        self.level = level

    def set_priority(self, priority):
        self.priority = priority

    def get_priority(self):
        return self.priority

    def __str__(self):
        return "  "
