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

from dateutil.parser import parse

from oslo_log import log

from cinderclient.v3.volumes import Volume
from novaclient.v2.servers import Server
from watcher._i18n import _
from watcher.common import cinder_helper
from watcher.common import nova_helper
from watcher.decision_engine.model import element
from watcher.decision_engine.strategy.strategies import base

LOG = log.getLogger(__name__)

INSTANCE = "instance"
VOLUME = "volume"
ACTIVE = "active"
PAUSED = 'paused'
STOPPED = "stopped"
status_ACTIVE = 'ACTIVE'
status_PAUSED = 'PAUSED'
status_SHUTOFF = 'SHUTOFF'
AVAILABLE = "available"
IN_USE = "in-use"


class ZoneMigration(base.ZoneMigrationBaseStrategy):
    """Zone migration using instance and volume migration

    This is zone migration strategy to migrate many instances and volumes
    efficiently with minimum downtime for hardware maintenance.
    """

    def __init__(self, config, osc=None):

        super(ZoneMigration, self).__init__(config, osc)
        self._nova = None
        self._cinder = None

        self.live_count = 0
        self.planned_live_count = 0
        self.cold_count = 0
        self.planned_cold_count = 0
        self.volume_count = 0
        self.planned_volume_count = 0

    # TODO(sean-n-mooney) This is backward compatibility
    # for calling the swap code paths. Swap is now an alias
    # for migrate, we should clean this up in a future
    # cycle.
    @property
    def volume_update_count(self):
        return self.volume_count

    # same as above clean up later.
    @property
    def planned_volume_update_count(self):
        return self.planned_volume_count

    @classmethod
    def get_name(cls):
        return "zone_migration"

    @classmethod
    def get_display_name(cls):
        return _("Zone migration")

    @classmethod
    def get_translatable_display_name(cls):
        return "Zone migration"

    @classmethod
    def get_schema(cls):
        return {
            "properties": {
                "compute_nodes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "src_node": {
                                "description": "Compute node from which"
                                               " instances migrate",
                                "type": "string"
                            },
                            "dst_node": {
                                "description": "Compute node to which "
                                               "instances migrate",
                                "type": "string"
                            }
                        },
                        "required": ["src_node"],
                        "additionalProperties": False
                    }
                },
                "storage_pools": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "src_pool": {
                                "description": "Storage pool from which"
                                               " volumes migrate",
                                "type": "string"
                            },
                            "dst_pool": {
                                "description": "Storage pool to which"
                                               " volumes migrate",
                                "type": "string"
                            },
                            "src_type": {
                                "description": "Volume type from which"
                                               " volumes migrate",
                                "type": "string"
                            },
                            "dst_type": {
                                "description": "Volume type to which"
                                               " volumes migrate",
                                "type": "string"
                            }
                        },
                        "required": ["src_pool", "src_type", "dst_type"],
                        "additionalProperties": False
                    }
                },
                "parallel_total": {
                    "description": "The number of actions to be run in"
                                   " parallel in total",
                    "type": "integer", "minimum": 0, "default": 6
                },
                "parallel_per_node": {
                    "description": "The number of actions to be run in"
                                   " parallel per compute node",
                    "type": "integer", "minimum": 0, "default": 2
                },
                "parallel_per_pool": {
                    "description": "The number of actions to be run in"
                                   " parallel per storage host",
                    "type": "integer", "minimum": 0, "default": 2
                },
                "priority": {
                    "description": "List prioritizes instances and volumes",
                    "type": "object",
                    "properties": {
                        "project": {
                            "type": "array", "items": {"type": "string"}
                        },
                        "compute_node": {
                            "type": "array", "items": {"type": "string"}
                        },
                        "storage_pool": {
                            "type": "array", "items": {"type": "string"}
                        },
                        "compute": {
                            "enum": ["vcpu_num", "mem_size", "disk_size",
                                     "created_at"]
                        },
                        "storage": {
                            "enum": ["size", "created_at"]
                        }
                    },
                    "additionalProperties": False
                },
                "with_attached_volume": {
                    "description": "instance migrates just after attached"
                                   " volumes or not",
                    "type": "boolean", "default": False
                },
            },
            "additionalProperties": False
        }

    @property
    def migrate_compute_nodes(self):
        """Get compute nodes from input_parameters

        :returns: compute nodes
                  e.g. [{"src_node": "w012", "dst_node": "w022"},
                        {"src_node": "w013", "dst_node": "w023"}]
        """

        return self.input_parameters.get('compute_nodes')

    @property
    def migrate_storage_pools(self):
        """Get storage pools from input_parameters

        :returns: storage pools
                  e.g. [
                         {"src_pool": "src1@back1#pool1",
                          "dst_pool": "dst1@back1#pool1",
                          "src_type": "src1_type",
                          "dst_type": "dst1_type"},
                         {"src_pool": "src1@back2#pool1",
                          "dst_pool": "dst1@back2#pool1",
                          "src_type": "src1_type",
                          "dst_type": "dst1_type"}
                       ]
        """

        return self.input_parameters.get('storage_pools')

    @property
    def parallel_total(self):
        return self.input_parameters.get('parallel_total')

    @property
    def parallel_per_node(self):
        return self.input_parameters.get('parallel_per_node')

    @property
    def parallel_per_pool(self):
        return self.input_parameters.get('parallel_per_pool')

    @property
    def priority(self):
        """Get priority from input_parameters

        :returns: priority map
                  e.g.
                  {
                      "project": ["pj1"],
                      "compute_node": ["compute1", "compute2"],
                      "compute": ["vcpu_num"],
                      "storage_pool": ["pool1", "pool2"],
                      "storage": ["size", "created_at"]
                  }
        """

        return self.input_parameters.get('priority')

    @property
    def with_attached_volume(self):
        return self.input_parameters.get('with_attached_volume')

    @property
    def nova(self):
        if self._nova is None:
            self._nova = nova_helper.NovaHelper(osc=self.osc)
        return self._nova

    @property
    def cinder(self):
        if self._cinder is None:
            self._cinder = cinder_helper.CinderHelper(osc=self.osc)
        return self._cinder

    def get_available_compute_nodes(self):
        default_node_scope = [element.ServiceState.ENABLED.value,
                              element.ServiceState.DISABLED.value]
        return {uuid: cn for uuid, cn in
                self.compute_model.get_all_compute_nodes().items()
                if cn.state == element.ServiceState.ONLINE.value and
                cn.status in default_node_scope}

    def get_available_storage_nodes(self):
        default_node_scope = [element.ServiceState.ENABLED.value,
                              element.ServiceState.DISABLED.value]
        return {uuid: cn for uuid, cn in
                self.storage_model.get_all_storage_nodes().items()
                if cn.state == element.ServiceState.ONLINE.value and
                cn.status in default_node_scope}

    def pre_execute(self):
        self._pre_execute()
        LOG.debug(self.storage_model.to_string())

    def do_execute(self, audit=None):
        """Strategy execution phase

        """
        filtered_targets = self.filtered_targets()
        self.set_migration_count(filtered_targets)

        total_limit = self.parallel_total
        per_node_limit = self.parallel_per_node
        per_pool_limit = self.parallel_per_pool
        action_counter = ActionCounter(total_limit,
                                       per_pool_limit, per_node_limit)

        for k, targets in iter(filtered_targets.items()):
            if k == VOLUME:
                self.volumes_migration(targets, action_counter)
            elif k == INSTANCE:
                if self.volume_count == 0 and self.volume_update_count == 0:
                    # if with_attached_volume is true,
                    # instance having attached volumes already migrated,
                    # migrate instances which does not have attached volumes
                    if self.with_attached_volume:
                        targets = self.instances_no_attached(targets)
                        self.instances_migration(targets, action_counter)
                    else:
                        self.instances_migration(targets, action_counter)

        LOG.debug("action total: %s, pools: %s, nodes %s ",
                  action_counter.total_count,
                  action_counter.per_pool_count,
                  action_counter.per_node_count)

    def post_execute(self):
        """Post-execution phase

        This can be used to compute the global efficacy
        """
        self.solution.set_efficacy_indicators(
            live_migrate_instance_count=self.live_count,
            planned_live_migrate_instance_count=self.planned_live_count,
            cold_migrate_instance_count=self.cold_count,
            planned_cold_migrate_instance_count=self.planned_cold_count,
            volume_migrate_count=self.volume_count,
            planned_volume_migrate_count=self.planned_volume_count,
            volume_update_count=self.volume_count,
            planned_volume_update_count=self.planned_volume_count
        )

    def set_migration_count(self, targets):
        """Set migration count

        :param targets: dict of instance object and volume object list
                        keys of dict are instance and volume
        """
        for instance in targets.get('instance', []):
            if self.is_live(instance):
                self.live_count += 1
            elif self.is_cold(instance):
                self.cold_count += 1
        for volume in targets.get('volume', []):
            self.volume_count += 1

    def is_live(self, instance):
        status = getattr(instance, 'status')
        state = getattr(instance, 'OS-EXT-STS:vm_state')
        return (status == status_ACTIVE and state == ACTIVE
                ) or (status == status_PAUSED and state == PAUSED)

    def is_cold(self, instance):
        status = getattr(instance, 'status')
        state = getattr(instance, 'OS-EXT-STS:vm_state')
        return status == status_SHUTOFF and state == STOPPED

    def is_available(self, volume):
        return getattr(volume, 'status') == AVAILABLE

    def is_in_use(self, volume):
        return getattr(volume, 'status') == IN_USE

    def instances_no_attached(self, instances):
        return [i for i in instances
                if not getattr(i, "os-extended-volumes:volumes_attached")]

    def get_host_by_pool(self, pool):
        """Get host name from pool name

        Utility method to get host name from pool name
        which is formatted as host@backend#pool.

        :param pool: pool name
        :returns: host name
        """
        return pool.split('@')[0]

    def get_dst_node(self, src_node):
        """Get destination node from self.migration_compute_nodes

        :param src_node: compute node name
        :returns: destination node name
        """
        for node in self.migrate_compute_nodes:
            if node.get("src_node") == src_node:
                return node.get("dst_node")

    def get_dst_pool_and_type(self, src_pool, src_type):
        """Get destination pool and type from self.migration_storage_pools

        :param src_pool: storage pool name
        :param src_type: storage volume type
        :returns: set of storage pool name and volume type name
        """
        for pool in self.migrate_storage_pools:
            if pool.get("src_pool") == src_pool:
                return (pool.get("dst_pool", None),
                        pool.get("dst_type"))

    def volumes_migration(self, volumes, action_counter):
        for volume in volumes:
            if action_counter.is_total_max():
                LOG.debug('total reached limit')
                break

            pool = getattr(volume, 'os-vol-host-attr:host')
            if action_counter.is_pool_max(pool):
                LOG.debug("%s has objects to be migrated, but it has"
                          " reached the limit of parallelization.", pool)
                continue

            src_type = volume.volume_type
            dst_pool, dst_type = self.get_dst_pool_and_type(pool, src_type)
            LOG.debug(src_type)
            LOG.debug("%s %s", dst_pool, dst_type)

            if src_type == dst_type:
                self._volume_migrate(volume, dst_pool)
            else:
                self._volume_retype(volume, dst_type)

            # if with_attached_volume is True, migrate attaching instances
            if self.with_attached_volume:
                instances = [self.nova.find_instance(dic.get('server_id'))
                             for dic in volume.attachments]
                self.instances_migration(instances, action_counter)

            action_counter.add_pool(pool)

    def instances_migration(self, instances, action_counter):

        for instance in instances:
            src_node = getattr(instance, 'OS-EXT-SRV-ATTR:host')

            if action_counter.is_total_max():
                LOG.debug('total reached limit')
                break

            if action_counter.is_node_max(src_node):
                LOG.debug("%s has objects to be migrated, but it has"
                          " reached the limit of parallelization.", src_node)
                continue

            dst_node = self.get_dst_node(src_node)
            if self.is_live(instance):
                self._live_migration(instance, src_node, dst_node)
            elif self.is_cold(instance):
                self._cold_migration(instance, src_node, dst_node)

            action_counter.add_node(src_node)

    def _live_migration(self, instance, src_node, dst_node):
        parameters = {"migration_type": "live",
                      "destination_node": dst_node,
                      "source_node": src_node,
                      "resource_name": instance.name}
        self.solution.add_action(
            action_type="migrate",
            resource_id=instance.id,
            input_parameters=parameters)
        self.planned_live_count += 1

    def _cold_migration(self, instance, src_node, dst_node):
        parameters = {"migration_type": "cold",
                      "destination_node": dst_node,
                      "source_node": src_node,
                      "resource_name": instance.name}
        self.solution.add_action(
            action_type="migrate",
            resource_id=instance.id,
            input_parameters=parameters)
        self.planned_cold_count += 1

    def _volume_migrate(self, volume, dst_pool):
        parameters = {"migration_type": "migrate",
                      "destination_node": dst_pool,
                      "resource_name": volume.name}
        self.solution.add_action(
            action_type="volume_migrate",
            resource_id=volume.id,
            input_parameters=parameters)
        self.planned_volume_count += 1

    def _volume_retype(self, volume, dst_type):
        parameters = {"migration_type": "retype",
                      "destination_type": dst_type,
                      "resource_name": volume.name}
        self.solution.add_action(
            action_type="volume_migrate",
            resource_id=volume.id,
            input_parameters=parameters)
        self.planned_volume_count += 1

    def get_src_node_list(self):
        """Get src nodes from migrate_compute_nodes

        :returns: src node name list
        """
        if not self.migrate_compute_nodes:
            return None

        return [v for dic in self.migrate_compute_nodes
                for k, v in dic.items() if k == "src_node"]

    def get_src_pool_list(self):
        """Get src pools from migrate_storage_pools

        :returns: src pool name list
        """

        return [v for dic in self.migrate_storage_pools
                for k, v in dic.items() if k == "src_pool"]

    def get_instances(self):
        """Get migrate target instances

        :returns: instance list on src nodes and compute scope
        """

        src_node_list = self.get_src_node_list()

        if not src_node_list:
            return None

        return [i for i in self.nova.get_instance_list()
                if getattr(i, 'OS-EXT-SRV-ATTR:host') in src_node_list and
                self.compute_model.get_instance_by_uuid(i.id)]

    def get_volumes(self):
        """Get migrate target volumes

        :returns: volume list on src pools and storage scope
        """

        src_pool_list = self.get_src_pool_list()

        return [i for i in self.cinder.get_volume_list()
                if getattr(i, 'os-vol-host-attr:host') in src_pool_list and
                self.storage_model.get_volume_by_uuid(i.id)]

    def filtered_targets(self):
        """Filter targets

        prioritize instances and volumes based on priorities
        from input parameters.

        :returns: prioritized targets
        """
        result = {}

        if self.migrate_compute_nodes:
            result["instance"] = self.get_instances()

        if self.migrate_storage_pools:
            result["volume"] = self.get_volumes()

        if not self.priority:
            return result

        filter_actions = self.get_priority_filter_list()
        LOG.debug(filter_actions)

        # apply all filters set in input parameter
        for action in list(reversed(filter_actions)):
            LOG.debug(action)
            result = action.apply_filter(result)

        return result

    def get_priority_filter_list(self):
        """Get priority filters

        :returns: list of filter object with arguments in self.priority
        """

        filter_list = []
        priority_filter_map = self.get_priority_filter_map()

        for k, v in iter(self.priority.items()):
            if k in priority_filter_map:
                filter_list.append(priority_filter_map[k](v))

        return filter_list

    def get_priority_filter_map(self):
        """Get priority filter map

        :returns: filter map
                  key is the key in priority input parameters.
                  value is filter class for prioritizing.
        """

        return {
            "project": ProjectSortFilter,
            "compute_node": ComputeHostSortFilter,
            "storage_pool": StorageHostSortFilter,
            "compute": ComputeSpecSortFilter,
            "storage": StorageSpecSortFilter,
        }


