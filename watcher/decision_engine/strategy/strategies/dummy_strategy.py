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

from watcher._i18n import _
from watcher.decision_engine.strategy.strategies import base

LOG = log.getLogger(__name__)


class DummyStrategy(base.DummyBaseStrategy):
    """Dummy strategy used for integration testing via Tempest

    *Description*

    This strategy does not provide any useful optimization. Indeed, its only
    purpose is to be used by Tempest tests.

    *Requirements*

    <None>

    *Limitations*

    Do not use in production.

    *Spec URL*

    <None>
    """

    NOP = "nop"
    SLEEP = "sleep"

    def __init__(self, config=None, osc=None):
        """Dummy Strategy implemented for demo and testing purposes

        :param config: A mapping containing the configuration of this strategy
        :type config: dict
        :param osc: :py:class:`~.OpenStackClients` instance
        """
        super(DummyStrategy, self).__init__(config, osc)

    def execute(self, original_model):
        LOG.debug("Executing Dummy strategy")
        parameters = {'message': 'hello World'}
        self.solution.add_action(action_type=self.NOP,
                                 input_parameters=parameters)

        parameters = {'message': 'Welcome'}
        self.solution.add_action(action_type=self.NOP,
                                 input_parameters=parameters)

        self.solution.add_action(action_type=self.SLEEP,
                                 input_parameters={'duration': 5.0})
        return self.solution

    @classmethod
    def get_name(cls):
        return "dummy"

    @classmethod
    def get_display_name(cls):
        return _("Dummy strategy")

    @classmethod
    def get_translatable_display_name(cls):
        return "Dummy strategy"
