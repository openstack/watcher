# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Intel Corp
#
# Authors: Junjie-Huang <junjie.huang@intel.com>
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

from watcher._i18n import _, _LE, _LI, _LW
from watcher.common import exception as wexc
from watcher.decision_engine.model import resource
from watcher.decision_engine.model import vm_state
from watcher.decision_engine.strategy.strategies import base
from watcher.metrics_engine.cluster_history import ceilometer as ceil

LOG = log.getLogger(__name__)


class UniformAirflow(base.BaseStrategy):
    """[PoC]Uniform Airflow using live migration

    *Description*

        It is a migration strategy based on the Airflow of physical
        servers. It generates solutions to move vm whenever a server's
        Airflow is higher than the specified threshold.

    *Requirements*

        * Hardware: compute node with NodeManager3.0 support
        * Software: Ceilometer component ceilometer-agent-compute running
          in each compute node, and Ceilometer API can report such telemetry
          "airflow, system power, inlet temperature" successfully.
        * You must have at least 2 physical compute nodes to run this strategy

    *Limitations*

       - This is a proof of concept that is not meant to be used in production
       - We cannot forecast how many servers should be migrated. This is the
         reason why we only plan a single virtual machine migration at a time.
         So it's better to use this algorithm with `CONTINUOUS` audits.
       - It assume that live migrations are possible

    """

    # The meter to report Airflow of physical server in ceilometer
    METER_NAME_AIRFLOW = "hardware.ipmi.node.airflow"
    # The meter to report inlet temperature of physical server in ceilometer
    METER_NAME_INLET_T = "hardware.ipmi.node.temperature"
    # The meter to report system power of physical server in ceilometer
    METER_NAME_POWER = "hardware.ipmi.node.power"
    # TODO(Junjie): make below thresholds configurable
    # Unit: 0.1 CFM
    THRESHOLD_AIRFLOW = 400.0
    # Unit: degree C
    THRESHOLD_INLET_T = 28.0
    # Unit: watts
    THRESHOLD_POWER = 350.0
    # choose 300 seconds as the default duration of meter aggregation
    # TODO(Junjie): make it configurable
    PERIOD = 300

    MIGRATION = "migrate"

    def __init__(self, config, osc=None):
        """Using live migration

        :param config: A mapping containing the configuration of this strategy
        :type config: dict
        :param osc: an OpenStackClients object
        """
        super(UniformAirflow, self).__init__(config, osc)
        # The migration plan will be triggered when the Ariflow reaches
        # threshold
        # TODO(Junjie): Threshold should be configurable for each audit
        self.threshold_airflow = self.THRESHOLD_AIRFLOW
        self.threshold_inlet_t = self.THRESHOLD_INLET_T
        self.threshold_power = self.THRESHOLD_POWER
        self.meter_name_airflow = self.METER_NAME_AIRFLOW
        self.meter_name_inlet_t = self.METER_NAME_INLET_T
        self.meter_name_power = self.METER_NAME_POWER
        self._ceilometer = None
        self._period = self.PERIOD

    @property
    def ceilometer(self):
        if self._ceilometer is None:
            self._ceilometer = ceil.CeilometerClusterHistory(osc=self.osc)
        return self._ceilometer

    @ceilometer.setter
    def ceilometer(self, c):
        self._ceilometer = c

    @classmethod
    def get_name(cls):
        return "uniform_airflow"

    @classmethod
    def get_display_name(cls):
        return _("uniform airflow migration strategy")

    @classmethod
    def get_translatable_display_name(cls):
        return "uniform airflow migration strategy"

    @classmethod
    def get_goal_name(cls):
        return "airflow_optimization"

    @classmethod
    def get_goal_display_name(cls):
        return _("AIRFLOW optimization")

    @classmethod
    def get_translatable_goal_display_name(cls):
        return "Airflow optimization"

    def calculate_used_resource(self, hypervisor, cap_cores, cap_mem,
                                cap_disk):
        '''calculate the used vcpus, memory and disk based on VM flavors'''
        vms = self.model.get_mapping().get_node_vms(hypervisor)
        vcpus_used = 0
        memory_mb_used = 0
        disk_gb_used = 0
        for vm_id in vms:
            vm = self.model.get_vm_from_id(vm_id)
            vcpus_used += cap_cores.get_capacity(vm)
            memory_mb_used += cap_mem.get_capacity(vm)
            disk_gb_used += cap_disk.get_capacity(vm)

        return vcpus_used, memory_mb_used, disk_gb_used

    def choose_vm_to_migrate(self, hosts):
        """pick up an active vm instance to migrate from provided hosts

        :param hosts: the array of dict which contains hypervisor object
        """
        vms_tobe_migrate = []
        for hvmap in hosts:
            source_hypervisor = hvmap['hv']
            source_vms = self.model.get_mapping().get_node_vms(
                source_hypervisor)
            if source_vms:
                inlet_t = self.ceilometer.statistic_aggregation(
                    resource_id=source_hypervisor.uuid,
                    meter_name=self.meter_name_inlet_t,
                    period=self._period,
                    aggregate='avg')
                power = self.ceilometer.statistic_aggregation(
                    resource_id=source_hypervisor.uuid,
                    meter_name=self.meter_name_power,
                    period=self._period,
                    aggregate='avg')
                if (power < self.threshold_power and
                        inlet_t < self.threshold_inlet_t):
                    # hardware issue, migrate all vms from this hypervisor
                    for vm_id in source_vms:
                        try:
                            vm = self.model.get_vm_from_id(vm_id)
                            vms_tobe_migrate.append(vm)
                        except wexc.InstanceNotFound:
                            LOG.error(_LE("VM not found Error: %s"), vm_id)
                    return source_hypervisor, vms_tobe_migrate
                else:
                    # migrate the first active vm
                    for vm_id in source_vms:
                        try:
                            vm = self.model.get_vm_from_id(vm_id)
                            if vm.state != vm_state.VMState.ACTIVE.value:
                                LOG.info(_LE("VM not active, skipped: %s"),
                                         vm.uuid)
                                continue
                            vms_tobe_migrate.append(vm)
                            return source_hypervisor, vms_tobe_migrate
                        except wexc.InstanceNotFound:
                            LOG.error(_LE("VM not found Error: %s"), vm_id)
            else:
                LOG.info(_LI("VM not found from hypervisor: %s"),
                         source_hypervisor.uuid)

    def filter_destination_hosts(self, hosts, vms_to_migrate):
        '''return vm and host with sufficient available resources'''

        cap_cores = self.model.get_resource_from_id(
            resource.ResourceType.cpu_cores)
        cap_disk = self.model.get_resource_from_id(resource.ResourceType.disk)
        cap_mem = self.model.get_resource_from_id(
            resource.ResourceType.memory)
        # large vm go first
        vms_to_migrate = sorted(vms_to_migrate, reverse=True,
                                key=lambda x: (cap_cores.get_capacity(x)))
        # find hosts for VMs
        destination_hosts = []
        for vm_to_migrate in vms_to_migrate:
            required_cores = cap_cores.get_capacity(vm_to_migrate)
            required_disk = cap_disk.get_capacity(vm_to_migrate)
            required_mem = cap_mem.get_capacity(vm_to_migrate)
            dest_migrate_info = {}
            for hvmap in hosts:
                host = hvmap['hv']
                if 'cores_used' not in hvmap:
                    # calculate the available resources
                    hvmap['cores_used'], hvmap['mem_used'],\
                        hvmap['disk_used'] = self.calculate_used_resource(
                            host, cap_cores, cap_mem, cap_disk)
                cores_available = (cap_cores.get_capacity(host) -
                                   hvmap['cores_used'])
                disk_available = (cap_disk.get_capacity(host) -
                                  hvmap['disk_used'])
                mem_available = cap_mem.get_capacity(host) - hvmap['mem_used']
                if (cores_available >= required_cores and
                        disk_available >= required_disk and
                        mem_available >= required_mem):
                    dest_migrate_info['vm'] = vm_to_migrate
                    dest_migrate_info['hv'] = host
                    hvmap['cores_used'] += required_cores
                    hvmap['mem_used'] += required_mem
                    hvmap['disk_used'] += required_disk
                    destination_hosts.append(dest_migrate_info)
                    break
        # check if all vms have target hosts
        if len(destination_hosts) != len(vms_to_migrate):
            LOG.warning(_LW("Not all target hosts could be found, it might "
                            "be because of there's no enough resource"))
            return None
        return destination_hosts

    def group_hosts_by_airflow(self):
        """Group hosts based on airflow meters"""

        hypervisors = self.model.get_all_hypervisors()
        if not hypervisors:
            raise wexc.ClusterEmpty()
        overload_hosts = []
        nonoverload_hosts = []
        for hypervisor_id in hypervisors:
            hypervisor = self.model.get_hypervisor_from_id(hypervisor_id)
            resource_id = hypervisor.uuid
            airflow = self.ceilometer.statistic_aggregation(
                resource_id=resource_id,
                meter_name=self.meter_name_airflow,
                period=self._period,
                aggregate='avg')
            # some hosts may not have airflow meter, remove from target
            if airflow is None:
                LOG.warning(_LE("%s: no airflow data"), resource_id)
                continue

            LOG.debug("%s: airflow %f" % (resource_id, airflow))
            hvmap = {'hv': hypervisor, 'airflow': airflow}
            if airflow >= self.threshold_airflow:
                # mark the hypervisor to release resources
                overload_hosts.append(hvmap)
            else:
                nonoverload_hosts.append(hvmap)
        return overload_hosts, nonoverload_hosts

    def pre_execute(self):
        LOG.debug("Initializing Uniform Airflow Strategy")

        if self.model is None:
            raise wexc.ClusterStateNotDefined()

    def do_execute(self):
        src_hypervisors, target_hypervisors = (
            self.group_hosts_by_airflow())

        if not src_hypervisors:
            LOG.debug("No hosts require optimization")
            return self.solution

        if not target_hypervisors:
            LOG.warning(_LW("No hosts current have airflow under %s "
                            ", therefore there are no possible target "
                            "hosts for any migration"),
                        self.threshold_airflow)
            return self.solution

        # migrate the vm from server with largest airflow first
        src_hypervisors = sorted(src_hypervisors,
                                 reverse=True,
                                 key=lambda x: (x["airflow"]))
        vms_to_migrate = self.choose_vm_to_migrate(src_hypervisors)
        if not vms_to_migrate:
            return self.solution
        source_hypervisor, vms_src = vms_to_migrate
        # sort host with airflow
        target_hypervisors = sorted(target_hypervisors,
                                    key=lambda x: (x["airflow"]))
        # find the hosts that have enough resource for the VM to be migrated
        destination_hosts = self.filter_destination_hosts(target_hypervisors,
                                                          vms_src)
        if not destination_hosts:
            LOG.warning(_LW("No proper target host could be found, it might "
                            "be because of there's no enough resource"))
            return self.solution
        # generate solution to migrate the vm to the dest server,
        for info in destination_hosts:
            vm_src = info['vm']
            mig_dst_hypervisor = info['hv']
            if self.model.get_mapping().migrate_vm(vm_src,
                                                   source_hypervisor,
                                                   mig_dst_hypervisor):
                parameters = {'migration_type': 'live',
                              'src_hypervisor': source_hypervisor.uuid,
                              'dst_hypervisor': mig_dst_hypervisor.uuid}
                self.solution.add_action(action_type=self.MIGRATION,
                                         resource_id=vm_src.uuid,
                                         input_parameters=parameters)

    def post_execute(self):
        self.solution.model = self.model
        # TODO(v-francoise): Add the indicators to the solution
