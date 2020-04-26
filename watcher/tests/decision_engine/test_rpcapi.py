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

from unittest import mock

import oslo_messaging as om
from watcher.common import exception
from watcher.common import utils
from watcher.decision_engine import rpcapi
from watcher.tests import base


class TestDecisionEngineAPI(base.TestCase):

    api = rpcapi.DecisionEngineAPI()

    def test_get_api_version(self):
        with mock.patch.object(om.RPCClient, 'call') as mock_call:
            expected_context = self.context
            self.api.check_api_version(expected_context)
            mock_call.assert_called_once_with(
                expected_context, 'check_api_version',
                api_version=rpcapi.DecisionEngineAPI().api_version)

    def test_execute_audit_throw_exception(self):
        audit_uuid = "uuid"
        self.assertRaises(exception.InvalidUuidOrName,
                          self.api.trigger_audit,
                          audit_uuid)

    def test_execute_audit_without_error(self):
        with mock.patch.object(om.RPCClient, 'cast') as mock_cast:
            audit_uuid = utils.generate_uuid()
            self.api.trigger_audit(self.context, audit_uuid)
            mock_cast.assert_called_once_with(
                self.context, 'trigger_audit', audit_uuid=audit_uuid)

    def test_get_strategy_info(self):
        with mock.patch.object(om.RPCClient, 'call') as mock_call:
            self.api.get_strategy_info(self.context, "dummy")
            mock_call.assert_called_once_with(
                self.context, 'get_strategy_info', strategy_name="dummy")

    def test_get_data_model_info(self):
        with mock.patch.object(om.RPCClient, 'call') as mock_call:
            self.api.get_data_model_info(
                self.context,
                data_model_type='compute',
                audit=None)
            mock_call.assert_called_once_with(
                self.context, 'get_data_model_info',
                data_model_type='compute',
                audit=None)
