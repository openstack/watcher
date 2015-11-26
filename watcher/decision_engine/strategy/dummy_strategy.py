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
from oslo_log import log

from watcher.decision_engine.meta_action.nop import Nop
from watcher.decision_engine.strategy.base import BaseStrategy

LOG = log.getLogger(__name__)


class DummyStrategy(BaseStrategy):

    DEFAULT_NAME = "dummy"
    DEFAULT_DESCRIPTION = "Dummy Strategy"

    def __init__(self, name=DEFAULT_NAME, description=DEFAULT_DESCRIPTION):
        super(DummyStrategy, self).__init__(name, description)

    def execute(self, model):
        n = Nop()
        self.solution.add_change_request(n)
        return self.solution
