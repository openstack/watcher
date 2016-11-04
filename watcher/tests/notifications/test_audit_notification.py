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

import freezegun
import mock

from watcher.common import exception
from watcher import notifications
from watcher import objects
from watcher.tests.db import base
from watcher.tests.objects import utils


class TestAuditNotification(base.DbTestCase):

    @mock.patch.object(notifications.audit.AuditUpdateNotification, '_emit')
    def test_send_version_invalid_audit(self, mock_emit):
        audit = utils.get_test_audit(mock.Mock(), state='DOESNOTMATTER',
                                     goal_id=1)

        self.assertRaises(
            exception.InvalidAudit,
            notifications.audit.send_update,
            mock.MagicMock(), audit, 'host', 'node0')

    @freezegun.freeze_time('2016-10-18T09:52:05.219414')
    @mock.patch.object(notifications.audit.AuditUpdateNotification, '_emit')
    def test_send_version_audit_update_with_strategy(self, mock_emit):
        goal = utils.create_test_goal(mock.Mock())
        strategy = utils.create_test_strategy(mock.Mock())
        audit = utils.create_test_audit(
            mock.Mock(), state=objects.audit.State.ONGOING,
            goal_id=goal.id, strategy_id=strategy.id,
            goal=goal, strategy=strategy)
        notifications.audit.send_update(
            mock.MagicMock(), audit, 'host', 'node0',
            old_state=objects.audit.State.PENDING)

        self.assertEqual(1, mock_emit.call_count)
        notification = mock_emit.call_args_list[0][1]
        payload = notification['payload']

        self.assertDictEqual(
            {
                "watcher_object.namespace": "watcher",
                "watcher_object.version": "1.0",
                "watcher_object.data": {
                    "interval": 3600,
                    "strategy": {
                        "watcher_object.namespace": "watcher",
                        "watcher_object.version": "1.0",
                        "watcher_object.data": {
                            "updated_at": None,
                            "uuid": "cb3d0b58-4415-4d90-b75b-1e96878730e3",
                            "name": "TEST",
                            "parameters_spec": {},
                            "created_at": "2016-10-18T09:52:05Z",
                            "display_name": "test strategy",
                            "deleted_at": None
                        },
                        "watcher_object.name": "StrategyPayload"
                    },
                    "parameters": {},
                    "uuid": "10a47dd1-4874-4298-91cf-eff046dbdb8d",
                    "goal": {
                        "watcher_object.namespace": "watcher",
                        "watcher_object.version": "1.0",
                        "watcher_object.data": {
                            "updated_at": None,
                            "uuid": "f7ad87ae-4298-91cf-93a0-f35a852e3652",
                            "name": "TEST",
                            "efficacy_specification": [],
                            "created_at": "2016-10-18T09:52:05Z",
                            "display_name": "test goal",
                            "deleted_at": None
                        },
                        "watcher_object.name": "GoalPayload"
                    },
                    "deleted_at": None,
                    "scope": [],
                    "state": "ONGOING",
                    "updated_at": None,
                    "created_at": "2016-10-18T09:52:05Z",
                    "state_update": {
                        "watcher_object.namespace": "watcher",
                        "watcher_object.version": "1.0",
                        "watcher_object.data": {
                            "old_state": "PENDING",
                            "state": "ONGOING"
                        },
                        "watcher_object.name": "AuditStateUpdatePayload"
                    },
                    "audit_type": "ONESHOT"
                },
                "watcher_object.name": "AuditUpdatePayload"
            },
            payload
        )

    @freezegun.freeze_time('2016-10-18T09:52:05.219414')
    @mock.patch.object(notifications.audit.AuditUpdateNotification, '_emit')
    def test_send_version_audit_update_without_strategy(self, mock_emit):
        goal = utils.create_test_goal(mock.Mock(), id=1)
        audit = utils.get_test_audit(
            mock.Mock(), state=objects.audit.State.ONGOING,
            goal_id=goal.id, goal=goal)
        notifications.audit.send_update(
            mock.MagicMock(), audit, 'host', 'node0',
            old_state=objects.audit.State.PENDING)

        self.assertEqual(1, mock_emit.call_count)
        notification = mock_emit.call_args_list[0][1]
        payload = notification['payload']

        self.assertDictEqual(
            {
                "watcher_object.namespace": "watcher",
                "watcher_object.version": "1.0",
                "watcher_object.data": {
                    "interval": 3600,
                    "parameters": {},
                    "uuid": "10a47dd1-4874-4298-91cf-eff046dbdb8d",
                    "goal": {
                        "watcher_object.namespace": "watcher",
                        "watcher_object.version": "1.0",
                        "watcher_object.data": {
                            "updated_at": None,
                            "uuid": "f7ad87ae-4298-91cf-93a0-f35a852e3652",
                            "name": "TEST",
                            "efficacy_specification": [],
                            "created_at": "2016-10-18T09:52:05Z",
                            "display_name": "test goal",
                            "deleted_at": None
                        },
                        "watcher_object.name": "GoalPayload"
                    },
                    "strategy": None,
                    "deleted_at": None,
                    "scope": [],
                    "state": "ONGOING",
                    "updated_at": None,
                    "created_at": None,
                    "state_update": {
                        "watcher_object.namespace": "watcher",
                        "watcher_object.version": "1.0",
                        "watcher_object.data": {
                            "old_state": "PENDING",
                            "state": "ONGOING"
                        },
                        "watcher_object.name": "AuditStateUpdatePayload"
                    },
                    "audit_type": "ONESHOT"
                },
                "watcher_object.name": "AuditUpdatePayload"
            },
            payload
        )

    @freezegun.freeze_time('2016-10-18T09:52:05.219414')
    @mock.patch.object(notifications.audit.AuditCreateNotification, '_emit')
    def test_send_version_audit_create(self, mock_emit):
        goal = utils.create_test_goal(mock.Mock())
        strategy = utils.create_test_strategy(mock.Mock())
        audit = utils.get_test_audit(
            mock.Mock(), state=objects.audit.State.PENDING,
            goal_id=goal.id, strategy_id=strategy.id,
            goal=goal.as_dict(), strategy=strategy.as_dict())
        notifications.audit.send_create(
            mock.MagicMock(), audit, 'host', 'node0')

        self.assertEqual(1, mock_emit.call_count)
        notification = mock_emit.call_args_list[0][1]
        payload = notification['payload']

        self.assertDictEqual(
            {
                "watcher_object.namespace": "watcher",
                "watcher_object.version": "1.0",
                "watcher_object.data": {
                    "interval": 3600,
                    "strategy": {
                        "watcher_object.namespace": "watcher",
                        "watcher_object.version": "1.0",
                        "watcher_object.data": {
                            "updated_at": None,
                            "uuid": "cb3d0b58-4415-4d90-b75b-1e96878730e3",
                            "name": "TEST",
                            "parameters_spec": {},
                            "created_at": "2016-10-18T09:52:05Z",
                            "display_name": "test strategy",
                            "deleted_at": None
                        },
                        "watcher_object.name": "StrategyPayload"
                    },
                    "parameters": {},
                    "uuid": "10a47dd1-4874-4298-91cf-eff046dbdb8d",
                    "goal": {
                        "watcher_object.namespace": "watcher",
                        "watcher_object.version": "1.0",
                        "watcher_object.data": {
                            "updated_at": None,
                            "uuid": "f7ad87ae-4298-91cf-93a0-f35a852e3652",
                            "name": "TEST",
                            "efficacy_specification": [],
                            "created_at": "2016-10-18T09:52:05Z",
                            "display_name": "test goal",
                            "deleted_at": None
                        },
                        "watcher_object.name": "GoalPayload"
                    },
                    "deleted_at": None,
                    "scope": [],
                    "state": "PENDING",
                    "updated_at": None,
                    "created_at": None,
                    "audit_type": "ONESHOT"
                },
                "watcher_object.name": "AuditCreatePayload"
            },
            payload
        )

    @freezegun.freeze_time('2016-10-18T09:52:05.219414')
    @mock.patch.object(notifications.audit.AuditDeleteNotification, '_emit')
    def test_send_version_audit_delete(self, mock_emit):
        goal = utils.create_test_goal(mock.Mock())
        strategy = utils.create_test_strategy(mock.Mock())
        audit = utils.create_test_audit(
            mock.Mock(), state=objects.audit.State.DELETED,
            goal_id=goal.id, strategy_id=strategy.id)
        notifications.audit.send_delete(
            mock.MagicMock(), audit, 'host', 'node0')

        self.assertEqual(1, mock_emit.call_count)
        notification = mock_emit.call_args_list[0][1]
        payload = notification['payload']

        self.assertDictEqual(
            {
                "watcher_object.namespace": "watcher",
                "watcher_object.version": "1.0",
                "watcher_object.data": {
                    "interval": 3600,
                    "strategy": {
                        "watcher_object.namespace": "watcher",
                        "watcher_object.version": "1.0",
                        "watcher_object.data": {
                            "updated_at": None,
                            "uuid": "cb3d0b58-4415-4d90-b75b-1e96878730e3",
                            "name": "TEST",
                            "parameters_spec": {},
                            "created_at": "2016-10-18T09:52:05Z",
                            "display_name": "test strategy",
                            "deleted_at": None
                        },
                        "watcher_object.name": "StrategyPayload"
                    },
                    "parameters": {},
                    "uuid": "10a47dd1-4874-4298-91cf-eff046dbdb8d",
                    "goal": {
                        "watcher_object.namespace": "watcher",
                        "watcher_object.version": "1.0",
                        "watcher_object.data": {
                            "updated_at": None,
                            "uuid": "f7ad87ae-4298-91cf-93a0-f35a852e3652",
                            "name": "TEST",
                            "efficacy_specification": [],
                            "created_at": "2016-10-18T09:52:05Z",
                            "display_name": "test goal",
                            "deleted_at": None
                        },
                        "watcher_object.name": "GoalPayload"
                    },
                    "deleted_at": None,
                    "scope": [],
                    "state": "DELETED",
                    "updated_at": None,
                    "created_at": "2016-10-18T09:52:05Z",
                    "audit_type": "ONESHOT"
                },
                "watcher_object.name": "AuditDeletePayload"
            },
            payload
        )
