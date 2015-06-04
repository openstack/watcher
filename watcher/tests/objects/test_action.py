# Copyright 2015 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock
from testtools.matchers import HasLength

from watcher.common import exception
# from watcher.common import utils as w_utils
from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils


class TestActionObject(base.DbTestCase):

    def setUp(self):
        super(TestActionObject, self).setUp()
        self.fake_action = utils.get_test_action()

    def test_get_by_id(self):
        action_id = self.fake_action['id']
        with mock.patch.object(self.dbapi, 'get_action_by_id',
                               autospec=True) as mock_get_action:
            mock_get_action.return_value = self.fake_action
            action = objects.Action.get(self.context, action_id)
            mock_get_action.assert_called_once_with(self.context,
                                                    action_id)
            self.assertEqual(self.context, action._context)

    def test_get_by_uuid(self):
        uuid = self.fake_action['uuid']
        with mock.patch.object(self.dbapi, 'get_action_by_uuid',
                               autospec=True) as mock_get_action:
            mock_get_action.return_value = self.fake_action
            action = objects.Action.get(self.context, uuid)
            mock_get_action.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, action._context)

    def test_get_bad_id_and_uuid(self):
        self.assertRaises(exception.InvalidIdentity,
                          objects.Action.get, self.context, 'not-a-uuid')

    def test_list(self):
        with mock.patch.object(self.dbapi, 'get_action_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_action]
            actions = objects.Action.list(self.context)
            self.assertEqual(mock_get_list.call_count, 1)
            self.assertThat(actions, HasLength(1))
            self.assertIsInstance(actions[0], objects.Action)
            self.assertEqual(self.context, actions[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_action',
                               autospec=True) as mock_create_action:
            mock_create_action.return_value = self.fake_action
            action = objects.Action(self.context, **self.fake_action)

            action.create()
            mock_create_action.assert_called_once_with(self.fake_action)
            self.assertEqual(self.context, action._context)

    def test_destroy(self):
        uuid = self.fake_action['uuid']
        with mock.patch.object(self.dbapi, 'get_action_by_uuid',
                               autospec=True) as mock_get_action:
            mock_get_action.return_value = self.fake_action
            with mock.patch.object(self.dbapi, 'destroy_action',
                                   autospec=True) as mock_destroy_action:
                action = objects.Action.get_by_uuid(self.context, uuid)
                action.destroy()
                mock_get_action.assert_called_once_with(self.context, uuid)
                mock_destroy_action.assert_called_once_with(uuid)
                self.assertEqual(self.context, action._context)

    def test_save(self):
        uuid = self.fake_action['uuid']
        with mock.patch.object(self.dbapi, 'get_action_by_uuid',
                               autospec=True) as mock_get_action:
            mock_get_action.return_value = self.fake_action
            with mock.patch.object(self.dbapi, 'update_action',
                                   autospec=True) as mock_update_action:
                action = objects.Action.get_by_uuid(self.context, uuid)
                action.state = 'SUCCESS'
                action.save()

                mock_get_action.assert_called_once_with(self.context, uuid)
                mock_update_action.assert_called_once_with(
                    uuid, {'state': 'SUCCESS'})
                self.assertEqual(self.context, action._context)

    def test_refresh(self):
        uuid = self.fake_action['uuid']
        returns = [dict(self.fake_action, state="first state"),
                   dict(self.fake_action, state="second state")]
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        with mock.patch.object(self.dbapi, 'get_action_by_uuid',
                               side_effect=returns,
                               autospec=True) as mock_get_action:
            action = objects.Action.get(self.context, uuid)
            self.assertEqual("first state", action.state)
            action.refresh()
            self.assertEqual("second state", action.state)
            self.assertEqual(expected, mock_get_action.call_args_list)
            self.assertEqual(self.context, action._context)