class ActionCounter(object):
    """Manage the number of actions in parallel"""

    def __init__(self, total_limit=6, per_pool_limit=2, per_node_limit=2):
        """Initialize dict of host and the number of action

        :param total_limit: total number of actions
        :param per_pool_limit: the number of migrate actions per storage pool
        :param per_node_limit: the number of migrate actions per compute node
        """
        self.total_limit = total_limit
        self.per_pool_limit = per_pool_limit
        self.per_node_limit = per_node_limit
        self.per_pool_count = {}
        self.per_node_count = {}
        self.total_count = 0

    def add_pool(self, pool):
        """Increment the number of actions on host and total count

        :param pool: storage pool
        :returns: True if incremented, False otherwise
        """
        if pool not in self.per_pool_count:
            self.per_pool_count[pool] = 0

        if not self.is_total_max() and not self.is_pool_max(pool):
            self.per_pool_count[pool] += 1
            self.total_count += 1
            LOG.debug("total: %s, per_pool: %s",
                      self.total_count, self.per_pool_count)
            return True
        return False

    def add_node(self, node):
        """Add the number of actions on node

        :param host: compute node
        :returns: True if action can be added, False otherwise
        """
        if node not in self.per_node_count:
            self.per_node_count[node] = 0

        if not self.is_total_max() and not self.is_node_max(node):
            self.per_node_count[node] += 1
            self.total_count += 1
            LOG.debug("total: %s, per_node: %s",
                      self.total_count, self.per_node_count)
            return True
        return False

    def is_total_max(self):
        """Check if total count reached limit

        :returns: True if total count reached limit, False otherwise
        """
        return self.total_count >= self.total_limit

    def is_pool_max(self, pool):
        """Check if per pool count reached limit

        :returns: True if count reached limit, False otherwise
        """
        if pool not in self.per_pool_count:
            self.per_pool_count[pool] = 0
        LOG.debug("the number of parallel per pool %s is %s ",
                  pool, self.per_pool_count[pool])
        LOG.debug("per pool limit is %s", self.per_pool_limit)
        return self.per_pool_count[pool] >= self.per_pool_limit

    def is_node_max(self, node):
        """Check if per node count reached limit

        :returns: True if count reached limit, False otherwise
        """
        if node not in self.per_node_count:
            self.per_node_count[node] = 0
        return self.per_node_count[node] >= self.per_node_limit


