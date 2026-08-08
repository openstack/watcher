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
from watcher.applier.actions import shelve
from watcher.common import exception
from watcher.tests.unit import base
from watcher.tests.unit.common import utils as test_utils


class TestShelve(test_utils.NovaResourcesMixin, base.TestCase):
    INSTANCE_UUID = "45a37aeb-95ab-4ddb-a305-7d9f62c2f5ba"

    def setUp(self):
        super().setUp()

        self.m_helper = self.useFixture(
            fixtures.MockPatch(
                "watcher.common.nova_helper.NovaHelper", autospec=False
            )
        ).mock.return_value

        self.input_parameters = {
            baction.BaseAction.RESOURCE_ID: self.INSTANCE_UUID
        }
        self.instance = self.create_openstacksdk_server(
            id=self.INSTANCE_UUID, status='ACTIVE'
        )
        self.action = shelve.Shelve(mock.Mock())
        self.action.input_parameters = self.input_parameters

    def test_parameters(self):
        parameters = {baction.BaseAction.RESOURCE_ID: self.INSTANCE_UUID}
        self.action.input_parameters = parameters
        self.assertTrue(self.action.validate_parameters())

    def test_parameters_exception_empty_resource_id(self):
        parameters = {baction.BaseAction.RESOURCE_ID: None}
        self.action.input_parameters = parameters
        self.assertRaises(
            jsonschema.ValidationError, self.action.validate_parameters
        )

    def test_parameters_exception_invalid_uuid_format(self):
        parameters = {baction.BaseAction.RESOURCE_ID: "invalid-uuid"}
        self.action.input_parameters = parameters
        self.assertRaises(
            jsonschema.ValidationError, self.action.validate_parameters
        )

    def test_parameters_exception_missing_resource_id(self):
        parameters = {}
        self.action.input_parameters = parameters
        self.assertRaises(
            jsonschema.ValidationError, self.action.validate_parameters
        )

    def test_instance_uuid_property(self):
        self.assertEqual(self.INSTANCE_UUID, self.action.instance_uuid)

    def test_pre_condition_instance_not_found(self):
        err = exception.ComputeResourceNotFound()
        self.m_helper.find_instance.side_effect = err

        self.assertRaisesRegex(
            exception.ActionSkipped,
            f"Instance {self.INSTANCE_UUID} not found",
            self.action.pre_condition,
        )

        self.m_helper.find_instance.assert_called_once_with(self.INSTANCE_UUID)

    def test_pre_condition_instance_already_shelved(self):
        self.instance.status = 'SHELVED'
        self.m_helper.find_instance.return_value = self.instance

        self.assertRaisesRegex(
            exception.ActionSkipped,
            f"Instance {self.INSTANCE_UUID} is already shelved",
            self.action.pre_condition,
        )
        self.m_helper.find_instance.assert_called_once_with(self.INSTANCE_UUID)

    def test_pre_condition_instance_already_shelved_offloaded(self):
        self.instance.status = 'SHELVED_OFFLOADED'
        self.m_helper.find_instance.return_value = self.instance

        self.assertRaisesRegex(
            exception.ActionSkipped,
            f"Instance {self.INSTANCE_UUID} is already shelved",
            self.action.pre_condition,
        )
        self.m_helper.find_instance.assert_called_once_with(self.INSTANCE_UUID)

    def test_pre_condition_instance_active(self):
        self.m_helper.find_instance.return_value = self.instance

        result = self.action.pre_condition()

        self.assertIsNone(result)
        self.m_helper.find_instance.assert_called_once_with(self.INSTANCE_UUID)

    def test_execute_success(self):
        self.m_helper.shelve_instance.return_value = True

        result = self.action.execute()

        self.assertTrue(result)
        self.m_helper.shelve_instance.assert_called_once_with(
            instance_id=self.INSTANCE_UUID
        )

    def test_execute_failure(self):
        self.m_helper.shelve_instance.return_value = False

        result = self.action.execute()

        self.assertFalse(result)
        self.m_helper.shelve_instance.assert_called_once_with(
            instance_id=self.INSTANCE_UUID
        )

    def test_execute_nova_client_error(self):
        self.m_helper.shelve_instance.side_effect = exception.NovaClientError(
            reason="shelve failed"
        )

        result = self.action.execute()

        self.assertFalse(result)

    def test_execute_unexpected_exception(self):
        self.m_helper.shelve_instance.side_effect = Exception("Unexpected")

        result = self.action.execute()

        self.assertFalse(result)

    def test_revert_not_supported(self):
        result = self.action.revert()

        self.assertFalse(result)

    def test_abort_returns_false(self):
        result = self.action.abort()

        self.assertFalse(result)

    def test_get_description(self):
        expected = "Shelve a VM instance"
        self.assertEqual(expected, self.action.get_description())
