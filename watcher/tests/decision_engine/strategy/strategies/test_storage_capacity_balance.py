# -*- encoding: utf-8 -*-
# Copyright (c) 2017 ZTE
#
# Authors: Canwei Li <li.canwei2@zte.com.cn>
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

import mock


from watcher.common import cinder_helper
from watcher.common import clients
from watcher.common import utils
from watcher.decision_engine.strategy import strategies
from watcher.tests.decision_engine.model import faker_cluster_state
from watcher.tests.decision_engine.strategy.strategies.test_base \
    import TestBaseStrategy


class TestStorageCapacityBalance(TestBaseStrategy):

    def setUp(self):
        super(TestStorageCapacityBalance, self).setUp()

        def test_fake_pool(name, free, total, allocated):
            fake_pool = mock.MagicMock()
            fake_pool.name = name
            fake_pool.pool_name = name.split('#')[1]
            fake_pool.volume_backend_name = name.split('#')[1]
            fake_pool.free_capacity_gb = free
            fake_pool.total_capacity_gb = total
            fake_pool.allocated_capacity_gb = allocated
            fake_pool.max_over_subscription_ratio = 1.0

            return fake_pool

        self.fake_pool1 = test_fake_pool('host1@IPSAN-1#pool1',
                                         '60', '100', '90')

        self.fake_pool2 = test_fake_pool('host1@IPSAN-1#pool2',
                                         '20', '100', '80')

        self.fake_pool3 = test_fake_pool('host1@IPSAN-1#local_vstorage',
                                         '20', '100', '80')
        self.fake_pools = [self.fake_pool1, self.fake_pool2,
                           self.fake_pool3]

        def test_fake_vol(id, name, size, status, bootable,
                          migration_status=None,
                          volume_type=None):
            fake_vol = mock.MagicMock()
            fake_vol.id = id
            fake_vol.name = name
            fake_vol.size = size
            fake_vol.status = status
            fake_vol.bootable = bootable
            fake_vol.migration_status = migration_status
            fake_vol.volume_type = volume_type
            setattr(fake_vol, 'os-vol-host-attr:host', 'host1@IPSAN-1#pool2')

            return fake_vol

        self.fake_vol1 = test_fake_vol('922d4762-0bc5-4b30-9cb9-48ab644dd861',
                                       'test_volume1', 4,
                                       'available', 'true', 'success',
                                       volume_type='type2')
        self.fake_vol2 = test_fake_vol('922d4762-0bc5-4b30-9cb9-48ab644dd862',
                                       'test_volume2', 10,
                                       'in-use', 'false')
        self.fake_vol3 = test_fake_vol('922d4762-0bc5-4b30-9cb9-48ab644dd863',
                                       'test_volume3', 4,
                                       'in-use', 'true', volume_type='type2')
        self.fake_vol4 = test_fake_vol('922d4762-0bc5-4b30-9cb9-48ab644dd864',
                                       'test_volume4', 10,
                                       'error', 'true')
        self.fake_vol5 = test_fake_vol('922d4762-0bc5-4b30-9cb9-48ab644dd865',
                                       'test_volume5', 15,
                                       'in-use', 'true')

        self.fake_volumes = [self.fake_vol1,
                             self.fake_vol2,
                             self.fake_vol3,
                             self.fake_vol4,
                             self.fake_vol5]

        def test_fake_snap(vol_id):
            fake_snap = mock.MagicMock()
            fake_snap.volume_id = vol_id

            return fake_snap

        self.fake_snap = [test_fake_snap(
            '922d4762-0bc5-4b30-9cb9-48ab644dd865')]

        def test_fake_volume_type(type_name, extra_specs):
            fake_type = mock.MagicMock()
            fake_type.name = type_name
            fake_type.extra_specs = extra_specs

            return fake_type

        self.fake_types = [test_fake_volume_type(
            'type1', {'volume_backend_name': 'pool1'}),
            test_fake_volume_type(
            'type2', {'volume_backend_name': 'pool2'})
            ]

        self.fake_c_cluster = faker_cluster_state.FakerStorageModelCollector()

        osc = clients.OpenStackClients()

        p_cinder = mock.patch.object(osc, 'cinder')
        p_cinder.start()
        self.addCleanup(p_cinder.stop)
        self.m_cinder = cinder_helper.CinderHelper(osc=osc)

        self.m_cinder.get_storage_pool_list = mock.Mock(
            return_value=self.fake_pools)
        self.m_cinder.get_volume_list = mock.Mock(
            return_value=self.fake_volumes)
        self.m_cinder.get_volume_snapshots_list = mock.Mock(
            return_value=self.fake_snap)
        self.m_cinder.get_volume_type_list = mock.Mock(
            return_value=self.fake_types)

        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model

        self.strategy = strategies.StorageCapacityBalance(
            config=mock.Mock(), osc=osc)
        self.strategy._cinder = self.m_cinder
        self.strategy.input_parameters = utils.Struct()
        self.strategy.input_parameters.update(
            {'volume_threshold': 80.0})
        self.strategy.volume_threshold = 80.0

    def test_get_pools(self):
        self.strategy.config.ex_pools = "local_vstorage"
        pools = self.strategy.get_pools(self.m_cinder)
        self.assertEqual(len(pools), 2)

    def test_get_volumes(self):
        volumes = self.strategy.get_volumes(self.m_cinder)
        self.assertEqual(len(volumes), 3)

    def test_group_pools(self):
        self.strategy.config.ex_pools = "local_vstorage"
        pools = self.strategy.get_pools(self.m_cinder)
        over_pools, under_pools = self.strategy.group_pools(pools, 0.50)
        self.assertEqual(len(under_pools), 1)
        self.assertEqual(len(over_pools), 1)

        over_pools, under_pools = self.strategy.group_pools(pools, 0.85)
        self.assertEqual(len(under_pools), 2)
        self.assertEqual(len(over_pools), 0)

        over_pools, under_pools = self.strategy.group_pools(pools, 0.30)
        self.assertEqual(len(under_pools), 0)
        self.assertEqual(len(over_pools), 2)

    def test_get_volume_type_by_name(self):
        vol_type = self.strategy.get_volume_type_by_name(
            self.m_cinder, 'pool1')
        self.assertEqual(len(vol_type), 1)

        vol_type = self.strategy.get_volume_type_by_name(
            self.m_cinder, 'ks3200')
        self.assertEqual(len(vol_type), 0)

    def test_check_pool_type(self):
        pool_type = self.strategy.check_pool_type(
            self.fake_vol3, self.fake_pool1)
        self.assertIsNotNone(pool_type)

        pool_type = self.strategy.check_pool_type(
            self.fake_vol3, self.fake_pool2)
        self.assertIsNone(pool_type)

    def test_migrate_fit(self):
        self.strategy.config.ex_pools = "local_vstorage"
        pools = self.strategy.get_pools(self.m_cinder)
        self.strategy.source_pools, self.strategy.dest_pools = (
            self.strategy.group_pools(pools, 0.60))
        target_pool = self.strategy.migrate_fit(self.fake_vol2, 0.60)
        self.assertIsNotNone(target_pool)

        target_pool = self.strategy.migrate_fit(self.fake_vol3, 0.50)
        self.assertIsNone(target_pool)

        target_pool = self.strategy.migrate_fit(self.fake_vol5, 0.60)
        self.assertIsNone(target_pool)

    def test_retype_fit(self):
        self.strategy.config.ex_pools = "local_vstorage"
        pools = self.strategy.get_pools(self.m_cinder)
        self.strategy.source_pools, self.strategy.dest_pools = (
            self.strategy.group_pools(pools, 0.50))
        target_pool = self.strategy.retype_fit(self.fake_vol1, 0.50)
        self.assertIsNotNone(target_pool)

        target_pool = self.strategy.retype_fit(self.fake_vol2, 0.50)
        self.assertIsNone(target_pool)

        target_pool = self.strategy.retype_fit(self.fake_vol3, 0.50)
        self.assertIsNotNone(target_pool)

        target_pool = self.strategy.retype_fit(self.fake_vol5, 0.60)
        self.assertIsNone(target_pool)

    def test_execute(self):
        self.strategy.input_parameters.update(
            {'volume_threshold': 45.0})
        self.strategy.config.ex_pools = "local_vstorage"
        solution = self.strategy.execute()
        self.assertEqual(len(solution.actions), 1)

        setattr(self.fake_pool1, 'free_capacity_gb', '60')
        self.strategy.input_parameters.update(
            {'volume_threshold': 50.0})
        solution = self.strategy.execute()
        self.assertEqual(len(solution.actions), 2)

        setattr(self.fake_pool1, 'free_capacity_gb', '60')
        self.strategy.input_parameters.update(
            {'volume_threshold': 60.0})

        solution = self.strategy.execute()
        self.assertEqual(len(solution.actions), 3)
