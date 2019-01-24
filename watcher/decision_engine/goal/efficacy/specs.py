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
            indicators.ComputeNodesCount(),
            indicators.ReleasedComputeNodesCount(),
            indicators.InstanceMigrationsCount(),
        ]

    def get_global_efficacy_indicator(self, indicators_map=None):
        value = 0
        global_efficacy = []
        if indicators_map and indicators_map.compute_nodes_count > 0:
            value = (float(indicators_map.released_compute_nodes_count) /
                     float(indicators_map.compute_nodes_count)) * 100
        global_efficacy.append(efficacy.Indicator(
            name="released_nodes_ratio",
            description=_("Ratio of released compute nodes divided by the "
                          "total number of enabled compute nodes."),
            unit='%',
            value=value,
        ))

        return global_efficacy


class WorkloadBalancing(base.EfficacySpecification):

    def get_indicators_specifications(self):
        return [
            indicators.InstanceMigrationsCount(),
            indicators.InstancesCount(),
            indicators.StandardDeviationValue(),
            indicators.OriginalStandardDeviationValue()
        ]

    def get_global_efficacy_indicator(self, indicators_map=None):
        gl_indicators = []
        mig_value = 0
        if indicators_map and indicators_map.instance_migrations_count > 0:
            mig_value = (
                indicators_map.instance_migrations_count /
                float(indicators_map.instances_count) * 100)
        gl_indicators.append(efficacy.Indicator(
            name="live_migrations_count",
            description=_("Ratio of migrated virtual machines to audited "
                          "virtual machines"),
            unit='%',
            value=mig_value))
        return gl_indicators


class HardwareMaintenance(base.EfficacySpecification):

    def get_indicators_specifications(self):
        return [
            indicators.LiveInstanceMigrateCount(),
            indicators.PlannedLiveInstanceMigrateCount(),
            indicators.ColdInstanceMigrateCount(),
            indicators.PlannedColdInstanceMigrateCount(),
            indicators.VolumeMigrateCount(),
            indicators.PlannedVolumeMigrateCount(),
            indicators.VolumeUpdateCount(),
            indicators.PlannedVolumeUpdateCount()
        ]

    def get_global_efficacy_indicator(self, indicators_map=None):
        li_value = 0
        if (indicators_map and
                indicators_map.planned_live_migrate_instance_count > 0):
            li_value = (
                float(indicators_map.planned_live_migrate_instance_count) /
                float(indicators_map.live_migrate_instance_count) *
                100
                )

        li_indicator = efficacy.Indicator(
            name="live_instance_migrate_ratio",
            description=_("Ratio of actual live migrated instances "
                          "to planned live migrate instances."),
            unit='%',
            value=li_value)

        ci_value = 0
        if (indicators_map and
                indicators_map.planned_cold_migrate_instance_count > 0):
            ci_value = (
                float(indicators_map.planned_cold_migrate_instance_count) /
                float(indicators_map.cold_migrate_instance_count) *
                100
                )

        ci_indicator = efficacy.Indicator(
            name="cold_instance_migrate_ratio",
            description=_("Ratio of actual cold migrated instances "
                          "to planned cold migrate instances."),
            unit='%',
            value=ci_value)

        dv_value = 0
        if (indicators_map and
                indicators_map.planned_volume_migrate_count > 0):
            dv_value = (float(indicators_map.planned_volume_migrate_count) /
                        float(indicators_map.
                              volume_migrate_count) *
                        100)

        dv_indicator = efficacy.Indicator(
            name="volume_migrate_ratio",
            description=_("Ratio of actual detached volumes migrated to"
                          " planned detached volumes migrate."),
            unit='%',
            value=dv_value)

        av_value = 0
        if (indicators_map and
                indicators_map.planned_volume_update_count > 0):
            av_value = (float(indicators_map.planned_volume_update_count) /
                        float(indicators_map.
                              volume_update_count) *
                        100)

        av_indicator = efficacy.Indicator(
            name="volume_update_ratio",
            description=_("Ratio of actual attached volumes migrated to"
                          " planned attached volumes migrate."),
            unit='%',
            value=av_value)

        return [li_indicator,
                ci_indicator,
                dv_indicator,
                av_indicator]
