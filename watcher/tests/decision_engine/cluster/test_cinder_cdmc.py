# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock

from watcher.common import cinder_helper
from watcher.common import exception
from watcher.decision_engine.model.collector import cinder
from watcher.tests import base
from watcher.tests import conf_fixture


class TestCinderClusterDataModelCollector(base.TestCase):

    def setUp(self):
        super(TestCinderClusterDataModelCollector, self).setUp()
        self.useFixture(conf_fixture.ConfReloadFixture())

    @mock.patch('keystoneclient.v3.client.Client', mock.Mock())
    @mock.patch.object(cinder_helper, 'CinderHelper')
    def test_cinder_cdmc_execute(self, m_cinder_helper_cls):

        m_cinder_helper = mock.Mock(name="cinder_helper")
        m_cinder_helper_cls.return_value = m_cinder_helper

        fake_storage_node = mock.Mock(
            host='host@backend',
            zone='zone',
            status='enabled',
            state='up',
            volume_type=['fake_type']
        )

        fake_storage_pool = mock.Mock(
            total_volumes=1,
            total_capacity_gb=30,
            free_capacity_gb=20,
            provisioned_capacity_gb=10,
            allocated_capacity_gb=10,
            virtual_free=20
        )
        setattr(fake_storage_pool, 'name', 'host@backend#pool')

        fake_volume = mock.Mock(
            id=1,
            size=1,
            status='in-use',
            attachments=[{"server_id": "server_id",
                          "attachment_id": "attachment_id"}],
            multiattach='false',
            snapshot_id='',
            metadata='{"key": "value"}',
            bootable='false'
        )
        setattr(fake_volume, 'name', 'name')
        setattr(fake_volume, 'os-vol-tenant-attr:tenant_id',
                '0c003652-0cb1-4210-9005-fd5b92b1faa2')
        setattr(fake_volume, 'os-vol-host-attr:host', 'host@backend#pool')

        # storage node list
        m_cinder_helper.get_storage_node_list.return_value = [
            fake_storage_node]
        m_cinder_helper.get_volume_type_by_backendname.return_value = [
            'fake_type']

        # storage pool list
        m_cinder_helper.get_storage_pool_list.return_value = [
            fake_storage_pool]
        # volume list
        m_cinder_helper.get_volume_list.return_value = [fake_volume]

        m_config = mock.Mock()
        m_osc = mock.Mock()

        cinder_cdmc = cinder.CinderClusterDataModelCollector(
            config=m_config, osc=m_osc)

        cinder_cdmc.get_audit_scope_handler([])
        model = cinder_cdmc.execute()

        storage_nodes = model.get_all_storage_nodes()
        storage_node = list(storage_nodes.values())[0]

        storage_pools = model.get_node_pools(storage_node)
        storage_pool = storage_pools[0]

        volumes = model.get_pool_volumes(storage_pool)
        volume = volumes[0]

        self.assertEqual(1, len(storage_nodes))
        self.assertEqual(1, len(storage_pools))
        self.assertEqual(1, len(volumes))

        self.assertEqual(storage_node.host, 'host@backend')
        self.assertEqual(storage_pool.name, 'host@backend#pool')
        self.assertEqual(volume.uuid, '1')

    @mock.patch('keystoneclient.v3.client.Client', mock.Mock())
    @mock.patch.object(cinder_helper, 'CinderHelper')
    def test_cinder_cdmc_total_capacity_gb_not_integer(
            self, m_cinder_helper_cls):

        m_cinder_helper = mock.Mock(name="cinder_helper")
        m_cinder_helper_cls.return_value = m_cinder_helper

        fake_storage_node = mock.Mock(
            host='host@backend',
            zone='zone',
            status='enabled',
            state='up',
            volume_type=['fake_type']
        )

        fake_storage_pool = mock.Mock(
            total_volumes=1,
            total_capacity_gb="unknown",
            free_capacity_gb=20,
            provisioned_capacity_gb=10,
            allocated_capacity_gb=10,
            virtual_free=20
        )
        setattr(fake_storage_pool, 'name', 'host@backend#pool')

        # storage node list
        m_cinder_helper.get_storage_node_list.return_value = [
            fake_storage_node]
        m_cinder_helper.get_volume_type_by_backendname.return_value = [
            'fake_type']

        # storage pool list
        m_cinder_helper.get_storage_pool_list.return_value = [
            fake_storage_pool]

        # volume list
        m_cinder_helper.get_volume_list.return_value = []

        m_config = mock.Mock()
        m_osc = mock.Mock()

        cinder_cdmc = cinder.CinderClusterDataModelCollector(
            config=m_config, osc=m_osc)

        cinder_cdmc.get_audit_scope_handler([])
        self.assertRaises(exception.InvalidPoolAttributeValue,
                          cinder_cdmc.execute)
