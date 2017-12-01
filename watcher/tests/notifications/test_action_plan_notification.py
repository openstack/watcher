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
class TestActionPlanNotification(base.DbTestCase):

    def setUp(self):
        super(TestActionPlanNotification, self).setUp()
        p_get_notifier = mock.patch.object(rpc, 'get_notifier')
        m_get_notifier = p_get_notifier.start()
        self.addCleanup(p_get_notifier.stop)
        self.m_notifier = mock.Mock(spec=om.Notifier)

        def fake_get_notifier(publisher_id):
            self.m_notifier.publisher_id = publisher_id
            return self.m_notifier

        m_get_notifier.side_effect = fake_get_notifier
        self.goal = utils.create_test_goal(mock.Mock())
        self.audit = utils.create_test_audit(mock.Mock(), interval=None)
        self.strategy = utils.create_test_strategy(mock.Mock())

    def test_send_invalid_action_plan(self):
        action_plan = utils.get_test_action_plan(
            mock.Mock(), state='DOESNOTMATTER', audit_id=1)

        self.assertRaises(
            exception.InvalidActionPlan,
            notifications.action_plan.send_update,
            mock.MagicMock(), action_plan, host='node0')

    def test_send_action_plan_update(self):
        action_plan = utils.create_test_action_plan(
            mock.Mock(), state=objects.action_plan.State.ONGOING,
            audit_id=self.audit.id, strategy_id=self.strategy.id,
            audit=self.audit, strategy=self.strategy)
        notifications.action_plan.send_update(
            mock.MagicMock(), action_plan, host='node0',
            old_state=objects.action_plan.State.PENDING)

        # The 1st notification is because we created the object.
        # The 2nd notification is because we created the action plan object.
        self.assertEqual(3, self.m_notifier.info.call_count)
        notification = self.m_notifier.info.call_args[1]
        payload = notification['payload']

        self.assertEqual("infra-optim:node0", self.m_notifier.publisher_id)
        self.assertDictEqual(
            {
                "watcher_object.namespace": "watcher",
                "watcher_object.version": "1.1",
                "watcher_object.data": {
                    "global_efficacy": [],
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
                    "uuid": "76be87bd-3422-43f9-93a0-e85a577e3061",
                    "audit_uuid": "10a47dd1-4874-4298-91cf-eff046dbdb8d",
                    "audit": {
                        "watcher_object.data": {
                            "interval": None,
                            "next_run_time": None,
                            "auto_trigger": False,
                            "parameters": {},
                            "uuid": "10a47dd1-4874-4298-91cf-eff046dbdb8d",
                            "name": "My Audit",
                            "strategy_uuid": None,
                            "goal_uuid": (
                                "f7ad87ae-4298-91cf-93a0-f35a852e3652"),
                            "deleted_at": None,
                            "scope": [],
                            "state": "PENDING",
                            "updated_at": None,
                            "created_at": "2016-10-18T09:52:05Z",
                            "audit_type": "ONESHOT"
                        },
                        "watcher_object.name": "TerseAuditPayload",
                        "watcher_object.namespace": "watcher",
                        "watcher_object.version": "1.2"
                    },
                    "deleted_at": None,
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
                        "watcher_object.name": "ActionPlanStateUpdatePayload"
                    },
                },
                "watcher_object.name": "ActionPlanUpdatePayload"
            },
            payload
        )

    def test_send_action_plan_create(self):
        action_plan = utils.get_test_action_plan(
            mock.Mock(), state=objects.action_plan.State.PENDING,
            audit_id=self.audit.id, strategy_id=self.strategy.id,
            audit=self.audit.as_dict(), strategy=self.strategy.as_dict())
        notifications.action_plan.send_create(
            mock.MagicMock(), action_plan, host='node0')

        self.assertEqual(2, self.m_notifier.info.call_count)
        notification = self.m_notifier.info.call_args[1]
        payload = notification['payload']

        self.assertEqual("infra-optim:node0", self.m_notifier.publisher_id)
        self.assertDictEqual(
            {
                "watcher_object.namespace": "watcher",
                "watcher_object.version": "1.1",
                "watcher_object.data": {
                    "global_efficacy": [],
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
                    "uuid": "76be87bd-3422-43f9-93a0-e85a577e3061",
                    "audit_uuid": "10a47dd1-4874-4298-91cf-eff046dbdb8d",
                    "audit": {
                        "watcher_object.data": {
                            "interval": None,
                            "next_run_time": None,
                            "auto_trigger": False,
                            "parameters": {},
                            "uuid": "10a47dd1-4874-4298-91cf-eff046dbdb8d",
                            "name": "My Audit",
                            "strategy_uuid": None,
                            "goal_uuid": (
                                "f7ad87ae-4298-91cf-93a0-f35a852e3652"),
                            "deleted_at": None,
                            "scope": [],
                            "state": "PENDING",
                            "updated_at": None,
                            "created_at": "2016-10-18T09:52:05Z",
                            "audit_type": "ONESHOT"
                        },
                        "watcher_object.name": "TerseAuditPayload",
                        "watcher_object.namespace": "watcher",
                        "watcher_object.version": "1.2"
                    },
                    "deleted_at": None,
                    "state": "PENDING",
                    "updated_at": None,
                    "created_at": None,
                },
                "watcher_object.name": "ActionPlanCreatePayload"
            },
            payload
        )

    def test_send_action_plan_delete(self):
        action_plan = utils.create_test_action_plan(
            mock.Mock(), state=objects.action_plan.State.DELETED,
            audit_id=self.audit.id, strategy_id=self.strategy.id)
        notifications.action_plan.send_delete(
            mock.MagicMock(), action_plan, host='node0')

        # The 1st notification is because we created the audit object.
        # The 2nd notification is because we created the action plan object.
        self.assertEqual(3, self.m_notifier.info.call_count)
        notification = self.m_notifier.info.call_args[1]
        payload = notification['payload']

        self.assertEqual("infra-optim:node0", self.m_notifier.publisher_id)
        self.assertDictEqual(
            {
                "watcher_object.namespace": "watcher",
                "watcher_object.version": "1.1",
                "watcher_object.data": {
                    "global_efficacy": [],
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
                    "uuid": "76be87bd-3422-43f9-93a0-e85a577e3061",
                    "audit_uuid": "10a47dd1-4874-4298-91cf-eff046dbdb8d",
                    "audit": {
                        "watcher_object.data": {
                            "interval": None,
                            "next_run_time": None,
                            "auto_trigger": False,
                            "parameters": {},
                            "uuid": "10a47dd1-4874-4298-91cf-eff046dbdb8d",
                            "name": "My Audit",
                            "strategy_uuid": None,
                            "goal_uuid": (
                                "f7ad87ae-4298-91cf-93a0-f35a852e3652"),
                            "deleted_at": None,
                            "scope": [],
                            "state": "PENDING",
                            "updated_at": None,
                            "created_at": "2016-10-18T09:52:05Z",
                            "audit_type": "ONESHOT"
                        },
                        "watcher_object.name": "TerseAuditPayload",
                        "watcher_object.namespace": "watcher",
                        "watcher_object.version": "1.2"
                    },
                    "deleted_at": None,
                    "state": "DELETED",
                    "updated_at": None,
                    "created_at": "2016-10-18T09:52:05Z",
                },
                "watcher_object.name": "ActionPlanDeletePayload"
            },
            payload
        )

    def test_send_action_plan_action(self):
        action_plan = utils.create_test_action_plan(
            mock.Mock(), state=objects.action_plan.State.ONGOING,
            audit_id=self.audit.id, strategy_id=self.strategy.id,
            audit=self.audit, strategy=self.strategy)
        notifications.action_plan.send_action_notification(
            mock.MagicMock(), action_plan, host='node0',
            action='execution', phase='start')

        # The 1st notification is because we created the audit object.
        # The 2nd notification is because we created the action plan object.
        self.assertEqual(3, self.m_notifier.info.call_count)
        notification = self.m_notifier.info.call_args[1]

        self.assertEqual("infra-optim:node0", self.m_notifier.publisher_id)
        self.assertDictEqual(
            {
                "event_type": "action_plan.execution.start",
                "payload": {
                    "watcher_object.data": {
                        "created_at": "2016-10-18T09:52:05Z",
                        "deleted_at": None,
                        "fault": None,
                        "audit_uuid": "10a47dd1-4874-4298-91cf-eff046dbdb8d",
                        "audit": {
                            "watcher_object.namespace": "watcher",
                            "watcher_object.name": "TerseAuditPayload",
                            "watcher_object.version": "1.2",
                            "watcher_object.data": {
                                "interval": None,
                                "next_run_time": None,
                                "auto_trigger": False,
                                "parameters": {},
                                "uuid": "10a47dd1-4874-4298-91cf-eff046dbdb8d",
                                "name": "My Audit",
                                "strategy_uuid": None,
                                "goal_uuid": (
                                    "f7ad87ae-4298-91cf-93a0-f35a852e3652"),
                                "deleted_at": None,
                                "scope": [],
                                "state": "PENDING",
                                "updated_at": None,
                                "created_at": "2016-10-18T09:52:05Z",
                                "audit_type": "ONESHOT"
                            }
                        },
                        "global_efficacy": [],
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
                        "uuid": "76be87bd-3422-43f9-93a0-e85a577e3061"
                    },
                    "watcher_object.name": "ActionPlanActionPayload",
                    "watcher_object.namespace": "watcher",
                    "watcher_object.version": "1.1"
                }
            },
            notification
        )

    def test_send_action_plan_action_with_error(self):
        action_plan = utils.create_test_action_plan(
            mock.Mock(), state=objects.action_plan.State.ONGOING,
            audit_id=self.audit.id, strategy_id=self.strategy.id,
            audit=self.audit, strategy=self.strategy)

        try:
            # This is to load the exception in sys.exc_info()
            raise exception.WatcherException("TEST")
        except exception.WatcherException:
            notifications.action_plan.send_action_notification(
                mock.MagicMock(), action_plan, host='node0',
                action='execution', priority='error', phase='error')

        self.assertEqual(1, self.m_notifier.error.call_count)
        notification = self.m_notifier.error.call_args[1]
        self.assertEqual("infra-optim:node0", self.m_notifier.publisher_id)
        self.assertDictEqual(
            {
                "event_type": "action_plan.execution.error",
                "payload": {
                    "watcher_object.data": {
                        "created_at": "2016-10-18T09:52:05Z",
                        "deleted_at": None,
                        "fault": {
                            "watcher_object.data": {
                                "exception": "WatcherException",
                                "exception_message": "TEST",
                                "function_name": (
                                    "test_send_action_plan_action_with_error"),
                                "module_name": "watcher.tests.notifications."
                                               "test_action_plan_notification"
                            },
                            "watcher_object.name": "ExceptionPayload",
                            "watcher_object.namespace": "watcher",
                            "watcher_object.version": "1.0"
                        },
                        "audit_uuid": "10a47dd1-4874-4298-91cf-eff046dbdb8d",
                        "audit": {
                            "watcher_object.data": {
                                "interval": None,
                                "next_run_time": None,
                                "auto_trigger": False,
                                "parameters": {},
                                "uuid": "10a47dd1-4874-4298-91cf-eff046dbdb8d",
                                "name": "My Audit",
                                "strategy_uuid": None,
                                "goal_uuid": (
                                    "f7ad87ae-4298-91cf-93a0-f35a852e3652"),
                                "deleted_at": None,
                                "scope": [],
                                "state": "PENDING",
                                "updated_at": None,
                                "created_at": "2016-10-18T09:52:05Z",
                                "audit_type": "ONESHOT"
                            },
                            "watcher_object.name": "TerseAuditPayload",
                            "watcher_object.namespace": "watcher",
                            "watcher_object.version": "1.2"
                        },
                        "global_efficacy": [],
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
                        "uuid": "76be87bd-3422-43f9-93a0-e85a577e3061"
                    },
                    "watcher_object.name": "ActionPlanActionPayload",
                    "watcher_object.namespace": "watcher",
                    "watcher_object.version": "1.1"
                }
            },
            notification
        )

    def test_send_action_plan_cancel(self):
        action_plan = utils.create_test_action_plan(
            mock.Mock(), state=objects.action_plan.State.ONGOING,
            audit_id=self.audit.id, strategy_id=self.strategy.id,
            audit=self.audit, strategy=self.strategy)
        notifications.action_plan.send_cancel_notification(
            mock.MagicMock(), action_plan, host='node0',
            action='cancel', phase='start')

        # The 1st notification is because we created the audit object.
        # The 2nd notification is because we created the action plan object.
        self.assertEqual(3, self.m_notifier.info.call_count)
        notification = self.m_notifier.info.call_args[1]
        self.assertEqual("infra-optim:node0", self.m_notifier.publisher_id)
        self.assertDictEqual(
            {
                "event_type": "action_plan.cancel.start",
                "payload": {
                    "watcher_object.data": {
                        "created_at": "2016-10-18T09:52:05Z",
                        "deleted_at": None,
                        "fault": None,
                        "audit_uuid": "10a47dd1-4874-4298-91cf-eff046dbdb8d",
                        "audit": {
                            "watcher_object.namespace": "watcher",
                            "watcher_object.name": "TerseAuditPayload",
                            "watcher_object.version": "1.2",
                            "watcher_object.data": {
                                "interval": None,
                                "next_run_time": None,
                                "auto_trigger": False,
                                "parameters": {},
                                "uuid": "10a47dd1-4874-4298-91cf-eff046dbdb8d",
                                'name': 'My Audit',
                                "strategy_uuid": None,
                                "goal_uuid": (
                                    "f7ad87ae-4298-91cf-93a0-f35a852e3652"),
                                "deleted_at": None,
                                "scope": [],
                                "state": "PENDING",
                                "updated_at": None,
                                "created_at": "2016-10-18T09:52:05Z",
                                "audit_type": "ONESHOT"
                            }
                        },
                        "global_efficacy": [],
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
                        "uuid": "76be87bd-3422-43f9-93a0-e85a577e3061"
                    },
                    "watcher_object.name": "ActionPlanCancelPayload",
                    "watcher_object.namespace": "watcher",
                    "watcher_object.version": "1.1"
                }
            },
            notification
        )

    def test_send_action_plan_cancel_with_error(self):
        action_plan = utils.create_test_action_plan(
            mock.Mock(), state=objects.action_plan.State.ONGOING,
            audit_id=self.audit.id, strategy_id=self.strategy.id,
            audit=self.audit, strategy=self.strategy)

        try:
            # This is to load the exception in sys.exc_info()
            raise exception.WatcherException("TEST")
        except exception.WatcherException:
            notifications.action_plan.send_cancel_notification(
                mock.MagicMock(), action_plan, host='node0',
                action='cancel', priority='error', phase='error')

        self.assertEqual(1, self.m_notifier.error.call_count)
        notification = self.m_notifier.error.call_args[1]
        self.assertEqual("infra-optim:node0", self.m_notifier.publisher_id)
        self.assertDictEqual(
            {
                "event_type": "action_plan.cancel.error",
                "payload": {
                    "watcher_object.data": {
                        "created_at": "2016-10-18T09:52:05Z",
                        "deleted_at": None,
                        "fault": {
                            "watcher_object.data": {
                                "exception": "WatcherException",
                                "exception_message": "TEST",
                                "function_name": (
                                    "test_send_action_plan_cancel_with_error"),
                                "module_name": "watcher.tests.notifications."
                                               "test_action_plan_notification"
                            },
                            "watcher_object.name": "ExceptionPayload",
                            "watcher_object.namespace": "watcher",
                            "watcher_object.version": "1.0"
                        },
                        "audit_uuid": "10a47dd1-4874-4298-91cf-eff046dbdb8d",
                        "audit": {
                            "watcher_object.data": {
                                "interval": None,
                                "next_run_time": None,
                                "auto_trigger": False,
                                "parameters": {},
                                "uuid": "10a47dd1-4874-4298-91cf-eff046dbdb8d",
                                'name': 'My Audit',
                                "strategy_uuid": None,
                                "goal_uuid": (
                                    "f7ad87ae-4298-91cf-93a0-f35a852e3652"),
                                "deleted_at": None,
                                "scope": [],
                                "state": "PENDING",
                                "updated_at": None,
                                "created_at": "2016-10-18T09:52:05Z",
                                "audit_type": "ONESHOT"
                            },
                            "watcher_object.name": "TerseAuditPayload",
                            "watcher_object.namespace": "watcher",
                            "watcher_object.version": "1.2"
                        },
                        "global_efficacy": [],
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
                        "uuid": "76be87bd-3422-43f9-93a0-e85a577e3061"
                    },
                    "watcher_object.name": "ActionPlanCancelPayload",
                    "watcher_object.namespace": "watcher",
                    "watcher_object.version": "1.1"
                }
            },
            notification
        )
