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

import collections

import mock
from oslo_versionedobjects import fixture

from watcher.common import exception
from watcher.common import rpc
from watcher.notifications import base as notificationbase
from watcher.objects import base
from watcher.objects import fields as wfields
from watcher.tests import base as testbase
from watcher.tests.objects import test_objects


class TestNotificationBase(testbase.TestCase):

    @base.WatcherObjectRegistry.register_if(False)
    class TestObject(base.WatcherObject):
        VERSION = '1.0'
        fields = {
            'field_1': wfields.StringField(),
            'field_2': wfields.IntegerField(),
            'not_important_field': wfields.IntegerField(),
        }

    @base.WatcherObjectRegistry.register_if(False)
    class TestNotificationPayload(notificationbase.NotificationPayloadBase):
        VERSION = '1.0'

        SCHEMA = {
            'field_1': ('source_field', 'field_1'),
            'field_2': ('source_field', 'field_2'),
        }

        fields = {
            'extra_field': wfields.StringField(),  # filled by ctor
            'field_1': wfields.StringField(),  # filled by the schema
            'field_2': wfields.IntegerField(),   # filled by the schema
        }

        def populate_schema(self, source_field):
            super(TestNotificationBase.TestNotificationPayload,
                  self).populate_schema(source_field=source_field)

    @base.WatcherObjectRegistry.register_if(False)
    class TestNotificationPayloadEmptySchema(
            notificationbase.NotificationPayloadBase):
        VERSION = '1.0'

        fields = {
            'extra_field': wfields.StringField(),  # filled by ctor
        }

    @notificationbase.notification_sample('test-update-1.json')
    @notificationbase.notification_sample('test-update-2.json')
    @base.WatcherObjectRegistry.register_if(False)
    class TestNotification(notificationbase.NotificationBase):
        VERSION = '1.0'
        fields = {
            'payload': wfields.ObjectField('TestNotificationPayload')
        }

    @base.WatcherObjectRegistry.register_if(False)
    class TestNotificationEmptySchema(notificationbase.NotificationBase):
        VERSION = '1.0'
        fields = {
            'payload': wfields.ObjectField(
                'TestNotificationPayloadEmptySchema')
        }

    expected_payload = {
        'watcher_object.name': 'TestNotificationPayload',
        'watcher_object.data': {
            'extra_field': 'test string',
            'field_1': 'test1',
            'field_2': 42},
        'watcher_object.version': '1.0',
        'watcher_object.namespace': 'watcher'}

    def setUp(self):
        super(TestNotificationBase, self).setUp()

        self.my_obj = self.TestObject(field_1='test1',
                                      field_2=42,
                                      not_important_field=13)

        self.payload = self.TestNotificationPayload(
            extra_field='test string')
        self.payload.populate_schema(source_field=self.my_obj)

        self.notification = self.TestNotification(
            event_type=notificationbase.EventType(
                object='test_object',
                action=wfields.NotificationAction.UPDATE,
                phase=wfields.NotificationPhase.START),
            publisher=notificationbase.NotificationPublisher(
                host='fake-host', binary='watcher-fake'),
            priority=wfields.NotificationPriority.INFO,
            payload=self.payload)

    def _verify_notification(self, mock_notifier, mock_context,
                             expected_event_type,
                             expected_payload):
        mock_notifier.prepare.assert_called_once_with(
            publisher_id='watcher-fake:fake-host')
        mock_notify = mock_notifier.prepare.return_value.info
        self.assertTrue(mock_notify.called)
        self.assertEqual(mock_notify.call_args[0][0], mock_context)
        self.assertEqual(mock_notify.call_args[1]['event_type'],
                         expected_event_type)
        actual_payload = mock_notify.call_args[1]['payload']
        self.assertEqual(expected_payload, actual_payload)

    @mock.patch.object(rpc, 'NOTIFIER')
    def test_emit_notification(self, mock_notifier):
        mock_context = mock.Mock()
        mock_context.to_dict.return_value = {}
        self.notification.emit(mock_context)

        self._verify_notification(
            mock_notifier,
            mock_context,
            expected_event_type='test_object.update.start',
            expected_payload=self.expected_payload)

    @mock.patch.object(rpc, 'NOTIFIER')
    def test_no_emit_notifs_disabled(self, mock_notifier):
        # Make sure notifications aren't emitted when notification_level
        # isn't defined, indicating notifications should be disabled
        self.config(notification_level=None)
        notif = self.TestNotification(
            event_type=notificationbase.EventType(
                object='test_object',
                action=wfields.NotificationAction.UPDATE,
                phase=wfields.NotificationPhase.START),
            publisher=notificationbase.NotificationPublisher(
                host='fake-host', binary='watcher-fake'),
            priority=wfields.NotificationPriority.INFO,
            payload=self.payload)

        mock_context = mock.Mock()
        notif.emit(mock_context)

        self.assertFalse(mock_notifier.called)

    @mock.patch.object(rpc, 'NOTIFIER')
    def test_no_emit_level_too_low(self, mock_notifier):
        # Make sure notification doesn't emit when set notification
        # level < config level
        self.config(notification_level='warning')
        notif = self.TestNotification(
            event_type=notificationbase.EventType(
                object='test_object',
                action=wfields.NotificationAction.UPDATE,
                phase=wfields.NotificationPhase.START),
            publisher=notificationbase.NotificationPublisher(
                host='fake-host', binary='watcher-fake'),
            priority=wfields.NotificationPriority.INFO,
            payload=self.payload)

        mock_context = mock.Mock()
        notif.emit(mock_context)

        self.assertFalse(mock_notifier.called)

    @mock.patch.object(rpc, 'NOTIFIER')
    def test_emit_event_type_without_phase(self, mock_notifier):
        noti = self.TestNotification(
            event_type=notificationbase.EventType(
                object='test_object',
                action=wfields.NotificationAction.UPDATE),
            publisher=notificationbase.NotificationPublisher(
                host='fake-host', binary='watcher-fake'),
            priority=wfields.NotificationPriority.INFO,
            payload=self.payload)

        mock_context = mock.Mock()
        mock_context.to_dict.return_value = {}
        noti.emit(mock_context)

        self._verify_notification(
            mock_notifier,
            mock_context,
            expected_event_type='test_object.update',
            expected_payload=self.expected_payload)

    @mock.patch.object(rpc, 'NOTIFIER')
    def test_not_possible_to_emit_if_not_populated(self, mock_notifier):
        non_populated_payload = self.TestNotificationPayload(
            extra_field='test string')
        noti = self.TestNotification(
            event_type=notificationbase.EventType(
                object='test_object',
                action=wfields.NotificationAction.UPDATE),
            publisher=notificationbase.NotificationPublisher(
                host='fake-host', binary='watcher-fake'),
            priority=wfields.NotificationPriority.INFO,
            payload=non_populated_payload)

        mock_context = mock.Mock()
        self.assertRaises(exception.NotificationPayloadError,
                          noti.emit, mock_context)
        self.assertFalse(mock_notifier.called)

    @mock.patch.object(rpc, 'NOTIFIER')
    def test_empty_schema(self, mock_notifier):
        non_populated_payload = self.TestNotificationPayloadEmptySchema(
            extra_field='test string')
        noti = self.TestNotificationEmptySchema(
            event_type=notificationbase.EventType(
                object='test_object',
                action=wfields.NotificationAction.UPDATE),
            publisher=notificationbase.NotificationPublisher(
                host='fake-host', binary='watcher-fake'),
            priority=wfields.NotificationPriority.INFO,
            payload=non_populated_payload)

        mock_context = mock.Mock()
        mock_context.to_dict.return_value = {}
        noti.emit(mock_context)

        self._verify_notification(
            mock_notifier,
            mock_context,
            expected_event_type='test_object.update',
            expected_payload={
                'watcher_object.name': 'TestNotificationPayloadEmptySchema',
                'watcher_object.data': {'extra_field': 'test string'},
                'watcher_object.version': '1.0',
                'watcher_object.namespace': 'watcher'})

    def test_sample_decorator(self):
        self.assertEqual(2, len(self.TestNotification.samples))
        self.assertIn('test-update-1.json', self.TestNotification.samples)
        self.assertIn('test-update-2.json', self.TestNotification.samples)


