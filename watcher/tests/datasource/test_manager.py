# -*- encoding: utf-8 -*-
# Copyright (c) 2017 Servionica
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

import mock

from watcher.common import exception
from watcher.datasource import gnocchi as gnoc
from watcher.datasource import manager as ds_manager
from watcher.tests import base


class TestDataSourceManager(base.BaseTestCase):

    @mock.patch.object(gnoc, 'GnocchiHelper')
    def test_get_backend(self, mock_gnoc):
        manager = ds_manager.DataSourceManager(
            config=mock.MagicMock(
                datasources=['gnocchi', 'ceilometer', 'monasca']),
            osc=mock.MagicMock())
        backend = manager.get_backend(['host_cpu_usage',
                                       'instance_cpu_usage'])
        self.assertEqual(backend, manager.gnocchi)

    def test_get_backend_wrong_metric(self):
        manager = ds_manager.DataSourceManager(
            config=mock.MagicMock(
                datasources=['gnocchi', 'ceilometer', 'monasca']),
            osc=mock.MagicMock())
        self.assertRaises(exception.NoSuchMetric, manager.get_backend,
                          ['host_cpu', 'instance_cpu_usage'])