class BaseFilter(object):
    """Base class for Filter"""

    apply_targets = ('ALL',)

    def __init__(self, values=[], **kwargs):
        """initialization

        :param values: priority value
        """

        if not isinstance(values, list):
            values = [values]

        self.condition = values

    def apply_filter(self, targets):
        """apply filter to targets

        :param targets: dict of instance object and volume object list
                        keys of dict are instance and volume
        """

        if not targets:
            return {}

        for cond in list(reversed(self.condition)):
            for k, v in iter(targets.items()):
                if not self.is_allowed(k):
                    continue
                LOG.debug("filter:%s with the key: %s", cond, k)
                targets[k] = self.exec_filter(v, cond)

        LOG.debug(targets)
        return targets

    def is_allowed(self, key):
        return (key in self.apply_targets) or ('ALL' in self.apply_targets)

    def exec_filter(self, items, sort_key):
        """This is implemented by sub class"""
        return items


class SortMovingToFrontFilter(BaseFilter):
    """This is to move to front if a condition is True"""

    def exec_filter(self, items, sort_key):
        return self.sort_moving_to_front(items,
                                         sort_key,
                                         self.compare_func)

    def sort_moving_to_front(self, items, sort_key=None, compare_func=None):
        if not compare_func or not sort_key:
            return items

        for item in list(reversed(items)):
            if compare_func(item, sort_key):
                items.remove(item)
                items.insert(0, item)
        return items

    def compare_func(self, item, sort_key):
        return True


