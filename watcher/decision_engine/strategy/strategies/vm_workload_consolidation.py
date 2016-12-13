# -*- encoding: utf-8 -*-
#
# Authors: Vojtech CIMA <cima@zhaw.ch>
#          Bruno GRAZIOLI <gaea@zhaw.ch>
#          Sean MURPHY <murp@zhaw.ch>
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
*VM Workload Consolidation Strategy*

A load consolidation strategy based on heuristic first-fit
algorithm which focuses on measured CPU utilization and tries to
minimize hosts which have too much or too little load respecting
resource capacity constraints.

This strategy produces a solution resulting in more efficient
utilization of cluster resources using following four phases:

* Offload phase - handling over-utilized resources
* Consolidation phase - handling under-utilized resources
* Solution optimization - reducing number of migrations
* Disability of unused compute nodes

A capacity coefficients (cc) might be used to adjust optimization
thresholds. Different resources may require different coefficient
values as well as setting up different coefficient values in both
phases may lead to to more efficient consolidation in the end.
If the cc equals 1 the full resource capacity may be used, cc
values lower than 1 will lead to resource under utilization and
values higher than 1 will lead to resource overbooking.
e.g. If targeted utilization is 80 percent of a compute node capacity,
the coefficient in the consolidation phase will be 0.8, but
may any lower value in the offloading phase. The lower it gets
the cluster will appear more released (distributed) for the
following consolidation phase.

