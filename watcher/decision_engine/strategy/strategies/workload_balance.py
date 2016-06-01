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


class WorkloadBalance(base.WorkloadStabilizationBaseStrategy):
    """[PoC]Workload balance using live migration

    *Description*

        It is a migration strategy based on the VM workload of physical
        servers. It generates solutions to move a workload whenever a server's
        CPU utilization % is higher than the specified threshold.
        The VM to be moved should make the host close to average workload
        of all hypervisors.

    *Requirements*

        * Hardware: compute node should use the same physical CPUs
        * Software: Ceilometer component ceilometer-agent-compute running
          in each compute node, and Ceilometer API can report such telemetry
          "cpu_util" successfully.
        * You must have at least 2 physical compute nodes to run this strategy

    *Limitations*

       - This is a proof of concept that is not meant to be used in production
       - We cannot forecast how many servers should be migrated. This is the
         reason why we only plan a single virtual machine migration at a time.
         So it's better to use this algorithm with `CONTINUOUS` audits.
       - It assume that live migrations are possible

    """

    # The meter to report CPU utilization % of VM in ceilometer
    METER_NAME = "cpu_util"
    # Unit: %, value range is [0 , 100]
    # TODO(Junjie): make it configurable
    THRESHOLD = 25.0
    # choose 300 seconds as the default duration of meter aggregation
    # TODO(Junjie): make it configurable
    PERIOD = 300

    MIGRATION = "migrate"

    def __init__(self, config, osc=None):
        """Workload balance using live migration

        :param config: A mapping containing the configuration of this strategy
        :type config: :py:class:`~.Struct` instance
        :param osc: :py:class:`~.OpenStackClients` instance
        """
        super(WorkloadBalance, self).__init__(config, osc)
        # the migration plan will be triggered when the CPU utlization %
        # reaches threshold
        # TODO(Junjie): Threshold should be configurable for each audit
        self.threshold = self.THRESHOLD
        self._meter = self.METER_NAME
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
        return "workload_balance"

    @classmethod
    def get_display_name(cls):
        return _("workload balance migration strategy")

    @classmethod
    def get_translatable_display_name(cls):
        return "workload balance migration strategy"

    def calculate_used_resource(self, hypervisor, cap_cores, cap_mem,
                                cap_disk):
        """Calculate the used vcpus, memory and disk based on VM flavors"""
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

    def choose_vm_to_migrate(self, hosts, avg_workload, workload_cache):
        """Pick up an active vm instance to migrate from provided hosts

        :param hosts: the array of dict which contains hypervisor object
        :param avg_workload: the average workload value of all hypervisors
        :param workload_cache: the map contains vm to workload mapping
        """
        for hvmap in hosts:
            source_hypervisor = hvmap['hv']
            source_vms = self.model.get_mapping().get_node_vms(
                source_hypervisor)
            if source_vms:
                delta_workload = hvmap['workload'] - avg_workload
                min_delta = 1000000
                instance_id = None
                for vm_id in source_vms:
                    try:
                        # select the first active VM to migrate
                        vm = self.model.get_vm_from_id(vm_id)
                        if vm.state != vm_state.VMState.ACTIVE.value:
                            LOG.debug("VM not active, skipped: %s",
                                      vm.uuid)
                            continue
                        current_delta = delta_workload - workload_cache[vm_id]
                        if 0 <= current_delta < min_delta:
                            min_delta = current_delta
                            instance_id = vm_id
                    except wexc.InstanceNotFound:
                        LOG.error(_LE("VM not found Error: %s"), vm_id)
                if instance_id:
                    return source_hypervisor, self.model.get_vm_from_id(
                        instance_id)
            else:
                LOG.info(_LI("VM not found from hypervisor: %s"),
                         source_hypervisor.uuid)

    def filter_destination_hosts(self, hosts, vm_to_migrate,
                                 avg_workload, workload_cache):
        '''Only return hosts with sufficient available resources'''

        cap_cores = self.model.get_resource_from_id(
            resource.ResourceType.cpu_cores)
        cap_disk = self.model.get_resource_from_id(resource.ResourceType.disk)
        cap_mem = self.model.get_resource_from_id(resource.ResourceType.memory)

        required_cores = cap_cores.get_capacity(vm_to_migrate)
        required_disk = cap_disk.get_capacity(vm_to_migrate)
        required_mem = cap_mem.get_capacity(vm_to_migrate)

        # filter hypervisors without enough resource
        destination_hosts = []
        src_vm_workload = workload_cache[vm_to_migrate.uuid]
        for hvmap in hosts:
            host = hvmap['hv']
            workload = hvmap['workload']
            # calculate the available resources
            cores_used, mem_used, disk_used = self.calculate_used_resource(
                host, cap_cores, cap_mem, cap_disk)
            cores_available = cap_cores.get_capacity(host) - cores_used
            disk_available = cap_disk.get_capacity(host) - disk_used
            mem_available = cap_mem.get_capacity(host) - mem_used
            if (
                    cores_available >= required_cores and
                    disk_available >= required_disk and
                    mem_available >= required_mem and
                    (src_vm_workload + workload) < self.threshold / 100 *
                    cap_cores.get_capacity(host)
            ):
                destination_hosts.append(hvmap)

        return destination_hosts

    def group_hosts_by_cpu_util(self):
        """Calculate the workloads of each hypervisor

        try to find out the hypervisors which have reached threshold
        and the hypervisors which are under threshold.
        and also calculate the average workload value of all hypervisors.
        and also generate the VM workload map.
        """

        hypervisors = self.model.get_all_hypervisors()
        cluster_size = len(hypervisors)
        if not hypervisors:
            raise wexc.ClusterEmpty()
        # get cpu cores capacity of hypervisors and vms
        cap_cores = self.model.get_resource_from_id(
            resource.ResourceType.cpu_cores)
        overload_hosts = []
        nonoverload_hosts = []
        # total workload of cluster
        # it's the total core numbers being utilized in a cluster.
        cluster_workload = 0.0
        # use workload_cache to store the workload of VMs for reuse purpose
        workload_cache = {}
        for hypervisor_id in hypervisors:
            hypervisor = self.model.get_hypervisor_from_id(hypervisor_id)
            vms = self.model.get_mapping().get_node_vms(hypervisor)
            hypervisor_workload = 0.0
            for vm_id in vms:
                vm = self.model.get_vm_from_id(vm_id)
                try:
                    cpu_util = self.ceilometer.statistic_aggregation(
                        resource_id=vm_id,
                        meter_name=self._meter,
                        period=self._period,
                        aggregate='avg')
                except Exception as exc:
                    LOG.exception(exc)
                    LOG.error(_LE("Can not get cpu_util"))
                    continue
                if cpu_util is None:
                    LOG.debug("%s: cpu_util is None", vm_id)
                    continue
                vm_cores = cap_cores.get_capacity(vm)
                workload_cache[vm_id] = cpu_util * vm_cores / 100
                hypervisor_workload += workload_cache[vm_id]
                LOG.debug("%s: cpu_util %f", vm_id, cpu_util)
            hypervisor_cores = cap_cores.get_capacity(hypervisor)
            hy_cpu_util = hypervisor_workload / hypervisor_cores * 100

            cluster_workload += hypervisor_workload

            hvmap = {'hv': hypervisor, "cpu_util": hy_cpu_util, 'workload':
                     hypervisor_workload}
            if hy_cpu_util >= self.threshold:
                # mark the hypervisor to release resources
                overload_hosts.append(hvmap)
            else:
                nonoverload_hosts.append(hvmap)

        avg_workload = cluster_workload / cluster_size

        return overload_hosts, nonoverload_hosts, avg_workload, workload_cache

    def pre_execute(self):
        """Pre-execution phase

        This can be used to fetch some pre-requisites or data.
        """
        LOG.info(_LI("Initializing Workload Balance Strategy"))

        if self.model is None:
            raise wexc.ClusterStateNotDefined()

    def do_execute(self):
        """Strategy execution phase

        This phase is where you should put the main logic of your strategy.
        """
        src_hypervisors, target_hypervisors, avg_workload, workload_cache = (
            self.group_hosts_by_cpu_util())

        if not src_hypervisors:
            LOG.debug("No hosts require optimization")
            return self.solution

        if not target_hypervisors:
            LOG.warning(_LW("No hosts current have CPU utilization under %s "
                            "percent, therefore there are no possible target "
                            "hosts for any migration"),
                        self.threshold)
            return self.solution

        # choose the server with largest cpu_util
        src_hypervisors = sorted(src_hypervisors,
                                 reverse=True,
                                 key=lambda x: (x[self.METER_NAME]))

        vm_to_migrate = self.choose_vm_to_migrate(
            src_hypervisors, avg_workload, workload_cache)
        if not vm_to_migrate:
            return self.solution
        source_hypervisor, vm_src = vm_to_migrate
        # find the hosts that have enough resource for the VM to be migrated
        destination_hosts = self.filter_destination_hosts(
            target_hypervisors, vm_src, avg_workload, workload_cache)
        # sort the filtered result by workload
        # pick up the lowest one as dest server
        if not destination_hosts:
            # for instance.
            LOG.warning(_LW("No proper target host could be found, it might "
                            "be because of there's no enough CPU/Memory/DISK"))
            return self.solution
        destination_hosts = sorted(destination_hosts,
                                   key=lambda x: (x["cpu_util"]))
        # always use the host with lowerest CPU utilization
        mig_dst_hypervisor = destination_hosts[0]['hv']
        # generate solution to migrate the vm to the dest server,
        if self.model.get_mapping().migrate_vm(vm_src, source_hypervisor,
                                               mig_dst_hypervisor):
            parameters = {'migration_type': 'live',
                          'src_hypervisor': source_hypervisor.uuid,
                          'dst_hypervisor': mig_dst_hypervisor.uuid}
            self.solution.add_action(action_type=self.MIGRATION,
                                     resource_id=vm_src.uuid,
                                     input_parameters=parameters)

    def post_execute(self):
        """Post-execution phase

        This can be used to compute the global efficacy
        """
        self.solution.model = self.model