class ProjectSortFilter(SortMovingToFrontFilter):
    """ComputeHostSortFilter"""

    apply_targets = ('instance', 'volume')

    def __init__(self, values=[], **kwargs):
        super(ProjectSortFilter, self).__init__(values, **kwargs)

    def compare_func(self, item, sort_key):
        """Compare project id of item with sort_key

        :param item: instance object or volume object
        :param sort_key: project id
        :returns: true: project id of item equals sort_key
                  false: otherwise
        """

        project_id = self.get_project_id(item)
        LOG.debug("project_id: %s, sort_key: %s", project_id, sort_key)
        return project_id == sort_key

    def get_project_id(self, item):
        """get project id of item

        :param item: instance object or volume object
        :returns: project id
        """

        if isinstance(item, Volume):
            return getattr(item, 'os-vol-tenant-attr:tenant_id')
        elif isinstance(item, Server):
            return item.tenant_id


class ComputeHostSortFilter(SortMovingToFrontFilter):
    """ComputeHostSortFilter"""

    apply_targets = ('instance',)

    def __init__(self, values=[], **kwargs):
        super(ComputeHostSortFilter, self).__init__(values, **kwargs)

    def compare_func(self, item, sort_key):
        """Compare compute name of item with sort_key

        :param item: instance object
        :param sort_key: compute host name
        :returns: true: compute name on where instance host equals sort_key
                  false: otherwise
        """

        host = self.get_host(item)
        LOG.debug("host: %s, sort_key: %s", host, sort_key)
        return host == sort_key

    def get_host(self, item):
        """get hostname on which item is

        :param item: instance object
        :returns: hostname on which item is
        """

        return getattr(item, 'OS-EXT-SRV-ATTR:host')


