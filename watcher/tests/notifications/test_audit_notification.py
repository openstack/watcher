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
import oslo_messaging as om

from watcher.common import exception
from watcher.common import rpc
from watcher import notifications
from watcher import objects
from watcher.tests.db import base
from watcher.tests.objects import utils


@freezegun.freeze_time('2016-10-18T09:52:05.219414')
class TestAuditNotification(base.DbTestCase):

    def setUp(self):
        super(TestAuditNotification, self).setUp()
        p_get_notifier = mock.patch.object(rpc, 'get_notifier')
        m_get_notifier = p_get_notifier.start()
        self.addCleanup(p_get_notifier.stop)
        self.m_notifier = mock.Mock(spec=om.Notifier)

        def fake_get_notifier(publisher_id):
            self.m_notifier.publisher_id = publisher_id
            return self.m_notifier

        m_get_notifier.side_effect = fake_get_notifier
        self.goal = utils.create_test_goal(mock.Mock())
        self.strategy = utils.create_test_strategy(mock.Mock())

    def test_send_invalid_audit(self):
        audit = utils.get_test_audit(
            mock.Mock(), interval=None, state='DOESNOTMATTER', goal_id=1)

        self.assertRaises(
            exception.InvalidAudit,
            notifications.audit.send_update,
            mock.MagicMock(), audit, host='node0')

    def test_send_audit_update_with_strategy(self):
        audit = utils.create_test_audit(
            mock.Mock(), interval=None, state=objects.audit.State.ONGOING,
            goal_id=self.goal.id, strategy_id=self.strategy.id,
            goal=self.goal, strategy=self.strategy)
        notifications.audit.send_update(
            mock.MagicMock(), audit, host='node0',
            old_state=objects.audit.State.PENDING)

        # The 1st notification is because we created the object.
        self.assertEqual(2, self.m_notifier.info.call_count)
        notification = self.m_notifier.info.call_args[1]
        payload = notification['payload']

        self.assertEqual("infra-optim:node0", self.m_notifier.publisher_id)
        self.assertDictEqual(
            {
                "watcher_object.namespace": "watcher",
                "watcher_object.version": "1.1",
                "watcher_object.data": {
                    "interval": None,
                    "next_run_time": None,
                    "auto_trigger": False,
                    "strategy_uuid": "cb3d0b58-4415-4d90-b75b-1e96878730e3",
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
                    "name": "My Audit",
                    "goal_uuid": "f7ad87ae-4298-91cf-93a0-f35a852e3652",
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

    def test_send_audit_update_without_strategy(self):
        audit = utils.get_test_audit(
            mock.Mock(), interval=None, state=objects.audit.State.ONGOING,
            goal_id=self.goal.id, goal=self.goal)
        notifications.audit.send_update(
            mock.MagicMock(), audit, host='node0',
            old_state=objects.audit.State.PENDING)

        self.assertEqual(1, self.m_notifier.info.call_count)
        notification = self.m_notifier.info.call_args[1]
        payload = notification['payload']

        self.assertEqual("infra-optim:node0", self.m_notifier.publisher_id)
        self.assertDictEqual(
            {
                "watcher_object.namespace": "watcher",
                "watcher_object.version": "1.1",
                "watcher_object.data": {
                    "interval": None,
                    "next_run_time": None,
                    "auto_trigger": False,
                    "parameters": {},
                    "uuid": "10a47dd1-4874-4298-91cf-eff046dbdb8d",
                    "name": "My Audit",
                    "goal_uuid": "f7ad87ae-4298-91cf-93a0-f35a852e3652",
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
                    "strategy_uuid": None,
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

    def test_send_audit_create(self):
        audit = utils.get_test_audit(
            mock.Mock(), interval=None, state=objects.audit.State.PENDING,
            goal_id=self.goal.id, strategy_id=self.strategy.id,
            goal=self.goal.as_dict(), strategy=self.strategy.as_dict())
        notifications.audit.send_create(
            mock.MagicMock(), audit, host='node0')

        self.assertEqual(1, self.m_notifier.info.call_count)
        notification = self.m_notifier.info.call_args[1]
        payload = notification['payload']

        self.assertEqual("infra-optim:node0", self.m_notifier.publisher_id)
        self.assertDictEqual(
            {
                "watcher_object.namespace": "watcher",
                "watcher_object.version": "1.1",
                "watcher_object.data": {
                    "interval": None,
                    "next_run_time": None,
                    "auto_trigger": False,
                    "strategy_uuid": "cb3d0b58-4415-4d90-b75b-1e96878730e3",
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
                    "name": "My Audit",
                    "goal_uuid": "f7ad87ae-4298-91cf-93a0-f35a852e3652",
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

    def test_send_audit_delete(self):
        audit = utils.create_test_audit(
            mock.Mock(), interval=None, state=objects.audit.State.DELETED,
            goal_id=self.goal.id, strategy_id=self.strategy.id)
        notifications.audit.send_delete(
            mock.MagicMock(), audit, host='node0')

        # The 1st notification is because we created the object.
        self.assertEqual(2, self.m_notifier.info.call_count)
        notification = self.m_notifier.info.call_args[1]
        payload = notification['payload']

        self.assertEqual("infra-optim:node0", self.m_notifier.publisher_id)
        self.assertDictEqual(
            {
                "watcher_object.namespace": "watcher",
                "watcher_object.version": "1.1",
                "watcher_object.data": {
                    "interval": None,
                    "next_run_time": None,
                    "auto_trigger": False,
                    "strategy_uuid": "cb3d0b58-4415-4d90-b75b-1e96878730e3",
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
                    "name": "My Audit",
                    "goal_uuid": "f7ad87ae-4298-91cf-93a0-f35a852e3652",
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

    def test_send_audit_action(self):
        audit = utils.create_test_audit(
            mock.Mock(), interval=None, state=objects.audit.State.ONGOING,
            goal_id=self.goal.id, strategy_id=self.strategy.id,
            goal=self.goal, strategy=self.strategy)
        notifications.audit.send_action_notification(
            mock.MagicMock(), audit, host='node0',
            action='strategy', phase='start')

        # The 1st notification is because we created the object.
        self.assertEqual(2, self.m_notifier.info.call_count)
        notification = self.m_notifier.info.call_args[1]
        notification = self.m_notifier.info.call_args[1]

        self.assertEqual("infra-optim:node0", self.m_notifier.publisher_id)
        self.assertDictEqual(
            {
                "event_type": "audit.strategy.start",
                "payload": {
                    "watcher_object.data": {
                        "audit_type": "ONESHOT",
                        "created_at": "2016-10-18T09:52:05Z",
                        "deleted_at": None,
                        "fault": None,
                        "goal_uuid": "f7ad87ae-4298-91cf-93a0-f35a852e3652",
                        "goal": {
                            "watcher_object.data": {
                                "created_at": "2016-10-18T09:52:05Z",
                                "deleted_at": None,
                                "display_name": "test goal",
                                "efficacy_specification": [],
                                "name": "TEST",
                                "updated_at": None,
                                "uuid": "f7ad87ae-4298-91cf-93a0-f35a852e3652"
                            },
                            "watcher_object.name": "GoalPayload",
                            "watcher_object.namespace": "watcher",
                            "watcher_object.version": "1.0"
                        },
                        "interval": None,
                        "next_run_time": None,
                        "auto_trigger": False,
                        "name": "My Audit",
                        "parameters": {},
                        "scope": [],
                        "state": "ONGOING",
                        "strategy_uuid": (
                            "cb3d0b58-4415-4d90-b75b-1e96878730e3"),
                        "strategy": {
                            "watcher_object.data": {
                                "created_at": "2016-10-18T09:52:05Z",
                                "deleted_at": None,
                                "display_name": "test strategy",
                                "name": "TEST",
                                "parameters_spec": {},
                                "updated_at": None,
                                "uuid": "cb3d0b58-4415-4d90-b75b-1e96878730e3"
                            },
                            "watcher_object.name": "StrategyPayload",
                            "watcher_object.namespace": "watcher",
                            "watcher_object.version": "1.0"
                        },
                        "updated_at": None,
                        "uuid": "10a47dd1-4874-4298-91cf-eff046dbdb8d"
                    },
                    "watcher_object.name": "AuditActionPayload",
                    "watcher_object.namespace": "watcher",
                    "watcher_object.version": "1.1"
                }
            },
            notification
        )

    def test_send_audit_action_with_error(self):
        audit = utils.create_test_audit(
            mock.Mock(), interval=None, state=objects.audit.State.ONGOING,
            goal_id=self.goal.id, strategy_id=self.strategy.id,
            goal=self.goal, strategy=self.strategy)

        try:
            # This is to load the exception in sys.exc_info()
            raise exception.WatcherException("TEST")
        except exception.WatcherException:
            notifications.audit.send_action_notification(
                mock.MagicMock(), audit, host='node0',
                action='strategy', priority='error', phase='error')

        self.assertEqual(1, self.m_notifier.error.call_count)
        notification = self.m_notifier.error.call_args[1]
        self.assertEqual("infra-optim:node0", self.m_notifier.publisher_id)
        self.assertDictEqual(
            {
                "event_type": "audit.strategy.error",
                "payload": {
                    "watcher_object.data": {
                        "audit_type": "ONESHOT",
                        "created_at": "2016-10-18T09:52:05Z",
                        "deleted_at": None,
                        "fault": {
                            "watcher_object.data": {
                                "exception": "WatcherException",
                                "exception_message": "TEST",
                                "function_name": (
                                    "test_send_audit_action_with_error"),
                                "module_name": "watcher.tests.notifications."
                                               "test_audit_notification"
                            },
                            "watcher_object.name": "ExceptionPayload",
                            "watcher_object.namespace": "watcher",
                            "watcher_object.version": "1.0"
                        },
                        "goal_uuid": "f7ad87ae-4298-91cf-93a0-f35a852e3652",
                        "goal": {
                            "watcher_object.data": {
                                "created_at": "2016-10-18T09:52:05Z",
                                "deleted_at": None,
                                "display_name": "test goal",
                                "efficacy_specification": [],
                                "name": "TEST",
                                "updated_at": None,
                                "uuid": "f7ad87ae-4298-91cf-93a0-f35a852e3652"
                            },
                            "watcher_object.name": "GoalPayload",
                            "watcher_object.namespace": "watcher",
                            "watcher_object.version": "1.0"
                        },
                        "interval": None,
                        "next_run_time": None,
                        "auto_trigger": False,
                        "name": "My Audit",
                        "parameters": {},
                        "scope": [],
                        "state": "ONGOING",
                        "strategy_uuid": (
                            "cb3d0b58-4415-4d90-b75b-1e96878730e3"),
                        "strategy": {
                            "watcher_object.data": {
                                "created_at": "2016-10-18T09:52:05Z",
                                "deleted_at": None,
                                "display_name": "test strategy",
                                "name": "TEST",
                                "parameters_spec": {},
                                "updated_at": None,
                                "uuid": "cb3d0b58-4415-4d90-b75b-1e96878730e3"
                            },
                            "watcher_object.name": "StrategyPayload",
                            "watcher_object.namespace": "watcher",
                            "watcher_object.version": "1.0"
                        },
                        "updated_at": None,
                        "uuid": "10a47dd1-4874-4298-91cf-eff046dbdb8d"
                    },
                    "watcher_object.name": "AuditActionPayload",
                    "watcher_object.namespace": "watcher",
                    "watcher_object.version": "1.1"
                }
            },
            notification
        )
