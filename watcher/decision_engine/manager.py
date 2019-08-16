# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
# Copyright (c) 2016 Intel Corp
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

"""
This component is responsible for computing a set of potential optimization
:ref:`Actions <action_definition>` in order to fulfill the
:ref:`Goal <goal_definition>` of an :ref:`Audit <audit_definition>`.

It first reads the parameters of the :ref:`Audit <audit_definition>` from the
associated :ref:`Audit Template <audit_template_definition>` and knows the
:ref:`Goal <goal_definition>` to achieve.

It then selects the most appropriate :ref:`Strategy <strategy_definition>`
depending on how Watcher was configured for this :ref:`Goal <goal_definition>`.

The :ref:`Strategy <strategy_definition>` is then executed and generates a set
of :ref:`Actions <action_definition>` which are scheduled in time by the
:ref:`Watcher Planner <watcher_planner_definition>` (i.e., it generates an
:ref:`Action Plan <action_plan_definition>`).

See :doc:`../architecture` for more details on this component.
"""

from watcher.common import service_manager
from watcher import conf
from watcher.decision_engine.messaging import audit_endpoint
from watcher.decision_engine.messaging import data_model_endpoint
from watcher.decision_engine.model.collector import manager
from watcher.decision_engine.strategy.strategies import base \
    as strategy_endpoint

CONF = conf.CONF


class DecisionEngineManager(service_manager.ServiceManager):

    @property
    def service_name(self):
        return 'watcher-decision-engine'

    @property
    def api_version(self):
        return '1.0'

    @property
    def publisher_id(self):
        return CONF.watcher_decision_engine.publisher_id

    @property
    def conductor_topic(self):
        return CONF.watcher_decision_engine.conductor_topic

    @property
    def notification_topics(self):
        return CONF.watcher_decision_engine.notification_topics

    @property
    def conductor_endpoints(self):
        return [audit_endpoint.AuditEndpoint,
                strategy_endpoint.StrategyEndpoint,
                data_model_endpoint.DataModelEndpoint]

    @property
    def notification_endpoints(self):
        return self.collector_manager.get_notification_endpoints()

    @property
    def collector_manager(self):
        return manager.CollectorManager()
