# -*- encoding: utf-8 -*-
# Copyright 2019 ZTE Corporation.
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
import unittest

from watcher.common import exception
from watcher.common import utils
from watcher.decision_engine.messaging import data_model_endpoint
from watcher.decision_engine.model.collector import manager
from watcher.objects import audit


class TestDataModelEndpoint(unittest.TestCase):
    def setUp(self):
        self.endpoint_instance = data_model_endpoint.DataModelEndpoint('fake')

    @mock.patch.object(audit.Audit, 'get')
    def test_get_audit_scope(self, mock_get):
        mock_get.return_value = mock.Mock(scope='fake_scope')
        audit_uuid = utils.generate_uuid()

        result = self.endpoint_instance.get_audit_scope(
            context=None,
            audit=audit_uuid)
        self.assertEqual('fake_scope', result)

    @mock.patch.object(audit.Audit, 'get_by_name')
    def test_get_audit_scope_with_error_name(self, mock_get_by_name):
        mock_get_by_name.side_effect = exception.AuditNotFound()
        audit_name = 'error_audit_name'

        self.assertRaises(
            exception.InvalidIdentity,
            self.endpoint_instance.get_audit_scope,
            context=None,
            audit=audit_name)

    @mock.patch.object(manager, 'CollectorManager', mock.Mock())
    def test_get_data_model_info(self):
        result = self.endpoint_instance.get_data_model_info(context='fake')
        self.assertIn('context', result)