expected_notification_fingerprints = {
    'EventType': '1.3-4258a2c86eca79fd34a7dffe1278eab9',
    'ExceptionNotification': '1.0-9b69de0724fda8310d05e18418178866',
    'ExceptionPayload': '1.0-4516ae282a55fe2fd5c754967ee6248b',
    'NotificationPublisher': '1.0-bbbc1402fb0e443a3eb227cc52b61545',
    'TerseAuditPayload': '1.0-aaf31166b8698f08d12cae98c380b8e0',
    'AuditPayload': '1.0-30c85c834648c8ca11f54fc5e084d86b',
    'AuditStateUpdatePayload': '1.0-1a1b606bf14a2c468800c2b010801ce5',
    'AuditUpdateNotification': '1.0-9b69de0724fda8310d05e18418178866',
    'AuditUpdatePayload': '1.0-d3aace28d9eb978c1ecf833e108f61f7',
    'AuditCreateNotification': '1.0-9b69de0724fda8310d05e18418178866',
    'AuditCreatePayload': '1.0-30c85c834648c8ca11f54fc5e084d86b',
    'AuditDeleteNotification': '1.0-9b69de0724fda8310d05e18418178866',
    'AuditDeletePayload': '1.0-30c85c834648c8ca11f54fc5e084d86b',
    'AuditActionNotification': '1.0-9b69de0724fda8310d05e18418178866',
    'AuditActionPayload': '1.0-09f5d005f94ba9e5f6b9200170332c52',
    'GoalPayload': '1.0-fa1fecb8b01dd047eef808ded4d50d1a',
    'StrategyPayload': '1.0-94f01c137b083ac236ae82573c1fcfc1',
    'ActionPlanActionPayload': '1.0-34871caf18e9b43a28899953c1c9733a',
    'ActionPlanCreateNotification': '1.0-9b69de0724fda8310d05e18418178866',
    'ActionPlanCreatePayload': '1.0-ffc3087acd73351b14f3dcc30e105027',
    'ActionPlanDeleteNotification': '1.0-9b69de0724fda8310d05e18418178866',
    'ActionPlanDeletePayload': '1.0-ffc3087acd73351b14f3dcc30e105027',
    'ActionPlanPayload': '1.0-ffc3087acd73351b14f3dcc30e105027',
    'ActionPlanStateUpdatePayload': '1.0-1a1b606bf14a2c468800c2b010801ce5',
    'ActionPlanUpdateNotification': '1.0-9b69de0724fda8310d05e18418178866',
    'ActionPlanUpdatePayload': '1.0-7912a45fe53775c721f42aa87f06a023',
    'ActionPlanActionNotification': '1.0-9b69de0724fda8310d05e18418178866',
}


