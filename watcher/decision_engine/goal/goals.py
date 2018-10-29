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
from watcher.decision_engine.goal import base
from watcher.decision_engine.goal.efficacy import specs


class Dummy(base.Goal):
    """Dummy

    Reserved goal that is used for testing purposes.
    """

    @classmethod
    def get_name(cls):
        return "dummy"

    @classmethod
    def get_display_name(cls):
        return _("Dummy goal")

    @classmethod
    def get_translatable_display_name(cls):
        return "Dummy goal"

    @classmethod
    def get_efficacy_specification(cls):
        """The efficacy spec for the current goal"""
        return specs.Unclassified()


class Unclassified(base.Goal):
    """Unclassified

    This goal is used to ease the development process of a strategy. Containing
    no actual indicator specification, this goal can be used whenever a
    strategy has yet to be formally associated with an existing goal. If the
    goal achieve has been identified but there is no available implementation,
    this Goal can also be used as a transitional stage.
    """

    @classmethod
    def get_name(cls):
        return "unclassified"

    @classmethod
    def get_display_name(cls):
        return _("Unclassified")

    @classmethod
    def get_translatable_display_name(cls):
        return "Unclassified"

    @classmethod
    def get_efficacy_specification(cls):
        """The efficacy spec for the current goal"""
        return specs.Unclassified()


class ServerConsolidation(base.Goal):
    """ServerConsolidation

    This goal is for efficient usage of compute server resources in order to
    reduce the total number of servers.
    """

    @classmethod
    def get_name(cls):
        return "server_consolidation"

    @classmethod
    def get_display_name(cls):
        return _("Server Consolidation")

    @classmethod
    def get_translatable_display_name(cls):
        return "Server Consolidation"

    @classmethod
    def get_efficacy_specification(cls):
        """The efficacy spec for the current goal"""
        return specs.ServerConsolidation()


class ThermalOptimization(base.Goal):
    """ThermalOptimization

    This goal is used to balance the temperature across different servers.
    """

    @classmethod
    def get_name(cls):
        return "thermal_optimization"

    @classmethod
    def get_display_name(cls):
        return _("Thermal Optimization")

    @classmethod
    def get_translatable_display_name(cls):
        return "Thermal Optimization"

    @classmethod
    def get_efficacy_specification(cls):
        """The efficacy spec for the current goal"""
        return specs.Unclassified()


class WorkloadBalancing(base.Goal):
    """WorkloadBalancing

    This goal is used to evenly distribute workloads across different servers.
    """

    @classmethod
    def get_name(cls):
        return "workload_balancing"

    @classmethod
    def get_display_name(cls):
        return _("Workload Balancing")

    @classmethod
    def get_translatable_display_name(cls):
        return "Workload Balancing"

    @classmethod
    def get_efficacy_specification(cls):
        """The efficacy spec for the current goal"""
        return specs.WorkloadBalancing()


class AirflowOptimization(base.Goal):
    """AirflowOptimization

    This goal is used to optimize the airflow within a cloud infrastructure.
    """

    @classmethod
    def get_name(cls):
        return "airflow_optimization"

    @classmethod
    def get_display_name(cls):
        return _("Airflow Optimization")

    @classmethod
    def get_translatable_display_name(cls):
        return "Airflow Optimization"

    @classmethod
    def get_efficacy_specification(cls):
        """The efficacy spec for the current goal"""
        return specs.Unclassified()


class NoisyNeighborOptimization(base.Goal):
    """NoisyNeighborOptimization

    This goal is used to identify and migrate a Noisy Neighbor -
    a low priority VM that negatively affects performance of a high priority VM
    in terms of IPC by over utilizing Last Level Cache.
    """

    @classmethod
    def get_name(cls):
        return "noisy_neighbor"

    @classmethod
    def get_display_name(cls):
        return _("Noisy Neighbor")

    @classmethod
    def get_translatable_display_name(cls):
        return "Noisy Neighbor"

    @classmethod
    def get_efficacy_specification(cls):
        """The efficacy spec for the current goal"""
        return specs.Unclassified()


class SavingEnergy(base.Goal):
    """SavingEnergy

    This goal is used to reduce power consumption within a data center.
    """

    @classmethod
    def get_name(cls):
        return "saving_energy"

    @classmethod
    def get_display_name(cls):
        return _("Saving Energy")

    @classmethod
    def get_translatable_display_name(cls):
        return "Saving Energy"

    @classmethod
    def get_efficacy_specification(cls):
        """The efficacy spec for the current goal"""
        return specs.Unclassified()


class HardwareMaintenance(base.Goal):
    """HardwareMaintenance

    This goal is to migrate instances and volumes on a set of compute nodes
    and storage from nodes under maintenance
    """

    @classmethod
    def get_name(cls):
        return "hardware_maintenance"

    @classmethod
    def get_display_name(cls):
        return _("Hardware Maintenance")

    @classmethod
    def get_translatable_display_name(cls):
        return "Hardware Maintenance"

    @classmethod
    def get_efficacy_specification(cls):
        """The efficacy spec for the current goal"""
        return specs.HardwareMaintenance()


class ClusterMaintaining(base.Goal):
    """ClusterMaintenance

    This goal is used to maintain compute nodes
    without having the user's application being interrupted.
    """

    @classmethod
    def get_name(cls):
        return "cluster_maintaining"

    @classmethod
    def get_display_name(cls):
        return _("Cluster Maintaining")

    @classmethod
    def get_translatable_display_name(cls):
        return "Cluster Maintaining"

    @classmethod
    def get_efficacy_specification(cls):
        """The efficacy spec for the current goal"""
        return specs.Unclassified()
