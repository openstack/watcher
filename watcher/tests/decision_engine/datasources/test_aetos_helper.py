# Copyright 2025 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
from unittest import mock

from observabilityclient.utils import metric_utils as obs_client_utils
from oslo_config import cfg

from watcher.decision_engine.datasources import aetos as aetos_helper
from watcher.tests import base


class TestAetosHelper(base.BaseTestCase):
    def setUp(self):
        super(TestAetosHelper, self).setUp()
        with mock.patch.object(
            aetos_helper.AetosHelper, '_setup_prometheus_client'
        ):
            self.helper = aetos_helper.AetosHelper(mock.Mock())

    def test_get_fqdn_label(self):
        fqdn = 'fqdn_label'
        cfg.CONF.aetos_client.fqdn_label = fqdn
        self.assertEqual(
            fqdn,
            self.helper._get_fqdn_label()
        )

    def test_get_instance_uuid_label(self):
        instance_uuid = 'instance_uuid_label'
        cfg.CONF.aetos_client.instance_uuid_label = instance_uuid
        self.assertEqual(
            instance_uuid,
            self.helper._get_instance_uuid_label()
        )

    @mock.patch.object(obs_client_utils, 'get_prom_client_from_keystone')
    def test_setup_prometheus_client(self, mock_get_prom_client):
        cfg.CONF.aetos_client.interface = 'internal'
        cfg.CONF.aetos_client.region_name = 'RegionTwo'

        opts = {'interface': 'internal',
                'region_name': 'RegionTwo',
                'service_type': 'metric-storage'}
        osc = mock.Mock()
        osc.session = mock.Mock()
        aetos_helper.AetosHelper(osc)

        mock_get_prom_client.assert_called_once_with(
            osc.session, adapter_options=opts)
