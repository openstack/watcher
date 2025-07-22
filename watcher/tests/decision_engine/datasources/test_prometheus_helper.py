# Copyright 2024 Red Hat, Inc.
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

from observabilityclient import prometheus_client
from oslo_config import cfg

from watcher.common import exception
from watcher.decision_engine.datasources import prometheus as prometheus_helper
from watcher.tests import base


class TestPrometheusHelper(base.BaseTestCase):
    def setUp(self):
        super(TestPrometheusHelper, self).setUp()
        cfg.CONF.prometheus_client.host = "foobarbaz"
        cfg.CONF.prometheus_client.port = "1234"

        with mock.patch.object(
            prometheus_helper.PrometheusHelper,
            '_setup_prometheus_client'
        ):
            self.helper = prometheus_helper.PrometheusHelper()

        # Set up patches for all methods used inside the
        # _setup_prometheus_client
        self.mock_init = mock.patch.object(
            prometheus_client.PrometheusAPIClient, '__init__',
            return_value=None).start()
        self.addCleanup(self.mock_init.stop)

        self.mock_set_ca_cert = mock.patch.object(
            prometheus_client.PrometheusAPIClient, 'set_ca_cert').start()
        self.addCleanup(self.mock_set_ca_cert.stop)

        self.mock_set_client_cert = mock.patch.object(
            prometheus_client.PrometheusAPIClient, 'set_client_cert').start()
        self.addCleanup(self.mock_set_client_cert.stop)

        self.mock_set_basic_auth = mock.patch.object(
            prometheus_client.PrometheusAPIClient, 'set_basic_auth').start()
        self.addCleanup(self.mock_set_basic_auth.stop)

        self.mock_build_fqdn_labels = mock.patch.object(
            prometheus_helper.PrometheusHelper,
            '_build_prometheus_fqdn_labels').start()
        self.addCleanup(self.mock_build_fqdn_labels.stop)

    def test_unset_missing_prometheus_host(self):
        cfg.CONF.prometheus_client.port = '123'
        cfg.CONF.prometheus_client.host = None
        self.assertRaisesRegex(
            exception.MissingParameter, 'prometheus host and port must be '
                                        'set in watcher.conf',
            prometheus_helper.PrometheusHelper
        )
        cfg.CONF.prometheus_client.host = ''
        self.assertRaisesRegex(
            exception.MissingParameter, 'prometheus host and port must be '
                                        'set in watcher.conf',
            prometheus_helper.PrometheusHelper
        )

    def test_unset_missing_prometheus_port(self):
        cfg.CONF.prometheus_client.host = 'some.host.domain'
        cfg.CONF.prometheus_client.port = None
        self.assertRaisesRegex(
            exception.MissingParameter, 'prometheus host and port must be '
                                        'set in watcher.conf',
            prometheus_helper.PrometheusHelper
        )
        cfg.CONF.prometheus_client.port = ''
        self.assertRaisesRegex(
            exception.MissingParameter, 'prometheus host and port must be '
                                        'set in watcher.conf',
            prometheus_helper.PrometheusHelper
        )

    def test_invalid_prometheus_port(self):
        cfg.CONF.prometheus_client.host = "hostOK"
        cfg.CONF.prometheus_client.port = "123badPort"
        self.assertRaisesRegex(
            exception.InvalidParameter, "missing or invalid port number "
                                        "'123badPort'",
            prometheus_helper.PrometheusHelper
        )
        cfg.CONF.prometheus_client.port = "123456"
        self.assertRaisesRegex(
            exception.InvalidParameter, "missing or invalid port number "
                                        "'123456'",
            prometheus_helper.PrometheusHelper
        )

    def test_invalid_prometheus_host(self):
        cfg.CONF.prometheus_client.port = "123"
        cfg.CONF.prometheus_client.host = "-badhost"
        self.assertRaisesRegex(
            exception.InvalidParameter, "hostname '-badhost' "
                                        "failed regex match",
            prometheus_helper.PrometheusHelper
        )
        too_long_hostname = ("a" * 256)
        cfg.CONF.prometheus_client.host = too_long_hostname
        self.assertRaisesRegex(
            exception.InvalidParameter, ("hostname is too long: " +
                                         "'" + too_long_hostname + "'"),
            prometheus_helper.PrometheusHelper
        )

    def test_get_fqdn_label(self):
        fqdn = 'fqdn_label'
        cfg.CONF.prometheus_client.fqdn_label = fqdn
        self.assertEqual(
            fqdn,
            self.helper._get_fqdn_label()
        )

    def test_get_instance_uuid_label(self):
        instance_uuid = 'instance_uuid_label'
        cfg.CONF.prometheus_client.instance_uuid_label = instance_uuid
        self.assertEqual(
            instance_uuid,
            self.helper._get_instance_uuid_label()
        )

    def test_setup_prometheus_client_no_auth_no_tls(self):
        cfg.CONF.prometheus_client.host = "somehost"
        cfg.CONF.prometheus_client.port = "1234"
        prometheus_helper.PrometheusHelper()

        self.mock_init.assert_called_once_with("somehost:1234")
        self.mock_set_basic_auth.assert_not_called()
        self.mock_set_client_cert.assert_not_called()
        self.mock_set_ca_cert.assert_not_called()

    def test_setup_prometheus_client_tls(self):
        cfg.CONF.prometheus_client.cafile = "/some/path"
        prometheus_helper.PrometheusHelper()

        self.mock_set_ca_cert.assert_called_once_with("/some/path")

    def test_setup_prometheus_client_basic_auth(self):
        cfg.CONF.prometheus_client.username = "user"
        cfg.CONF.prometheus_client.password = "password"
        prometheus_helper.PrometheusHelper()

        self.mock_set_basic_auth.assert_called_once_with("user", "password")

    def test_setup_prometheus_client_mtls(self):
        cfg.CONF.prometheus_client.certfile = "/cert/path"
        cfg.CONF.prometheus_client.keyfile = "/key/path"
        cfg.CONF.prometheus_client.cafile = "/ca/path"
        prometheus_helper.PrometheusHelper()

        self.mock_set_client_cert.assert_called_once_with(
            "/cert/path", "/key/path")
