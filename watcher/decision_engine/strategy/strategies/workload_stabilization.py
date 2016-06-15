# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Servionica LLC
#
# Authors: Alexander Chadin <a.chadin@servionica.ru>
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

from copy import deepcopy
import itertools
import math
import random

import oslo_cache
from oslo_config import cfg
from oslo_log import log

from watcher._i18n import _LI, _
from watcher.common import exception
from watcher.decision_engine.model import resource
from watcher.decision_engine.model import vm_state
from watcher.decision_engine.strategy.strategies import base
from watcher.metrics_engine.cluster_history import ceilometer as \
    ceilometer_cluster_history

LOG = log.getLogger(__name__)

metrics = ['cpu_util', 'memory.resident']
thresholds_dict = {'cpu_util': 0.2, 'memory.resident': 0.2}
weights_dict = {'cpu_util_weight': 1.0, 'memory.resident_weight': 1.0}
vm_host_measures = {'cpu_util': 'hardware.cpu.util',
                    'memory.resident': 'hardware.memory.used'}

ws_opts = [
    cfg.ListOpt('metrics',
                default=metrics,
                required=True,
                help='Metrics used as rates of cluster loads.'),
    cfg.DictOpt('thresholds',
                default=thresholds_dict,
                help=''),
    cfg.DictOpt('weights',
                default=weights_dict,
                help='These weights used to calculate '
                     'common standard deviation. Name of weight '
                     'contains meter name and _weight suffix.'),
    cfg.StrOpt('host_choice',
               default='retry',
               required=True,
               help="Method of host's choice."),
    cfg.IntOpt('retry_count',
               default=1,
               required=True,
               help='Count of random returned hosts.'),
]

CONF = cfg.CONF

CONF.register_opts(ws_opts, 'watcher_strategies.workload_stabilization')


def _set_memoize(conf):
    oslo_cache.configure(conf)
    region = oslo_cache.create_region()
    configured_region = oslo_cache.configure_cache_region(conf, region)
    return oslo_cache.core.get_memoization_decorator(conf,
                                                     configured_region,
                                                     'cache')


