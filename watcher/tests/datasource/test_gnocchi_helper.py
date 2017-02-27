# -*- encoding: utf-8 -*-
# Copyright (c) 2017 Servionica
#
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
from oslo_config import cfg
from oslo_utils import timeutils

from watcher.common import clients
from watcher.common import exception
from watcher.datasource import gnocchi as gnocchi_helper
from watcher.tests import base

CONF = cfg.CONF


@mock.patch.object(clients.OpenStackClients, 'gnocchi')
class TestGnocchiHelper(base.BaseTestCase):

    def test_gnocchi_statistic_aggregation(self, mock_gnocchi):
        gnocchi = mock.MagicMock()
        expected_result = 5.5

        expected_measures = [["2017-02-02T09:00:00.000000", 360, 5.5]]

        gnocchi.metric.get_measures.return_value = expected_measures
        mock_gnocchi.return_value = gnocchi

        helper = gnocchi_helper.GnocchiHelper()
        result = helper.statistic_aggregation(
            resource_id='16a86790-327a-45f9-bc82-45839f062fdc',
            metric='cpu_util',
            granularity=360,
            start_time=timeutils.parse_isotime("2017-02-02T09:00:00.000000"),
            stop_time=timeutils.parse_isotime("2017-02-02T10:00:00.000000"),
            aggregation='mean'
        )
        self.assertEqual(expected_result, result)

    def test_gnocchi_wrong_datetime(self, mock_gnocchi):
        gnocchi = mock.MagicMock()

        expected_measures = [["2017-02-02T09:00:00.000000", 360, 5.5]]

        gnocchi.metric.get_measures.return_value = expected_measures
        mock_gnocchi.return_value = gnocchi

        helper = gnocchi_helper.GnocchiHelper()
        self.assertRaises(
            exception.InvalidParameter, helper.statistic_aggregation,
            resource_id='16a86790-327a-45f9-bc82-45839f062fdc',
            metric='cpu_util',
            granularity=360,
            start_time="2017-02-02T09:00:00.000000",
            stop_time=timeutils.parse_isotime("2017-02-02T10:00:00.000000"),
            aggregation='mean')
