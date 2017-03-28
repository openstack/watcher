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

from watcher.common import clients
from watcher.common import exception

LOG = log.getLogger(__name__)


class CinderHelper(object):

    def __init__(self, osc=None):
        """:param osc: an OpenStackClients instance"""
        self.osc = osc if osc else clients.OpenStackClients()
        self.cinder = self.osc.cinder()

    def get_storage_node_list(self):
        return list(self.cinder.services.list(binary='cinder-volume'))

    def get_storage_node_by_name(self, name):
        """Get storage node by name(host@backendname)"""
        try:
            storages = list(filter(lambda storage:
                            storage.host == name,
                            self.get_storage_node_list()))
            if len(storages) != 1:
                raise exception.StorageNodeNotFound(name=name)
            return storages[0]
        except Exception as exc:
            LOG.exception(exc)
            raise exception.StorageNodeNotFound(name=name)

    def get_storage_pool_list(self):
        return self.cinder.pools.list(detailed=True)

    def get_storage_pool_by_name(self, name):
        """Get pool by name(host@backend#poolname)"""
        try:
            pools = list(filter(lambda pool:
                         pool.name == name,
                         self.get_storage_pool_list()))
            if len(pools) != 1:
                raise exception.PoolNotFound(name=name)
            return pools[0]
        except Exception as exc:
            LOG.exception(exc)
            raise exception.PoolNotFound(name=name)

    def get_volume_list(self):
        return self.cinder.volumes.list(search_opts={'all_tenants': True})

    def get_volume_type_list(self):
        return self.cinder.volume_types.list()

    def get_volume_type_by_backendname(self, backendname):
        volume_type_list = self.get_volume_type_list()

        volume_type = list(filter(
            lambda volume_type:
                volume_type.extra_specs.get(
                    'volume_backend_name') == backendname, volume_type_list))
        if volume_type:
            return volume_type[0].name
        else:
            return ""