class StorageHostSortFilter(SortMovingToFrontFilter):
    """StoragehostSortFilter"""

    apply_targets = ('volume',)

    def compare_func(self, item, sort_key):
        """Compare pool name of item with sort_key

        :param item: volume object
        :param sort_key: storage pool name
        :returns: true: pool name on where instance.host equals sort_key
                  false: otherwise
        """

        host = self.get_host(item)
        LOG.debug("host: %s, sort_key: %s", host, sort_key)
        return host == sort_key

    def get_host(self, item):
        return getattr(item, 'os-vol-host-attr:host')


class ComputeSpecSortFilter(BaseFilter):
    """ComputeSpecSortFilter"""

    apply_targets = ('instance',)
    accept_keys = ['vcpu_num', 'mem_size', 'disk_size', 'created_at']

    def __init__(self, values=[], **kwargs):
        super(ComputeSpecSortFilter, self).__init__(values, **kwargs)
        self._nova = None

    @property
    def nova(self):
        if self._nova is None:
            self._nova = nova_helper.NovaHelper()
        return self._nova

    def exec_filter(self, items, sort_key):
        result = items

        if sort_key not in self.accept_keys:
            LOG.warning("Invalid key is specified: %s", sort_key)
        else:
            result = self.get_sorted_items(items, sort_key)

        return result

    def get_sorted_items(self, items, sort_key):
        """Sort items by sort_key

        :param items: instances
        :param sort_key: sort_key
        :returns: items sorted by sort_key
        """

        result = items
        flavors = self.nova.get_flavor_list()

        if sort_key == 'mem_size':
            result = sorted(items,
                            key=lambda x: float(self.get_mem_size(x, flavors)),
                            reverse=True)
        elif sort_key == 'vcpu_num':
            result = sorted(items,
                            key=lambda x: float(self.get_vcpu_num(x, flavors)),
                            reverse=True)
        elif sort_key == 'disk_size':
            result = sorted(items,
                            key=lambda x: float(
                                self.get_disk_size(x, flavors)),
                            reverse=True)
        elif sort_key == 'created_at':
            result = sorted(items,
                            key=lambda x: parse(getattr(x, sort_key)),
                            reverse=False)

        return result

    def get_mem_size(self, item, flavors):
        """Get memory size of item

        :param item: instance
        :param flavors: flavors
        :returns: memory size of item
        """

        LOG.debug("item: %s, flavors: %s", item, flavors)
        for flavor in flavors:
            LOG.debug("item.flavor: %s, flavor: %s", item.flavor, flavor)
            if item.flavor.get('id') == flavor.id:
                LOG.debug("flavor.ram: %s", flavor.ram)
                return flavor.ram

    def get_vcpu_num(self, item, flavors):
        """Get vcpu number of item

        :param item: instance
        :param flavors: flavors
        :returns: vcpu number of item
        """

        LOG.debug("item: %s, flavors: %s", item, flavors)
        for flavor in flavors:
            LOG.debug("item.flavor: %s, flavor: %s", item.flavor, flavor)
            if item.flavor.get('id') == flavor.id:
                LOG.debug("flavor.vcpus: %s", flavor.vcpus)
                return flavor.vcpus

    def get_disk_size(self, item, flavors):
        """Get disk size of item

        :param item: instance
        :param flavors: flavors
        :returns: disk size of item
        """

        LOG.debug("item: %s, flavors: %s", item, flavors)
        for flavor in flavors:
            LOG.debug("item.flavor: %s, flavor: %s", item.flavor, flavor)
            if item.flavor.get('id') == flavor.id:
                LOG.debug("flavor.disk: %s", flavor.disk)
                return flavor.disk


class StorageSpecSortFilter(BaseFilter):
    """StorageSpecSortFilter"""

    apply_targets = ('volume',)
    accept_keys = ['size', 'created_at']

    def exec_filter(self, items, sort_key):
        result = items

        if sort_key not in self.accept_keys:
            LOG.warning("Invalid key is specified: %s", sort_key)
            return result

        if sort_key == 'created_at':
            result = sorted(items,
                            key=lambda x: parse(getattr(x, sort_key)),
                            reverse=False)
        else:
            result = sorted(items,
                            key=lambda x: float(getattr(x, sort_key)),
                            reverse=True)
        LOG.debug(result)
        return result
