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
"""
*Good server consolidation strategy*

Consolidation of VMs is essential to achieve energy optimization in cloud
environments such as OpenStack. As VMs are spinned up and/or moved over time,
it becomes necessary to migrate VMs among servers to lower the costs. However,
migration of VMs introduces runtime overheads and consumes extra energy, thus
a good server consolidation strategy should carefully plan for migration in
order to both minimize energy consumption and comply to the various SLAs.
"""

from oslo_log import log

from watcher._i18n import _LE, _LI, _LW
from watcher.common import exception
from watcher.decision_engine.model import hypervisor_state as hyper_state
from watcher.decision_engine.model import resource
from watcher.decision_engine.model import vm_state
from watcher.decision_engine.strategy.strategies import base
from watcher.metrics_engine.cluster_history import ceilometer as \
    ceilometer_cluster_history

LOG = log.getLogger(__name__)


class BasicConsolidation(base.BaseStrategy):
    """Basic offline consolidation using live migration

    *Description*

    This is server consolidation algorithm which not only minimizes the overall
    number of used servers, but also minimizes the number of migrations.

    *Requirements*

    * You must have at least 2 physical compute nodes to run this strategy.

    *Limitations*

    - It has been developed only for tests.
    - It assumes that the virtual machine and the compute node are on the same
      private network.
    - It assume that live migrations are possible

    *Spec URL*

    <None>
    """

    DEFAULT_NAME = "basic"
    DEFAULT_DESCRIPTION = "Basic offline consolidation"

    HOST_CPU_USAGE_METRIC_NAME = 'compute.node.cpu.percent'
    INSTANCE_CPU_USAGE_METRIC_NAME = 'cpu_util'

    MIGRATION = "migrate"
    CHANGE_NOVA_SERVICE_STATE = "change_nova_service_state"

    def __init__(self, name=DEFAULT_NAME, description=DEFAULT_DESCRIPTION,
                 osc=None):
        """Basic offline Consolidation using live migration

        :param name: The name of the strategy (Default: "basic")
        :param description: The description of the strategy
                            (Default: "Basic offline consolidation")
        :param osc: An :py:class:`~watcher.common.clients.OpenStackClients`
                    instance
        """
        super(BasicConsolidation, self).__init__(name, description, osc)

        # set default value for the number of released nodes
        self.number_of_released_nodes = 0
        # set default value for the number of migrations
        self.number_of_migrations = 0
        # set default value for number of allowed migration attempts
        self.migration_attempts = 0

        # set default value for the efficacy
        self.efficacy = 100

        self._ceilometer = None

        # TODO(jed) improve threshold overbooking ?,...
        self.threshold_mem = 1
        self.threshold_disk = 1
        self.threshold_cores = 1

        # TODO(jed) target efficacy
        self.target_efficacy = 60

        # TODO(jed) weight
        self.weight_cpu = 1
        self.weight_mem = 1
        self.weight_disk = 1

        # TODO(jed) bound migration attempts (80 %)
        self.bound_migration = 0.80

    @property
    def ceilometer(self):
        if self._ceilometer is None:
            self._ceilometer = (ceilometer_cluster_history.
                                CeilometerClusterHistory(osc=self.osc))
        return self._ceilometer

    @ceilometer.setter
    def ceilometer(self, ceilometer):
        self._ceilometer = ceilometer

    def compute_attempts(self, size_cluster):
        """Upper bound of the number of migration

        :param size_cluster:
        """
        self.migration_attempts = size_cluster * self.bound_migration

    def check_migration(self, cluster_data_model,
                        src_hypervisor,
                        dest_hypervisor,
                        vm_to_mig):
        """check if the migration is possible

        :param cluster_data_model: the current state of the cluster
        :param src_hypervisor: the current node of the virtual machine
        :param dest_hypervisor: the destination of the virtual machine
        :param vm_to_mig: the virtual machine
        :return: True if the there is enough place otherwise false
        """
        if src_hypervisor == dest_hypervisor:
            return False

        LOG.debug('Migrate VM {0} from {1} to  {2} '.format(vm_to_mig,
                                                            src_hypervisor,
                                                            dest_hypervisor,
                                                            ))

        total_cores = 0
        total_disk = 0
        total_mem = 0
        cpu_capacity = cluster_data_model.get_resource_from_id(
            resource.ResourceType.cpu_cores)
        disk_capacity = cluster_data_model.get_resource_from_id(
            resource.ResourceType.disk)
        memory_capacity = cluster_data_model.get_resource_from_id(
            resource.ResourceType.memory)

        for vm_id in cluster_data_model. \
                get_mapping().get_node_vms(dest_hypervisor):
            vm = cluster_data_model.get_vm_from_id(vm_id)
            total_cores += cpu_capacity.get_capacity(vm)
            total_disk += disk_capacity.get_capacity(vm)
            total_mem += memory_capacity.get_capacity(vm)

        # capacity requested by hypervisor
        total_cores += cpu_capacity.get_capacity(vm_to_mig)
        total_disk += disk_capacity.get_capacity(vm_to_mig)
        total_mem += memory_capacity.get_capacity(vm_to_mig)

        return self.check_threshold(cluster_data_model,
                                    dest_hypervisor,
                                    total_cores,
                                    total_disk,
                                    total_mem)

    def check_threshold(self, cluster_data_model,
                        dest_hypervisor,
                        total_cores,
                        total_disk,
                        total_mem):
        """Check threshold

        check the threshold value defined by the ratio of
        aggregated CPU capacity of VMs on one node to CPU capacity
        of this node must not exceed the threshold value.
        :param cluster_data_model: the current state of the cluster
        :param dest_hypervisor: the destination of the virtual machine
        :param total_cores
        :param total_disk
        :param total_mem
        :return: True if the threshold is not exceed
        """
        cpu_capacity = cluster_data_model.get_resource_from_id(
            resource.ResourceType.cpu_cores).get_capacity(dest_hypervisor)
        disk_capacity = cluster_data_model.get_resource_from_id(
            resource.ResourceType.disk).get_capacity(dest_hypervisor)
        memory_capacity = cluster_data_model.get_resource_from_id(
            resource.ResourceType.memory).get_capacity(dest_hypervisor)

        if (cpu_capacity >= total_cores * self.threshold_cores and
                disk_capacity >= total_disk * self.threshold_disk and
                memory_capacity >= total_mem * self.threshold_mem):
            return True
        else:
            return False

    def get_allowed_migration_attempts(self):
        """Allowed migration

        Maximum allowed number of migrations this allows us to fix
        the upper bound of the number of migrations
        :return:
        """
        return self.migration_attempts

    def get_threshold_cores(self):
        return self.threshold_cores

    def set_threshold_cores(self, threshold):
        self.threshold_cores = threshold

    def get_number_of_released_nodes(self):
        return self.number_of_released_nodes

    def get_number_of_migrations(self):
        return self.number_of_migrations

    def calculate_weight(self, cluster_data_model, element,
                         total_cores_used, total_disk_used,
                         total_memory_used):
        """Calculate weight of every resource

        :param cluster_data_model:
        :param element:
        :param total_cores_used:
        :param total_disk_used:
        :param total_memory_used:
        :return:
        """
        cpu_capacity = cluster_data_model.get_resource_from_id(
            resource.ResourceType.cpu_cores).get_capacity(element)

        disk_capacity = cluster_data_model.get_resource_from_id(
            resource.ResourceType.disk).get_capacity(element)

        memory_capacity = cluster_data_model.get_resource_from_id(
            resource.ResourceType.memory).get_capacity(element)

        score_cores = (1 - (float(cpu_capacity) - float(total_cores_used)) /
                       float(cpu_capacity))

        # It's possible that disk_capacity is 0, e.g. m1.nano.disk = 0
        if disk_capacity == 0:
            score_disk = 0
        else:
            score_disk = (1 - (float(disk_capacity) - float(total_disk_used)) /
                          float(disk_capacity))

        score_memory = (
            1 - (float(memory_capacity) - float(total_memory_used)) /
            float(memory_capacity))
        # todo(jed) take in account weight
        return (score_cores + score_disk + score_memory) / 3

    def calculate_score_node(self, hypervisor, model):
        """calculate the score that represent the utilization level

            :param hypervisor:
            :param model:
            :return:
            """
        resource_id = "%s_%s" % (hypervisor.uuid, hypervisor.hostname)
        host_avg_cpu_util = self.ceilometer. \
            statistic_aggregation(resource_id=resource_id,
                                  meter_name=self.HOST_CPU_USAGE_METRIC_NAME,
                                  period="7200",
                                  aggregate='avg'
                                  )
        if host_avg_cpu_util is None:
            LOG.error(
                _LE("No values returned by %(resource_id)s "
                    "for %(metric_name)s"),
                resource_id=resource_id,
                metric_name=self.HOST_CPU_USAGE_METRIC_NAME,
            )
            host_avg_cpu_util = 100

        cpu_capacity = model.get_resource_from_id(
            resource.ResourceType.cpu_cores).get_capacity(hypervisor)

        total_cores_used = cpu_capacity * (host_avg_cpu_util / 100)

        return self.calculate_weight(model, hypervisor, total_cores_used,
                                     0,
                                     0)

    def calculate_migration_efficacy(self):
        """Calculate migration efficacy

        :return: The efficacy tells us that every VM migration resulted
         in releasing on node
        """
        if self.number_of_migrations > 0:
            return (float(self.number_of_released_nodes) / float(
                self.number_of_migrations)) * 100
        else:
            return 0

    def calculate_score_vm(self, vm, cluster_data_model):
        """Calculate Score of virtual machine

        :param vm: the virtual machine
        :param cluster_data_model: the cluster model
        :return: score
        """
        if cluster_data_model is None:
            raise exception.ClusterStateNotDefined()

        vm_cpu_utilization = self.ceilometer. \
            statistic_aggregation(
                resource_id=vm.uuid,
                meter_name=self.INSTANCE_CPU_USAGE_METRIC_NAME,
                period="7200",
                aggregate='avg'
            )
        if vm_cpu_utilization is None:
            LOG.error(
                _LE("No values returned by %(resource_id)s "
                    "for %(metric_name)s"),
                resource_id=vm.uuid,
                metric_name=self.INSTANCE_CPU_USAGE_METRIC_NAME,
            )
            vm_cpu_utilization = 100

        cpu_capacity = cluster_data_model.get_resource_from_id(
            resource.ResourceType.cpu_cores).get_capacity(vm)

        total_cores_used = cpu_capacity * (vm_cpu_utilization / 100.0)

        return self.calculate_weight(cluster_data_model, vm,
                                     total_cores_used, 0, 0)

    def add_change_service_state(self, resource_id, state):
        parameters = {'state': state}
        self.solution.add_action(action_type=self.CHANGE_NOVA_SERVICE_STATE,
                                 resource_id=resource_id,
                                 input_parameters=parameters)

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

    def score_of_nodes(self, cluster_data_model, score):
        """Calculate score of nodes based on load by VMs"""
        for hypervisor_id in cluster_data_model.get_all_hypervisors():
            hypervisor = cluster_data_model. \
                get_hypervisor_from_id(hypervisor_id)
            count = cluster_data_model.get_mapping(). \
                get_node_vms_from_id(hypervisor_id)
            if len(count) > 0:
                result = self.calculate_score_node(hypervisor,
                                                   cluster_data_model)
            else:
                ''' the hypervisor has not VMs '''
                result = 0
            if len(count) > 0:
                score.append((hypervisor_id, result))
        return score

    def node_and_vm_score(self, sorted_score, score, current_model):
        """Get List of VMs from Node"""
        node_to_release = sorted_score[len(score) - 1][0]
        vms_to_mig = current_model.get_mapping().get_node_vms_from_id(
            node_to_release)

        vm_score = []
        for vm_id in vms_to_mig:
            vm = current_model.get_vm_from_id(vm_id)
            if vm.state == vm_state.VMState.ACTIVE.value:
                vm_score.append(
                    (vm_id, self.calculate_score_vm(vm, current_model)))

        return node_to_release, vm_score

    def create_migration_vm(self, current_model, mig_vm, mig_src_hypervisor,
                            mig_dst_hypervisor):
        """Create migration VM """
        if current_model.get_mapping().migrate_vm(
                mig_vm, mig_src_hypervisor, mig_dst_hypervisor):
            self.add_migration(mig_vm.uuid, 'live',
                               mig_src_hypervisor.uuid,
                               mig_dst_hypervisor.uuid)

        if len(current_model.get_mapping().get_node_vms(
                mig_src_hypervisor)) == 0:
            self.add_change_service_state(mig_src_hypervisor.
                                          uuid,
                                          hyper_state.HypervisorState.
                                          DISABLED.value)
            self.number_of_released_nodes += 1

    def calculate_num_migrations(self, sorted_vms, current_model,
                                 node_to_release, sorted_score):
        number_migrations = 0
        for vm in sorted_vms:
            for j in range(0, len(sorted_score)):
                mig_vm = current_model.get_vm_from_id(vm[0])
                mig_src_hypervisor = current_model.get_hypervisor_from_id(
                    node_to_release)
                mig_dst_hypervisor = current_model.get_hypervisor_from_id(
                    sorted_score[j][0])

                result = self.check_migration(current_model,
                                              mig_src_hypervisor,
                                              mig_dst_hypervisor, mig_vm)
                if result:
                    self.create_migration_vm(
                        current_model, mig_vm,
                        mig_src_hypervisor, mig_dst_hypervisor)
                    number_migrations += 1
                    break
        return number_migrations

    def unsuccessful_migration_actualization(self, number_migrations,
                                             unsuccessful_migration):
        if number_migrations > 0:
            self.number_of_migrations += number_migrations
            return 0
        else:
            return unsuccessful_migration + 1

    def execute(self, original_model):
        LOG.info(_LI("Initializing Sercon Consolidation"))

        if original_model is None:
            raise exception.ClusterStateNotDefined()

        # todo(jed) clone model
        current_model = original_model

        self.efficacy = 100
        unsuccessful_migration = 0

        first_migration = True
        size_cluster = len(current_model.get_all_hypervisors())
        if size_cluster == 0:
            raise exception.ClusterEmpty()

        self.compute_attempts(size_cluster)

        for hypervisor_id in current_model.get_all_hypervisors():
            hypervisor = current_model.get_hypervisor_from_id(hypervisor_id)
            count = current_model.get_mapping(). \
                get_node_vms_from_id(hypervisor_id)
            if len(count) == 0:
                if hypervisor.state == hyper_state.HypervisorState.ENABLED:
                    self.add_change_service_state(hypervisor_id,
                                                  hyper_state.HypervisorState.
                                                  DISABLED.value)

        while self.get_allowed_migration_attempts() >= unsuccessful_migration:
            if not first_migration:
                self.efficacy = self.calculate_migration_efficacy()
                if self.efficacy < float(self.target_efficacy):
                    break
            first_migration = False
            score = []

            score = self.score_of_nodes(current_model, score)

            ''' sort compute nodes by Score decreasing '''''
            sorted_score = sorted(score, reverse=True, key=lambda x: (x[1]))
            LOG.debug("Hypervisor(s) BFD {0}".format(sorted_score))

            ''' get Node to be released '''
            if len(score) == 0:
                LOG.warning(_LW(
                    "The workloads of the compute nodes"
                    " of the cluster is zero"))
                break

            node_to_release, vm_score = self.node_and_vm_score(
                sorted_score, score, current_model)

            ''' sort VMs by Score '''
            sorted_vms = sorted(vm_score, reverse=True, key=lambda x: (x[1]))
            # BFD: Best Fit Decrease
            LOG.debug("VM(s) BFD {0}".format(sorted_vms))

            migrations = self.calculate_num_migrations(
                sorted_vms, current_model, node_to_release, sorted_score)

            unsuccessful_migration = self.unsuccessful_migration_actualization(
                migrations, unsuccessful_migration)
        infos = {
            "number_of_migrations": self.number_of_migrations,
            "number_of_nodes_released": self.number_of_released_nodes,
            "efficacy": self.efficacy
        }
        LOG.debug(infos)
        self.solution.model = current_model
        self.solution.efficacy = self.efficacy
        return self.solution