class WorkloadStabilization(base.WorkloadStabilizationBaseStrategy):
    """Workload Stabilization control using live migration

    *Description*

    This is workload stabilization strategy based on standard deviation
    algorithm. The goal is to determine if there is an overload in a cluster
    and respond to it by migrating VMs to stabilize the cluster.

    *Requirements*

    * Software: Ceilometer component ceilometer-compute running
      in each compute host, and Ceilometer API can report such telemetries
      ``memory.resident`` and ``cpu_util`` successfully.
    * You must have at least 2 physical compute nodes to run this strategy.

    *Limitations*

    - It assume that live migrations are possible
    - Load on the system is sufficiently stable.

    *Spec URL*

    https://review.openstack.org/#/c/286153/
    """

    MIGRATION = "migrate"
    MEMOIZE = _set_memoize(CONF)

    def __init__(self, config, osc=None):
        super(WorkloadStabilization, self).__init__(config, osc)
        self._ceilometer = None
        self._nova = None
        self.weights = CONF['watcher_strategies.workload_stabilization']\
            .weights
        self.metrics = CONF['watcher_strategies.workload_stabilization']\
            .metrics
        self.thresholds = CONF['watcher_strategies.workload_stabilization']\
            .thresholds
        self.host_choice = CONF['watcher_strategies.workload_stabilization']\
            .host_choice

    @classmethod
    def get_name(cls):
        return "workload_stabilization"

    @classmethod
    def get_display_name(cls):
        return _("Workload stabilization")

    @classmethod
    def get_translatable_display_name(cls):
        return "Workload stabilization"

    @property
    def ceilometer(self):
        if self._ceilometer is None:
            self._ceilometer = (ceilometer_cluster_history.
                                CeilometerClusterHistory(osc=self.osc))
        return self._ceilometer

    @property
    def nova(self):
        if self._nova is None:
            self._nova = self.osc.nova()
        return self._nova

    @nova.setter
    def nova(self, n):
        self._nova = n

    @ceilometer.setter
    def ceilometer(self, c):
        self._ceilometer = c

    def transform_vm_cpu(self, vm_load, host_vcpus):
        """This method transforms vm cpu utilization to overall host cpu utilization.

        :param vm_load: dict that contains vm uuid and utilization info.
        :param host_vcpus: int
        :return: float value
        """
        return vm_load['cpu_util'] * (vm_load['vcpus'] / float(host_vcpus))

    @MEMOIZE
    def get_vm_load(self, vm_uuid):
        """Gathering vm load through ceilometer statistic.

        :param vm_uuid: vm for which statistic is gathered.
        :return: dict
        """
        LOG.debug(_LI('get_vm_load started'))
        vm_vcpus = self.model.get_resource_from_id(
            resource.ResourceType.cpu_cores).get_capacity(
                self.model.get_vm_from_id(vm_uuid))
        vm_load = {'uuid': vm_uuid, 'vcpus': vm_vcpus}
        for meter in self.metrics:
            avg_meter = self.ceilometer.statistic_aggregation(
                resource_id=vm_uuid,
                meter_name=meter,
                period="120",
                aggregate='min'
            )
            if avg_meter is None:
                raise exception.NoMetricValuesForVM(resource_id=vm_uuid,
                                                    metric_name=meter)
            vm_load[meter] = avg_meter
        return vm_load

    def normalize_hosts_load(self, hosts):
        normalized_hosts = deepcopy(hosts)
        for host in normalized_hosts:
            if 'memory.resident' in normalized_hosts[host]:
                h_memory = self.model.get_resource_from_id(
                    resource.ResourceType.memory).get_capacity(
                        self.model.get_hypervisor_from_id(host))
                normalized_hosts[host]['memory.resident'] /= float(h_memory)

        return normalized_hosts

    def get_hosts_load(self):
        """Get load of every host by gathering vms load"""
        hosts_load = {}
        for hypervisor_id in self.model.get_all_hypervisors():
            hosts_load[hypervisor_id] = {}
            host_vcpus = self.model.get_resource_from_id(
                resource.ResourceType.cpu_cores).get_capacity(
                    self.model.get_hypervisor_from_id(hypervisor_id))
            hosts_load[hypervisor_id]['vcpus'] = host_vcpus

            for metric in self.metrics:
                avg_meter = self.ceilometer.statistic_aggregation(
                    resource_id=hypervisor_id,
                    meter_name=vm_host_measures[metric],
                    period="60",
                    aggregate='avg'
                )
                if avg_meter is None:
                    raise exception.NoSuchMetricForHost(
                        metric=vm_host_measures[metric],
                        host=hypervisor_id)
                hosts_load[hypervisor_id][metric] = avg_meter
        return hosts_load

    def get_sd(self, hosts, meter_name):
        """Get standard deviation among hosts by specified meter"""
        mean = 0
        variaton = 0
        for host_id in hosts:
            mean += hosts[host_id][meter_name]
        mean /= len(hosts)
        for host_id in hosts:
            variaton += (hosts[host_id][meter_name] - mean) ** 2
        variaton /= len(hosts)
        sd = math.sqrt(variaton)
        return sd

    def calculate_weighted_sd(self, sd_case):
        """Calculate common standard deviation among meters on host"""
        weighted_sd = 0
        for metric, value in zip(self.metrics, sd_case):
            try:
                weighted_sd += value * float(self.weights[metric + '_weight'])
            except KeyError as exc:
                LOG.exception(exc)
                raise exception.WatcherException(
                    _("Incorrect mapping: could not find associated weight"
                      " for %s in weight dict.") % metric)
        return weighted_sd

    def calculate_migration_case(self, hosts, vm_id, src_hp_id, dst_hp_id):
        """Calculate migration case

        Return list of standard deviation values, that appearing in case of
        migration of vm from source host to destination host
        :param hosts: hosts with their workload
        :param vm_id: the virtual machine
        :param src_hp_id: the source hypervisor id
        :param dst_hp_id: the destination hypervisor id
        :return: list of standard deviation values
        """
        migration_case = []
        new_hosts = deepcopy(hosts)
        vm_load = self.get_vm_load(vm_id)
        d_host_vcpus = new_hosts[dst_hp_id]['vcpus']
        s_host_vcpus = new_hosts[src_hp_id]['vcpus']
        for metric in self.metrics:
            if metric is 'cpu_util':
                new_hosts[src_hp_id][metric] -= self.transform_vm_cpu(
                    vm_load,
                    s_host_vcpus)
                new_hosts[dst_hp_id][metric] += self.transform_vm_cpu(
                    vm_load,
                    d_host_vcpus)
            else:
                new_hosts[src_hp_id][metric] -= vm_load[metric]
                new_hosts[dst_hp_id][metric] += vm_load[metric]
        normalized_hosts = self.normalize_hosts_load(new_hosts)
        for metric in self.metrics:
            migration_case.append(self.get_sd(normalized_hosts, metric))
        migration_case.append(new_hosts)
        return migration_case

    def simulate_migrations(self, hosts):
        """Make sorted list of pairs vm:dst_host"""
        def yield_hypervisors(hypervisors):
            ct = CONF['watcher_strategies.workload_stabilization'].retry_count
            if self.host_choice == 'cycle':
                for i in itertools.cycle(hypervisors):
                    yield [i]
            if self.host_choice == 'retry':
                while True:
                    yield random.sample(hypervisors, ct)
            if self.host_choice == 'fullsearch':
                while True:
                    yield hypervisors

        vm_host_map = []
        for source_hp_id in self.model.get_all_hypervisors():
            hypervisors = list(self.model.get_all_hypervisors())
            hypervisors.remove(source_hp_id)
            hypervisor_list = yield_hypervisors(hypervisors)
            vms_id = self.model.get_mapping(). \
                get_node_vms_from_id(source_hp_id)
            for vm_id in vms_id:
                min_sd_case = {'value': len(self.metrics)}
                vm = self.model.get_vm_from_id(vm_id)
                if vm.state not in [vm_state.VMState.ACTIVE.value,
                                    vm_state.VMState.PAUSED.value]:
                    continue
                for dst_hp_id in next(hypervisor_list):
                    sd_case = self.calculate_migration_case(hosts, vm_id,
                                                            source_hp_id,
                                                            dst_hp_id)

                    weighted_sd = self.calculate_weighted_sd(sd_case[:-1])

                    if weighted_sd < min_sd_case['value']:
                        min_sd_case = {'host': dst_hp_id, 'value': weighted_sd,
                                       's_host': source_hp_id, 'vm': vm_id}
                        vm_host_map.append(min_sd_case)
                    break
        return sorted(vm_host_map, key=lambda x: x['value'])

    def check_threshold(self):
        """Check if cluster is needed in balancing"""
        hosts_load = self.get_hosts_load()
        normalized_load = self.normalize_hosts_load(hosts_load)
        for metric in self.metrics:
            metric_sd = self.get_sd(normalized_load, metric)
            if metric_sd > float(self.thresholds[metric]):
                return self.simulate_migrations(hosts_load)

    def add_migration(self,
                      resource_id,
                      migration_type,
                      src_hypervisor,
                      dst_hypervisor):
        parameters = {'migration_type': migration_type,
                      'src_hypervisor': src_hypervisor,
                      'dst_hypervisor': dst_hypervisor}
        self.solution.add_action(action_type=self.MIGRATION,
                                 resource_id=resource_id,
                                 input_parameters=parameters)

    def create_migration_vm(self, mig_vm, mig_src_hypervisor,
                            mig_dst_hypervisor):
        """Create migration VM """
        if self.model.get_mapping().migrate_vm(
                mig_vm, mig_src_hypervisor, mig_dst_hypervisor):
            self.add_migration(mig_vm.uuid, 'live',
                               mig_src_hypervisor.uuid,
                               mig_dst_hypervisor.uuid)

    def migrate(self, vm_uuid, src_host, dst_host):
        mig_vm = self.model.get_vm_from_id(vm_uuid)
        mig_src_hypervisor = self.model.get_hypervisor_from_id(src_host)
        mig_dst_hypervisor = self.model.get_hypervisor_from_id(dst_host)
        self.create_migration_vm(mig_vm, mig_src_hypervisor,
                                 mig_dst_hypervisor)

    def fill_solution(self):
        self.solution.model = self.model
        return self.solution

    def pre_execute(self):
        LOG.info(_LI("Initializing Workload Stabilization"))

        if self.model is None:
            raise exception.ClusterStateNotDefined()

    def do_execute(self):
        migration = self.check_threshold()
        if migration:
            hosts_load = self.get_hosts_load()
            min_sd = 1
            balanced = False
            for vm_host in migration:
                dst_hp_disk = self.model.get_resource_from_id(
                    resource.ResourceType.disk).get_capacity(
                        self.model.get_hypervisor_from_id(vm_host['host']))
                vm_disk = self.model.get_resource_from_id(
                    resource.ResourceType.disk).get_capacity(
                        self.model.get_vm_from_id(vm_host['vm']))
                if vm_disk > dst_hp_disk:
                    continue
                vm_load = self.calculate_migration_case(hosts_load,
                                                        vm_host['vm'],
                                                        vm_host['s_host'],
                                                        vm_host['host'])
                weighted_sd = self.calculate_weighted_sd(vm_load[:-1])
                if weighted_sd < min_sd:
                    min_sd = weighted_sd
                    hosts_load = vm_load[-1]
                    self.migrate(vm_host['vm'],
                                 vm_host['s_host'], vm_host['host'])

                for metric, value in zip(self.metrics, vm_load[:-1]):
                    if value < float(self.thresholds[metric]):
                        balanced = True
                        break
                if balanced:
                    break

    def post_execute(self):
        """Post-execution phase

        This can be used to compute the global efficacy
        """
        self.fill_solution()