class TestNotificationObjectVersions(testbase.TestCase):
    def setUp(self):
        super(TestNotificationObjectVersions, self).setUp()
        base.WatcherObjectRegistry.register_notification_objects()

    def test_versions(self):
        checker = fixture.ObjectVersionChecker(
            test_objects.get_watcher_objects())
        expected_notification_fingerprints.update(
            test_objects.expected_object_fingerprints)
        expected, actual = checker.test_hashes(
            expected_notification_fingerprints)
        self.assertEqual(expected, actual,
                         'Some notification objects have changed; please make '
                         'sure the versions have been bumped, and then update '
                         'their hashes here.')

    def test_notification_payload_version_depends_on_the_schema(self):
        @base.WatcherObjectRegistry.register_if(False)
        class TestNotificationPayload(
                notificationbase.NotificationPayloadBase):
            VERSION = '1.0'

            SCHEMA = {
                'field_1': ('source_field', 'field_1'),
                'field_2': ('source_field', 'field_2'),
            }

            fields = {
                'extra_field': wfields.StringField(),  # filled by ctor
                'field_1': wfields.StringField(),  # filled by the schema
                'field_2': wfields.IntegerField(),   # filled by the schema
            }

        checker = fixture.ObjectVersionChecker(
            {'TestNotificationPayload': (TestNotificationPayload,)})

        old_hash = checker.get_hashes(extra_data_func=get_extra_data)
        TestNotificationPayload.SCHEMA['field_3'] = ('source_field',
                                                     'field_3')
        new_hash = checker.get_hashes(extra_data_func=get_extra_data)

        self.assertNotEqual(old_hash, new_hash)


def get_extra_data(obj_class):
    extra_data = tuple()

    # Get the SCHEMA items to add to the fingerprint
    # if we are looking at a notification
    if issubclass(obj_class, notificationbase.NotificationPayloadBase):
        schema_data = collections.OrderedDict(
            sorted(obj_class.SCHEMA.items()))

        extra_data += (schema_data,)

    return extra_data
