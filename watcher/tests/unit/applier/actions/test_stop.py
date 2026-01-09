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

from unittest import mock

import fixtures
import jsonschema

from watcher.applier.actions import base as baction
from watcher.applier.actions import stop
from watcher.common import exception
from watcher.tests.unit import base
from watcher.tests.unit.common import utils as test_utils


class TestStop(test_utils.NovaResourcesMixin, base.TestCase):

    INSTANCE_UUID = "45a37aeb-95ab-4ddb-a305-7d9f62c2f5ba"

    def setUp(self):
        super().setUp()

        self.m_helper = self.useFixture(
            fixtures.MockPatch(
                "watcher.common.nova_helper.NovaHelper",
                autospec=False)).mock.return_value

        self.input_parameters = {
            baction.BaseAction.RESOURCE_ID: self.INSTANCE_UUID,
        }
        self.instance = self.create_nova_server(
            id=self.INSTANCE_UUID,
            status='ACTIVE'
        )
        self.action = stop.Stop(mock.Mock())
        self.action.input_parameters = self.input_parameters

    def test_parameters(self):
        parameters = {baction.BaseAction.RESOURCE_ID: self.INSTANCE_UUID}
        self.action.input_parameters = parameters
        self.assertTrue(self.action.validate_parameters())

    def test_parameters_exception_empty_resource_id(self):
        parameters = {baction.BaseAction.RESOURCE_ID: None}
        self.action.input_parameters = parameters
        self.assertRaises(jsonschema.ValidationError,
                          self.action.validate_parameters)

    def test_parameters_exception_invalid_uuid_format(self):
        parameters = {baction.BaseAction.RESOURCE_ID: "invalid-uuid"}
        self.action.input_parameters = parameters
        self.assertRaises(jsonschema.ValidationError,
                          self.action.validate_parameters)

    def test_parameters_exception_missing_resource_id(self):
        parameters = {}
        self.action.input_parameters = parameters
        self.assertRaises(jsonschema.ValidationError,
                          self.action.validate_parameters)

    def test_instance_uuid_property(self):
        self.assertEqual(self.INSTANCE_UUID, self.action.instance_uuid)

    def test_pre_condition_instance_not_found(self):
        err = exception.ComputeResourceNotFound()
        self.m_helper.find_instance.side_effect = err

        # ActionSkipped is expected because the instance is not found
        self.assertRaisesRegex(
            exception.ActionSkipped,
            f"Instance {self.INSTANCE_UUID} not found",
            self.action.pre_condition)

        self.m_helper.find_instance.assert_called_once_with(self.INSTANCE_UUID)

    def test_pre_condition_instance_already_stopped(self):
        self.instance.status = 'SHUTOFF'
        self.m_helper.find_instance.return_value = self.instance

        # ActionSkipped is expected because the instance is already stopped
        self.assertRaisesRegex(
            exception.ActionSkipped,
            f"Instance {self.INSTANCE_UUID} is already stopped",
            self.action.pre_condition)
        self.m_helper.find_instance.assert_called_once_with(self.INSTANCE_UUID)

    def test_pre_condition_instance_active(self):
        self.m_helper.find_instance.return_value = self.instance

        result = self.action.pre_condition()

        # pre_condition returns None for active instances (implicit success)
        self.assertIsNone(result)
        self.m_helper.find_instance.assert_called_once_with(self.INSTANCE_UUID)

    def test_pre_condition_nova_exception(self):
        self.m_helper.find_instance.side_effect = Exception("Nova error")

        self.assertRaises(Exception, self.action.pre_condition)
        self.m_helper.find_instance.assert_called_once_with(self.INSTANCE_UUID)

    def test_execute_success(self):
        self.m_helper.stop_instance.return_value = True

        result = self.action.execute()

        self.assertTrue(result)
        self.m_helper.stop_instance.assert_called_once_with(
            instance_id=self.INSTANCE_UUID)

    def test_execute_stop_failure_instance_exists(self):
        # Instance exists but stop operation fails
        self.m_helper.find_instance.return_value = self.instance
        self.m_helper.stop_instance.return_value = False

        result = self.action.execute()

        # Should return False when stop fails and instance still exists
        self.assertFalse(result)
        self.m_helper.stop_instance.assert_called_once_with(
            instance_id=self.INSTANCE_UUID)
        # Should check instance existence after stop failure
        self.m_helper.find_instance.assert_called_once_with(self.INSTANCE_UUID)

    def test_execute_stop_failure_instance_not_found(self):
        # Stop operation fails but instance doesn't exist (idempotent)
        self.m_helper.find_instance.return_value = None
        self.m_helper.stop_instance.return_value = False

        result = self.action.execute()

        # Return True when stop fails but instance doesn't exist (idempotent)
        self.assertTrue(result)
        self.m_helper.stop_instance.assert_called_once_with(
            instance_id=self.INSTANCE_UUID)
        # Should check instance existence after stop failure
        self.m_helper.find_instance.assert_called_once_with(self.INSTANCE_UUID)

    def test_execute_nova_exception(self):
        self.m_helper.stop_instance.side_effect = Exception("Stop failed")

        result = self.action.execute()

        # Execute should return False when Nova API fails, not raise exception
        self.assertFalse(result)
        self.m_helper.stop_instance.assert_called_once_with(
            instance_id=self.INSTANCE_UUID)

    def test_revert_success(self):
        self.m_helper.start_instance.return_value = True

        result = self.action.revert()

        self.assertTrue(result)
        # revert method doesn't call find_instance - it directly tries to start
        self.m_helper.start_instance.assert_called_once_with(
            instance_id=self.INSTANCE_UUID)

    def test_revert_instance_not_found(self):
        # The revert method doesn't check for instance existence,
        # it just tries to start and may fail gracefully
        self.m_helper.start_instance.side_effect = exception.InstanceNotFound(
            name=self.INSTANCE_UUID)

        result = self.action.revert()

        # Should return False when start fails due to instance not found
        self.assertFalse(result)
        self.m_helper.start_instance.assert_called_once_with(
            instance_id=self.INSTANCE_UUID)

    def test_revert_start_failure(self):
        self.m_helper.start_instance.return_value = False

        result = self.action.revert()

        self.assertFalse(result)
        self.m_helper.start_instance.assert_called_once_with(
            instance_id=self.INSTANCE_UUID)

    def test_revert_nova_exception(self):
        self.m_helper.start_instance.side_effect = Exception("Start failed")

        result = self.action.revert()

        # Should return False when start fails with exception
        self.assertFalse(result)

    def test_get_description(self):
        expected = "Stop a VM instance"
        self.assertEqual(expected, self.action.get_description())
