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
class TestActionNotification(base.DbTestCase):

    def setUp(self):
        super(TestActionNotification, self).setUp()
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
        self.audit = utils.create_test_audit(mock.Mock(),
                                             strategy_id=self.strategy.id)
        self.action_plan = utils.create_test_action_plan(mock.Mock())

    def test_send_invalid_action_plan(self):
        action_plan = utils.get_test_action_plan(
            mock.Mock(), state='DOESNOTMATTER', audit_id=1)

        self.assertRaises(
            exception.InvalidActionPlan,
            notifications.action_plan.send_update,
            mock.MagicMock(), action_plan, host='node0')

    def test_send_action_update(self):
        action = utils.create_test_action(
            mock.Mock(), state=objects.action.State.ONGOING,
            action_type='nop', input_parameters={'param1': 1, 'param2': 2},
            parents=[], action_plan_id=self.action_plan.id)
        notifications.action.send_update(
            mock.MagicMock(), action, host='node0',
            old_state=objects.action.State.PENDING)

        # The 1st notification is because we created the object.
        # The 2nd notification is because we created the action plan object.
        self.assertEqual(4, self.m_notifier.info.call_count)
        notification = self.m_notifier.info.call_args[1]
        payload = notification['payload']

        self.assertEqual("infra-optim:node0", self.m_notifier.publisher_id)
        self.assertDictEqual(
            {
                'watcher_object.namespace': 'watcher',
                'watcher_object.version': '1.0',
                'watcher_object.name': 'ActionUpdatePayload',
                'watcher_object.data': {
                    'uuid': '10a47dd1-4874-4298-91cf-eff046dbdb8d',
                    'input_parameters': {
                        'param2': 2,
                        'param1': 1
                    },
                    'created_at': '2016-10-18T09:52:05Z',
                    'updated_at': None,
                    'state_update': {
                        'watcher_object.namespace': 'watcher',
                        'watcher_object.version': '1.0',
                        'watcher_object.name': 'ActionStateUpdatePayload',
                        'watcher_object.data': {
                            'old_state': 'PENDING',
                            'state': 'ONGOING'
                        }
                    },
                    'state': 'ONGOING',
                    'action_plan': {
                        'watcher_object.namespace': 'watcher',
                        'watcher_object.version': '1.1',
                        'watcher_object.name': 'TerseActionPlanPayload',
                        'watcher_object.data': {
                            'uuid': '76be87bd-3422-43f9-93a0-e85a577e3061',
                            'global_efficacy': [],
                            'created_at': '2016-10-18T09:52:05Z',
                            'updated_at': None,
                            'state': 'ONGOING',
                            'audit_uuid': '10a47dd1-4874-4298'
                                          '-91cf-eff046dbdb8d',
                            'strategy_uuid': 'cb3d0b58-4415-4d90'
                                             '-b75b-1e96878730e3',
                            'deleted_at': None
                        }
                    },
                    'parents': [],
                    'action_type': 'nop',
                    'deleted_at': None
                }
            },
            payload
        )

    def test_send_action_plan_create(self):
        action = utils.create_test_action(
            mock.Mock(), state=objects.action.State.PENDING,
            action_type='nop', input_parameters={'param1': 1, 'param2': 2},
            parents=[], action_plan_id=self.action_plan.id)
        notifications.action.send_create(mock.MagicMock(), action,
                                         host='node0')

        self.assertEqual(4, self.m_notifier.info.call_count)
        notification = self.m_notifier.info.call_args[1]
        payload = notification['payload']

        self.assertEqual("infra-optim:node0", self.m_notifier.publisher_id)
        self.assertDictEqual(
            {
                'watcher_object.namespace': 'watcher',
                'watcher_object.version': '1.0',
                'watcher_object.name': 'ActionCreatePayload',
                'watcher_object.data': {
                    'uuid': '10a47dd1-4874-4298-91cf-eff046dbdb8d',
                    'input_parameters': {
                        'param2': 2,
                        'param1': 1
                    },
                    'created_at': '2016-10-18T09:52:05Z',
                    'updated_at': None,
                    'state': 'PENDING',
                    'action_plan': {
                        'watcher_object.namespace': 'watcher',
                        'watcher_object.version': '1.1',
                        'watcher_object.name': 'TerseActionPlanPayload',
                        'watcher_object.data': {
                            'uuid': '76be87bd-3422-43f9-93a0-e85a577e3061',
                            'global_efficacy': [],
                            'created_at': '2016-10-18T09:52:05Z',
                            'updated_at': None,
                            'state': 'ONGOING',
                            'audit_uuid': '10a47dd1-4874-4298'
                                          '-91cf-eff046dbdb8d',
                            'strategy_uuid': 'cb3d0b58-4415-4d90'
                                             '-b75b-1e96878730e3',
                            'deleted_at': None
                        }
                    },
                    'parents': [],
                    'action_type': 'nop',
                    'deleted_at': None
                }
            },
            payload
        )

    def test_send_action_delete(self):
        action = utils.create_test_action(
            mock.Mock(), state=objects.action.State.DELETED,
            action_type='nop', input_parameters={'param1': 1, 'param2': 2},
            parents=[], action_plan_id=self.action_plan.id)
        notifications.action.send_delete(mock.MagicMock(), action,
                                         host='node0')

        # The 1st notification is because we created the audit object.
        # The 2nd notification is because we created the action plan object.
        self.assertEqual(4, self.m_notifier.info.call_count)
        notification = self.m_notifier.info.call_args[1]
        payload = notification['payload']

        self.assertEqual("infra-optim:node0", self.m_notifier.publisher_id)
        self.assertDictEqual(
            {
                'watcher_object.namespace': 'watcher',
                'watcher_object.version': '1.0',
                'watcher_object.name': 'ActionDeletePayload',
                'watcher_object.data': {
                    'uuid': '10a47dd1-4874-4298-91cf-eff046dbdb8d',
                    'input_parameters': {
                        'param2': 2,
                        'param1': 1
                    },
                    'created_at': '2016-10-18T09:52:05Z',
                    'updated_at': None,
                    'state': 'DELETED',
                    'action_plan': {
                        'watcher_object.namespace': 'watcher',
                        'watcher_object.version': '1.1',
                        'watcher_object.name': 'TerseActionPlanPayload',
                        'watcher_object.data': {
                            'uuid': '76be87bd-3422-43f9-93a0-e85a577e3061',
                            'global_efficacy': [],
                            'created_at': '2016-10-18T09:52:05Z',
                            'updated_at': None,
                            'state': 'ONGOING',
                            'audit_uuid': '10a47dd1-4874-4298'
                                          '-91cf-eff046dbdb8d',
                            'strategy_uuid': 'cb3d0b58-4415-4d90'
                                             '-b75b-1e96878730e3',
                            'deleted_at': None
                        }
                    },
                    'parents': [],
                    'action_type': 'nop',
                    'deleted_at': None
                }
            },
            payload
        )

    def test_send_action_execution(self):
        action = utils.create_test_action(
            mock.Mock(), state=objects.action.State.PENDING,
            action_type='nop', input_parameters={'param1': 1, 'param2': 2},
            parents=[], action_plan_id=self.action_plan.id)
        notifications.action.send_execution_notification(
            mock.MagicMock(), action, 'execution', phase='start', host='node0')

        # The 1st notification is because we created the audit object.
        # The 2nd notification is because we created the action plan object.
        self.assertEqual(4, self.m_notifier.info.call_count)
        notification = self.m_notifier.info.call_args[1]

        self.assertEqual("infra-optim:node0", self.m_notifier.publisher_id)
        self.assertDictEqual(
            {
                'event_type': 'action.execution.start',
                'payload': {
                    'watcher_object.namespace': 'watcher',
                    'watcher_object.version': '1.0',
                    'watcher_object.name': 'ActionExecutionPayload',
                    'watcher_object.data': {
                        'uuid': '10a47dd1-4874-4298-91cf-eff046dbdb8d',
                        'input_parameters': {
                            'param2': 2,
                            'param1': 1
                        },
                        'created_at': '2016-10-18T09:52:05Z',
                        'fault': None,
                        'updated_at': None,
                        'state': 'PENDING',
                        'action_plan': {
                            'watcher_object.namespace': 'watcher',
                            'watcher_object.version': '1.1',
                            'watcher_object.name': 'TerseActionPlanPayload',
                            'watcher_object.data': {
                                'uuid': '76be87bd-3422-43f9-93a0-e85a577e3061',
                                'global_efficacy': [],
                                'created_at': '2016-10-18T09:52:05Z',
                                'updated_at': None,
                                'state': 'ONGOING',
                                'audit_uuid': '10a47dd1-4874-4298'
                                              '-91cf-eff046dbdb8d',
                                'strategy_uuid': 'cb3d0b58-4415-4d90'
                                                 '-b75b-1e96878730e3',
                                'deleted_at': None
                            }
                        },
                        'parents': [],
                        'action_type': 'nop',
                        'deleted_at': None
                    }
                }
            },
            notification
        )

    def test_send_action_execution_with_error(self):
        action = utils.create_test_action(
            mock.Mock(), state=objects.action.State.FAILED,
            action_type='nop', input_parameters={'param1': 1, 'param2': 2},
            parents=[], action_plan_id=self.action_plan.id)

        try:
            # This is to load the exception in sys.exc_info()
            raise exception.WatcherException("TEST")
        except exception.WatcherException:
            notifications.action.send_execution_notification(
                mock.MagicMock(), action, 'execution', phase='error',
                host='node0', priority='error')

        self.assertEqual(1, self.m_notifier.error.call_count)
        notification = self.m_notifier.error.call_args[1]
        self.assertEqual("infra-optim:node0", self.m_notifier.publisher_id)
        self.assertDictEqual(
            {
                'event_type': 'action.execution.error',
                'payload': {
                    'watcher_object.namespace': 'watcher',
                    'watcher_object.version': '1.0',
                    'watcher_object.name': 'ActionExecutionPayload',
                    'watcher_object.data': {
                        'uuid': '10a47dd1-4874-4298-91cf-eff046dbdb8d',
                        'input_parameters': {
                            'param2': 2,
                            'param1': 1
                        },
                        'created_at': '2016-10-18T09:52:05Z',
                        'fault': {
                            'watcher_object.data': {
                                'exception': u'WatcherException',
                                'exception_message': u'TEST',
                                'function_name': (
                                    'test_send_action_execution_with_error'),
                                'module_name': (
                                    'watcher.tests.notifications.'
                                    'test_action_notification')
                            },
                            'watcher_object.name': 'ExceptionPayload',
                            'watcher_object.namespace': 'watcher',
                            'watcher_object.version': '1.0'
                        },
                        'updated_at': None,
                        'state': 'FAILED',
                        'action_plan': {
                            'watcher_object.namespace': 'watcher',
                            'watcher_object.version': '1.1',
                            'watcher_object.name': 'TerseActionPlanPayload',
                            'watcher_object.data': {
                                'uuid': '76be87bd-3422-43f9-93a0-e85a577e3061',
                                'global_efficacy': [],
                                'created_at': '2016-10-18T09:52:05Z',
                                'updated_at': None,
                                'state': 'ONGOING',
                                'audit_uuid': '10a47dd1-4874-4298'
                                              '-91cf-eff046dbdb8d',
                                'strategy_uuid': 'cb3d0b58-4415-4d90'
                                                 '-b75b-1e96878730e3',
                                'deleted_at': None
                            }
                        },
                        'parents': [],
                        'action_type': 'nop',
                        'deleted_at': None
                    }
                }
            },
            notification
        )

    def test_send_action_cancel(self):
        action = utils.create_test_action(
            mock.Mock(), state=objects.action.State.PENDING,
            action_type='nop', input_parameters={'param1': 1, 'param2': 2},
            parents=[], action_plan_id=self.action_plan.id)
        notifications.action.send_cancel_notification(
            mock.MagicMock(), action, 'cancel', phase='start', host='node0')

        # The 1st notification is because we created the audit object.
        # The 2nd notification is because we created the action plan object.
        self.assertEqual(4, self.m_notifier.info.call_count)
        notification = self.m_notifier.info.call_args[1]

        self.assertEqual("infra-optim:node0", self.m_notifier.publisher_id)
        self.assertDictEqual(
            {
                'event_type': 'action.cancel.start',
                'payload': {
                    'watcher_object.namespace': 'watcher',
                    'watcher_object.version': '1.0',
                    'watcher_object.name': 'ActionCancelPayload',
                    'watcher_object.data': {
                        'uuid': '10a47dd1-4874-4298-91cf-eff046dbdb8d',
                        'input_parameters': {
                            'param2': 2,
                            'param1': 1
                        },
                        'created_at': '2016-10-18T09:52:05Z',
                        'fault': None,
                        'updated_at': None,
                        'state': 'PENDING',
                        'action_plan': {
                            'watcher_object.namespace': 'watcher',
                            'watcher_object.version': '1.1',
                            'watcher_object.name': 'TerseActionPlanPayload',
                            'watcher_object.data': {
                                'uuid': '76be87bd-3422-43f9-93a0-e85a577e3061',
                                'global_efficacy': [],
                                'created_at': '2016-10-18T09:52:05Z',
                                'updated_at': None,
                                'state': 'ONGOING',
                                'audit_uuid': '10a47dd1-4874-4298'
                                              '-91cf-eff046dbdb8d',
                                'strategy_uuid': 'cb3d0b58-4415-4d90'
                                                 '-b75b-1e96878730e3',
                                'deleted_at': None
                            }
                        },
                        'parents': [],
                        'action_type': 'nop',
                        'deleted_at': None
                    }
                }
            },
            notification
        )

    def test_send_action_cancel_with_error(self):
        action = utils.create_test_action(
            mock.Mock(), state=objects.action.State.FAILED,
            action_type='nop', input_parameters={'param1': 1, 'param2': 2},
            parents=[], action_plan_id=self.action_plan.id)

        try:
            # This is to load the exception in sys.exc_info()
            raise exception.WatcherException("TEST")
        except exception.WatcherException:
            notifications.action.send_cancel_notification(
                mock.MagicMock(), action, 'cancel', phase='error',
                host='node0', priority='error')

        self.assertEqual(1, self.m_notifier.error.call_count)
        notification = self.m_notifier.error.call_args[1]
        self.assertEqual("infra-optim:node0", self.m_notifier.publisher_id)
        self.assertDictEqual(
            {
                'event_type': 'action.cancel.error',
                'payload': {
                    'watcher_object.namespace': 'watcher',
                    'watcher_object.version': '1.0',
                    'watcher_object.name': 'ActionCancelPayload',
                    'watcher_object.data': {
                        'uuid': '10a47dd1-4874-4298-91cf-eff046dbdb8d',
                        'input_parameters': {
                            'param2': 2,
                            'param1': 1
                        },
                        'created_at': '2016-10-18T09:52:05Z',
                        'fault': {
                            'watcher_object.data': {
                                'exception': u'WatcherException',
                                'exception_message': u'TEST',
                                'function_name': (
                                    'test_send_action_cancel_with_error'),
                                'module_name': (
                                    'watcher.tests.notifications.'
                                    'test_action_notification')
                            },
                            'watcher_object.name': 'ExceptionPayload',
                            'watcher_object.namespace': 'watcher',
                            'watcher_object.version': '1.0'
                        },
                        'updated_at': None,
                        'state': 'FAILED',
                        'action_plan': {
                            'watcher_object.namespace': 'watcher',
                            'watcher_object.version': '1.1',
                            'watcher_object.name': 'TerseActionPlanPayload',
                            'watcher_object.data': {
                                'uuid': '76be87bd-3422-43f9-93a0-e85a577e3061',
                                'global_efficacy': [],
                                'created_at': '2016-10-18T09:52:05Z',
                                'updated_at': None,
                                'state': 'ONGOING',
                                'audit_uuid': '10a47dd1-4874-4298'
                                              '-91cf-eff046dbdb8d',
                                'strategy_uuid': 'cb3d0b58-4415-4d90'
                                                 '-b75b-1e96878730e3',
                                'deleted_at': None
                            }
                        },
                        'parents': [],
                        'action_type': 'nop',
                        'deleted_at': None
                    }
                }
            },
            notification
        )
