# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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

from __future__ import absolute_import
from __future__ import unicode_literals

from mock import MagicMock
from mock import mock

from watcher.common.ceilometer import CeilometerClient

from watcher.tests.base import BaseTestCase


class TestCeilometer(BaseTestCase):
    def setUp(self):
        super(TestCeilometer, self).setUp()
        self.cm = CeilometerClient()

    def test_build_query(self):
        expected = [{'field': 'user_id', 'op': 'eq', 'value': u'user_id'},
                    {'field': 'project_id', 'op': 'eq', 'value': u'tenant_id'},
                    {'field': 'resource_id', 'op': 'eq',
                     'value': u'resource_id'}]

        query = self.cm.build_query(user_id="user_id",
                                    tenant_id="tenant_id",
                                    resource_id="resource_id",
                                    user_ids=["user_ids"],
                                    tenant_ids=["tenant_ids"],
                                    resource_ids=["resource_ids"])
        self.assertEqual(query, expected)

    @mock.patch("watcher.common.keystone.Keystoneclient")
    def test_get_ceilometer_v2(self, mock_keystone):
        c = CeilometerClient(api_version='2')
        from ceilometerclient.v2 import Client
        self.assertIsInstance(c.cmclient, Client)

    @mock.patch.object(CeilometerClient, "cmclient")
    def test_statistic_aggregation(self, mock_keystone):
        statistic = MagicMock()
        expected_result = 100
        statistic[-1]._info = {'aggregate': {'avg': expected_result}}
        mock_keystone.statistics.list.return_value = statistic
        val = self.cm.statistic_aggregation(
            resource_id="VM_ID",
            meter_name="cpu_util",
            period="7300"
        )
        self.assertEqual(val, expected_result)

    @mock.patch.object(CeilometerClient, "cmclient")
    def test_get_last_sample(self, mock_keystone):
        statistic = MagicMock()
        expected_result = 100
        statistic[-1]._info = {'counter_volume': expected_result}
        mock_keystone.samples.list.return_value = statistic
        val = self.cm.get_last_sample_value(
            resource_id="id",
            meter_name="compute.node.percent"
        )
        self.assertEqual(val, expected_result)

    @mock.patch.object(CeilometerClient, "cmclient")
    def test_get_last_sample_none(self, mock_keystone):
        expected = False
        mock_keystone.samples.list.return_value = None
        val = self.cm.get_last_sample_values(
            resource_id="id",
            meter_name="compute.node.percent"
        )
        self.assertEqual(val, expected)

    @mock.patch.object(CeilometerClient, "cmclient")
    def test_statistic_list(self, mock_keystone):
        expected_value = []
        mock_keystone.statistics.list.return_value = expected_value
        val = self.cm.statistic_list(meter_name="cpu_util")
        self.assertEqual(val, expected_value)
