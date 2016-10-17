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
from watcher.notifications import audit as auditnotifs
from watcher.tests import base as testbase
from watcher.tests.objects import utils


class TestAuditNotification(testbase.TestCase):

    @mock.patch.object(auditnotifs.AuditUpdateNotification, '_emit')
    def test_send_version_invalid_audit(self, mock_emit):
        audit = utils.get_test_audit(mock.Mock(), state='DOESNOTMATTER',
                                     goal_id=1)

        self.assertRaises(
            exception.InvalidAudit,
            auditnotifs.send_update,
            mock.MagicMock(), audit, 'host', 'node0')

    @freezegun.freeze_time('2016-10-18T09:52:05.219414')
    @mock.patch.object(auditnotifs.AuditUpdateNotification, '_emit')
    def test_send_version_audit_update_with_strategy(self, mock_emit):
        goal = utils.get_test_goal(mock.Mock(), id=1)
        strategy = utils.get_test_strategy(mock.Mock(), id=1)
        audit = utils.get_test_audit(mock.Mock(), state='ONGOING',
                                     goal_id=goal.id, strategy_id=strategy.id,
                                     goal=goal, strategy=strategy)
        auditnotifs.send_update(
            mock.MagicMock(), audit, 'host', 'node0', old_state='PENDING')

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
                            "created_at": None,
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
                            "created_at": None,
                            "display_name": "test goal",
                            "deleted_at": None
                        },
                        "watcher_object.name": "GoalPayload"
                    },
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
    @mock.patch.object(auditnotifs.AuditUpdateNotification, '_emit')
    def test_send_version_audit_update_without_strategy(self, mock_emit):
        goal = utils.get_test_goal(mock.Mock(), id=1)
        audit = utils.get_test_audit(
            mock.Mock(), state='ONGOING', goal_id=goal.id, goal=goal)
        auditnotifs.send_update(
            mock.MagicMock(), audit, 'host', 'node0', old_state='PENDING')

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
                            "created_at": None,
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
