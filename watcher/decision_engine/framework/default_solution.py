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
from watcher.decision_engine.api.solution.solution import Solution
from watcher.openstack.common import log

LOG = log.getLogger(__name__)


class DefaultSolution(Solution):
    def __init__(self):
        self._meta_actions = []

    def add_change_request(self, r):
        self._meta_actions.append(r)

    def __str__(self):
        val = ""
        for action in self._meta_actions:
            val += str(action) + "\n"
        return val

    @property
    def meta_actions(self):
        """Get the current meta-actions of the solution

        """
        return self._meta_actions
