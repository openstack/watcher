# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
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

from watcher._i18n import _
from watcher.decision_engine.goal.efficacy import base
from watcher.decision_engine.goal.efficacy import indicators
from watcher.decision_engine.solution import efficacy


class Unclassified(base.EfficacySpecification):

    def get_indicators_specifications(self):
        return ()

    def get_global_efficacy_indicator(self, indicators_map):
        return None


class ServerConsolidation(base.EfficacySpecification):

    def get_indicators_specifications(self):
        return [
            indicators.ReleasedComputeNodesCount(),
            indicators.VmMigrationsCount(),
        ]

    def get_global_efficacy_indicator(self, indicators_map):
        value = 0
        if indicators_map.vm_migrations_count > 0:
            value = (float(indicators_map.released_compute_nodes_count) /
                     float(indicators_map.vm_migrations_count)) * 100

        return efficacy.Indicator(
            name="released_nodes_ratio",
            description=_("Ratio of released compute nodes divided by the "
                          "number of VM migrations."),
            unit='%',
            value=value,
        )