As this strategy leverages VM live migration to move the load
from one compute node to another, this feature needs to be set up
correctly on all compute nodes within the cluster.
This strategy assumes it is possible to live migrate any VM from
an active compute node to any other active compute node.
"""

from oslo_log import log
import six

from watcher._i18n import _, _LE, _LI
from watcher.common import exception
from watcher.decision_engine.cluster.history import ceilometer \
    as ceilometer_cluster_history
from watcher.decision_engine.model import element
from watcher.decision_engine.strategy.strategies import base

LOG = log.getLogger(__name__)


class VMWorkloadConsolidation(base.ServerConsolidationBaseStrategy):
    """VM Workload Consolidation Strategy"""

    def __init__(self, config, osc=None):
        super(VMWorkloadConsolidation, self).__init__(config, osc)
        self._ceilometer = None
        self.number_of_migrations = 0
        self.number_of_released_nodes = 0
        self.ceilometer_instance_data_cache = dict()

    @classmethod
    def get_name(cls):
        return "vm_workload_consolidation"

    @classmethod
    def get_display_name(cls):
        return _("VM Workload Consolidation Strategy")

    @classmethod
    def get_translatable_display_name(cls):
        return "VM Workload Consolidation Strategy"

    @property
    def ceilometer(self):
        if self._ceilometer is None:
            self._ceilometer = (ceilometer_cluster_history.
                                CeilometerClusterHistory(osc=self.osc))
        return self._ceilometer

    @ceilometer.setter
    def ceilometer(self, ceilometer):
        self._ceilometer = ceilometer

    def get_state_str(self, state):
        """Get resource state in string format.

        :param state: resource state of unknown type
        """
        if isinstance(state, six.string_types):
            return state
        elif isinstance(state, (element.InstanceState, element.ServiceState)):
            return state.value
        else:
            LOG.error(_LE('Unexpexted resource state type, '
                          'state=%(state)s, state_type=%(st)s.'),
                      state=state,
                      st=type(state))
            raise exception.WatcherException

    def add_action_enable_compute_node(self, node):
        """Add an action for node enabler into the solution.

        :param node: node object
        :return: None
        """
        params = {'state': element.ServiceState.ENABLED.value}
        self.solution.add_action(
            action_type='change_nova_service_state',
            resource_id=node.uuid,
            input_parameters=params)
        self.number_of_released_nodes -= 1

    def add_action_disable_node(self, node):
        """Add an action for node disability into the solution.

        :param node: node object
        :return: None
        """
        params = {'state': element.ServiceState.DISABLED.value}
        self.solution.add_action(
            action_type='change_nova_service_state',
            resource_id=node.uuid,
            input_parameters=params)
        self.number_of_released_nodes += 1

    def add_migration(self, instance_uuid, source_node,
                      destination_node, model):
        """Add an action for VM migration into the solution.

        :param instance_uuid: instance uuid
        :param source_node: node object
        :param destination_node: node object
        :param model: model_root object
        :return: None
        """
        instance = model.get_instance_by_uuid(instance_uuid)

        instance_state_str = self.get_state_str(instance.state)
        if instance_state_str != element.InstanceState.ACTIVE.value:
            # Watcher curently only supports live VM migration and block live
            # VM migration which both requires migrated VM to be active.
            # When supported, the cold migration may be used as a fallback
            # migration mechanism to move non active VMs.
            LOG.error(
                _LE('Cannot live migrate: instance_uuid=%(instance_uuid)s, '
                    'state=%(instance_state)s.'),
                instance_uuid=instance_uuid,
                instance_state=instance_state_str)
            return

        migration_type = 'live'

        destination_node_state_str = self.get_state_str(destination_node.state)
        if destination_node_state_str == element.ServiceState.DISABLED.value:
            self.add_action_enable_compute_node(destination_node)
        model.mapping.unmap(source_node, instance)
        model.mapping.map(destination_node, instance)

        params = {'migration_type': migration_type,
                  'source_node': source_node.uuid,
                  'destination_node': destination_node.uuid}
        self.solution.add_action(action_type='migrate',
                                 resource_id=instance.uuid,
                                 input_parameters=params)
        self.number_of_migrations += 1

    def disable_unused_nodes(self, model):
        """Generate actions for disablity of unused nodes.

        :param model: model_root object
        :return: None
        """
        for node in model.get_all_compute_nodes().values():
            if (len(model.mapping.get_node_instances(node)) == 0 and
                    node.status !=
                    element.ServiceState.DISABLED.value):
                self.add_action_disable_node(node)

    def get_instance_utilization(self, instance_uuid, model,
                                 period=3600, aggr='avg'):
        """Collect cpu, ram and disk utilization statistics of a VM.

        :param instance_uuid: instance object
        :param model: model_root object
        :param period: seconds
        :param aggr: string
        :return: dict(cpu(number of vcpus used), ram(MB used), disk(B used))
        """
        if instance_uuid in self.ceilometer_instance_data_cache.keys():
            return self.ceilometer_instance_data_cache.get(instance_uuid)

        cpu_util_metric = 'cpu_util'
        ram_util_metric = 'memory.usage'

        ram_alloc_metric = 'memory'
        disk_alloc_metric = 'disk.root.size'
        instance_cpu_util = self.ceilometer.statistic_aggregation(
            resource_id=instance_uuid, meter_name=cpu_util_metric,
            period=period, aggregate=aggr)
        instance_cpu_cores = model.get_resource_by_uuid(
            element.ResourceType.cpu_cores).get_capacity(
                model.get_instance_by_uuid(instance_uuid))

        if instance_cpu_util:
            total_cpu_utilization = (
                instance_cpu_cores * (instance_cpu_util / 100.0))
        else:
            total_cpu_utilization = instance_cpu_cores

        instance_ram_util = self.ceilometer.statistic_aggregation(
            resource_id=instance_uuid, meter_name=ram_util_metric,
            period=period, aggregate=aggr)

        if not instance_ram_util:
            instance_ram_util = self.ceilometer.statistic_aggregation(
                resource_id=instance_uuid, meter_name=ram_alloc_metric,
                period=period, aggregate=aggr)

        instance_disk_util = self.ceilometer.statistic_aggregation(
            resource_id=instance_uuid, meter_name=disk_alloc_metric,
            period=period, aggregate=aggr)

        if not instance_ram_util or not instance_disk_util:
            LOG.error(
                _LE('No values returned by %(resource_id)s '
                    'for memory.usage or disk.root.size'),
                resource_id=instance_uuid
            )
            raise exception.NoDataFound

        self.ceilometer_instance_data_cache[instance_uuid] = dict(
            cpu=total_cpu_utilization, ram=instance_ram_util,
            disk=instance_disk_util)
        return self.ceilometer_instance_data_cache.get(instance_uuid)

    def get_node_utilization(self, node, model, period=3600, aggr='avg'):
        """Collect cpu, ram and disk utilization statistics of a node.

        :param node: node object
        :param model: model_root object
        :param period: seconds
        :param aggr: string
        :return: dict(cpu(number of cores used), ram(MB used), disk(B used))
        """
        node_instances = model.mapping.get_node_instances_by_uuid(
            node.uuid)
        node_ram_util = 0
        node_disk_util = 0
        node_cpu_util = 0
        for instance_uuid in node_instances:
            instance_util = self.get_instance_utilization(
                instance_uuid, model, period, aggr)
            node_cpu_util += instance_util['cpu']
            node_ram_util += instance_util['ram']
            node_disk_util += instance_util['disk']

        return dict(cpu=node_cpu_util, ram=node_ram_util,
                    disk=node_disk_util)

    def get_node_capacity(self, node, model):
        """Collect cpu, ram and disk capacity of a node.

        :param node: node object
        :param model: model_root object
        :return: dict(cpu(cores), ram(MB), disk(B))
        """
        node_cpu_capacity = model.get_resource_by_uuid(
            element.ResourceType.cpu_cores).get_capacity(node)

        node_disk_capacity = model.get_resource_by_uuid(
            element.ResourceType.disk_capacity).get_capacity(node)

        node_ram_capacity = model.get_resource_by_uuid(
            element.ResourceType.memory).get_capacity(node)
        return dict(cpu=node_cpu_capacity, ram=node_ram_capacity,
                    disk=node_disk_capacity)

    def get_relative_node_utilization(self, node, model):
        """Return relative node utilization (rhu).

        :param node: node object
        :param model: model_root object
        :return: {'cpu': <0,1>, 'ram': <0,1>, 'disk': <0,1>}
        """
        rhu = {}
        util = self.get_node_utilization(node, model)
        cap = self.get_node_capacity(node, model)
        for k in util.keys():
            rhu[k] = float(util[k]) / float(cap[k])
        return rhu

    def get_relative_cluster_utilization(self, model):
        """Calculate relative cluster utilization (rcu).

        RCU is an average of relative utilizations (rhu) of active nodes.
        :param model: model_root object
        :return: {'cpu': <0,1>, 'ram': <0,1>, 'disk': <0,1>}
        """
        nodes = model.get_all_compute_nodes().values()
        rcu = {}
        counters = {}
        for node in nodes:
            node_state_str = self.get_state_str(node.state)
            if node_state_str == element.ServiceState.ENABLED.value:
                rhu = self.get_relative_node_utilization(
                    node, model)
                for k in rhu.keys():
                    if k not in rcu:
                        rcu[k] = 0
                    if k not in counters:
                        counters[k] = 0
                    rcu[k] += rhu[k]
                    counters[k] += 1
        for k in rcu.keys():
            rcu[k] /= counters[k]
        return rcu

    def is_overloaded(self, node, model, cc):
        """Indicate whether a node is overloaded.

        This considers provided resource capacity coefficients (cc).
        :param node: node object
        :param model: model_root object
        :param cc: dictionary containing resource capacity coefficients
        :return: [True, False]
        """
        node_capacity = self.get_node_capacity(node, model)
        node_utilization = self.get_node_utilization(
            node, model)
        metrics = ['cpu']
        for m in metrics:
            if node_utilization[m] > node_capacity[m] * cc[m]:
                return True
        return False

    def instance_fits(self, instance_uuid, node, model, cc):
        """Indicate whether is a node able to accommodate a VM.

        This considers provided resource capacity coefficients (cc).
        :param instance_uuid: string
        :param node: node object
        :param model: model_root object
        :param cc: dictionary containing resource capacity coefficients
        :return: [True, False]
        """
        node_capacity = self.get_node_capacity(node, model)
        node_utilization = self.get_node_utilization(
            node, model)
        instance_utilization = self.get_instance_utilization(
            instance_uuid, model)
        metrics = ['cpu', 'ram', 'disk']
        for m in metrics:
            if (instance_utilization[m] + node_utilization[m] >
                    node_capacity[m] * cc[m]):
                return False
        return True

    def optimize_solution(self, model):
        """Optimize solution.

        This is done by eliminating unnecessary or circular set of migrations
        which can be replaced by a more efficient solution.
        e.g.:

        * A->B, B->C => replace migrations A->B, B->C with
          a single migration A->C as both solution result in
          VM running on node C which can be achieved with
          one migration instead of two.
        * A->B, B->A => remove A->B and B->A as they do not result
          in a new VM placement.

        :param model: model_root object
        """
        migrate_actions = (
            a for a in self.solution.actions if a[
                'action_type'] == 'migrate')
        instance_to_be_migrated = (
            a['input_parameters']['resource_id'] for a in migrate_actions)
        instance_uuids = list(set(instance_to_be_migrated))
        for instance_uuid in instance_uuids:
            actions = list(
                a for a in self.solution.actions if a[
                    'input_parameters'][
                        'resource_id'] == instance_uuid)
            if len(actions) > 1:
                src = actions[0]['input_parameters']['source_node']
                dst = actions[-1]['input_parameters']['destination_node']
                for a in actions:
                    self.solution.actions.remove(a)
                    self.number_of_migrations -= 1
                if src != dst:
                    self.add_migration(instance_uuid, src, dst, model)

    def offload_phase(self, model, cc):
        """Perform offloading phase.

        This considers provided resource capacity coefficients.
        Offload phase performing first-fit based bin packing to offload
        overloaded nodes. This is done in a fashion of moving
        the least CPU utilized VM first as live migration these
        generaly causes less troubles. This phase results in a cluster
        with no overloaded nodes.
        * This phase is be able to enable disabled nodes (if needed
        and any available) in the case of the resource capacity provided by
        active nodes is not able to accomodate all the load.
        As the offload phase is later followed by the consolidation phase,
        the node enabler in this phase doesn't necessarily results
        in more enabled nodes in the final solution.

        :param model: model_root object
        :param cc: dictionary containing resource capacity coefficients
        """
        sorted_nodes = sorted(
            model.get_all_compute_nodes().values(),
            key=lambda x: self.get_node_utilization(x, model)['cpu'])
        for node in reversed(sorted_nodes):
            if self.is_overloaded(node, model, cc):
                for instance in sorted(
                        model.mapping.get_node_instances(node),
                        key=lambda x: self.get_instance_utilization(
                            x, model)['cpu']
                ):
                    for destination_node in reversed(sorted_nodes):
                        if self.instance_fits(
                                instance, destination_node, model, cc):
                            self.add_migration(instance, node,
                                               destination_node, model)
                            break
                    if not self.is_overloaded(node, model, cc):
                        break

    def consolidation_phase(self, model, cc):
        """Perform consolidation phase.

        This considers provided resource capacity coefficients.
        Consolidation phase performing first-fit based bin packing.
        First, nodes with the lowest cpu utilization are consolidated
        by moving their load to nodes with the highest cpu utilization
        which can accomodate the load. In this phase the most cpu utilizied
        VMs are prioritizied as their load is more difficult to accomodate
        in the system than less cpu utilizied VMs which can be later used
        to fill smaller CPU capacity gaps.

        :param model: model_root object
        :param cc: dictionary containing resource capacity coefficients
        """
        sorted_nodes = sorted(
            model.get_all_compute_nodes().values(),
            key=lambda x: self.get_node_utilization(x, model)['cpu'])
        asc = 0
        for node in sorted_nodes:
            instances = sorted(
                model.mapping.get_node_instances(node),
                key=lambda x: self.get_instance_utilization(x, model)['cpu'])
            for instance in reversed(instances):
                dsc = len(sorted_nodes) - 1
                for destination_node in reversed(sorted_nodes):
                    if asc >= dsc:
                        break
                    if self.instance_fits(
                            instance, destination_node, model, cc):
                        self.add_migration(instance, node,
                                           destination_node, model)
                        break
                    dsc -= 1
            asc += 1

    def pre_execute(self):
        if not self.compute_model:
            raise exception.ClusterStateNotDefined()

        if self.compute_model.stale:
            raise exception.ClusterStateStale()

        LOG.debug(self.compute_model.to_string())

    def do_execute(self):
        """Execute strategy.

        This strategy produces a solution resulting in more
        efficient utilization of cluster resources using following
        four phases:

        * Offload phase - handling over-utilized resources
        * Consolidation phase - handling under-utilized resources
        * Solution optimization - reducing number of migrations
        * Disability of unused nodes

        :param original_model: root_model object
        """
        LOG.info(_LI('Executing Smart Strategy'))
        model = self.compute_model
        rcu = self.get_relative_cluster_utilization(model)
        self.ceilometer_vm_data_cache = dict()

        cc = {'cpu': 1.0, 'ram': 1.0, 'disk': 1.0}

        # Offloading phase
        self.offload_phase(model, cc)

        # Consolidation phase
        self.consolidation_phase(model, cc)

        # Optimize solution
        self.optimize_solution(model)

        # disable unused nodes
        self.disable_unused_nodes(model)

        rcu_after = self.get_relative_cluster_utilization(model)
        info = {
            'number_of_migrations': self.number_of_migrations,
            'number_of_released_nodes':
                self.number_of_released_nodes,
            'relative_cluster_utilization_before': str(rcu),
            'relative_cluster_utilization_after': str(rcu_after)
        }

        LOG.debug(info)

    def post_execute(self):
        self.solution.set_efficacy_indicators(
            released_compute_nodes_count=self.number_of_released_nodes,
            instance_migrations_count=self.number_of_migrations,
        )

        LOG.debug(self.compute_model.to_string())
