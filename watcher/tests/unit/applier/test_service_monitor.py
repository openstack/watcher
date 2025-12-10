# Copyright (c) 2025 Red Hat, Inc.
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

from apscheduler.schedulers import background
import datetime
import freezegun
from oslo_utils import timeutils

from watcher.applier import rpcapi
from watcher.applier import service_monitor
from watcher.applier import sync
from watcher.common import utils as common_utils
from watcher.notifications import service
from watcher import objects
from watcher.tests.unit import base
from watcher.tests.unit.db import base as db_base
from watcher.tests.unit.db import utils


class TestApplierMonitor(base.TestCase):

    @mock.patch.object(background.BackgroundScheduler, 'start', autospec=True)
    def test_start_service_monitoring_service(self, m_start):
        monitor = service_monitor.ApplierMonitor()
        monitor.start()
        m_start.assert_called_once_with(monitor)
        jobs = monitor.get_jobs()
        self.assertEqual(1, len(jobs))

    @mock.patch.object(background.BackgroundScheduler, 'shutdown',
                       autospec=True)
    def test_stop_service_monitoring_service(self, m_shutdown):
        monitor = service_monitor.ApplierMonitor()
        monitor.stop()
        m_shutdown.assert_called_once_with(monitor)

    def test_wait_service_monitoring_service(self):
        monitor = service_monitor.ApplierMonitor()
        # Should not raise any exception
        monitor.wait()

    def test_reset_service_monitoring_service(self):
        monitor = service_monitor.ApplierMonitor()
        # Should not raise any exception
        monitor.reset()


class TestApplierMonitorFunctions(db_base.DbTestCase):

    def setUp(self):
        super().setUp()
        fake_service = utils.get_test_service(
            created_at=timeutils.utcnow())
        self.fake_service = objects.Service(**fake_service)

    @mock.patch.object(service_monitor.ApplierMonitor,
                       'get_service_status', autospec=True)
    @mock.patch.object(objects.Service, 'list', autospec=True)
    @mock.patch.object(service, 'send_service_update')
    @mock.patch.object(objects.ActionPlan, 'list', autospec=True)
    def test_monitor_not_send_notification_on_active(self, m_actionplan_list,
                                                     m_send_notif,
                                                     m_service_list,
                                                     m_get_service_status):
        # Create two applier services
        fake_ap_service1 = utils.get_test_service(
            id=1, name='watcher-applier', host='host1')
        fake_ap_service2 = utils.get_test_service(
            id=2, name='watcher-applier', host='host2')
        fake_ap_service_obj1 = objects.Service(**fake_ap_service1)
        fake_ap_service_obj2 = objects.Service(**fake_ap_service2)

        m_service_list.return_value = [
            fake_ap_service_obj1, fake_ap_service_obj2]

        # First call: both ACTIVE in first and second call
        m_get_service_status.side_effect = [
            objects.service.ServiceStatus.ACTIVE,  # service1 first call
            objects.service.ServiceStatus.ACTIVE,  # service2 first call
            objects.service.ServiceStatus.ACTIVE,  # service1 second call
            objects.service.ServiceStatus.ACTIVE   # service2 second call
        ]

        monitor = service_monitor.ApplierMonitor()

        # Set CONF.host to make this service the leader
        self.flags(host='host1')
        # First call: both ACTIVE
        monitor.monitor_services_status(self.context)
        self.assertEqual(monitor.services_status, {
            fake_ap_service_obj1.id: objects.service.ServiceStatus.ACTIVE,
            fake_ap_service_obj2.id: objects.service.ServiceStatus.ACTIVE
        })
        # Second call: both ACTIVE
        monitor.monitor_services_status(self.context)
        self.assertEqual(monitor.services_status, {
            fake_ap_service_obj1.id: objects.service.ServiceStatus.ACTIVE,
            fake_ap_service_obj2.id: objects.service.ServiceStatus.ACTIVE
        })

        m_send_notif.assert_not_called()
        m_actionplan_list.assert_not_called()

    @mock.patch.object(service_monitor.ApplierMonitor,
                       'get_service_status', autospec=True)
    @mock.patch.object(objects.Service, 'list', autospec=True)
    @mock.patch.object(service, 'send_service_update', autospec=True)
    @mock.patch.object(
        sync.Syncer,
        '_cancel_ongoing_actionplans', autospec=True)
    @mock.patch.object(service_monitor.ApplierMonitor,
                       '_retrigger_pending_actionplans', autospec=True)
    def test_monitor_failover_on_failure(self, m_retrigger,
                                         m_sync_cancel,
                                         m_send_notif,
                                         m_service_list,
                                         m_get_service_status):
        # Create two applier services
        fake_ap_service1 = utils.get_test_service(
            id=1, name='watcher-applier', host='host1')
        fake_ap_service2 = utils.get_test_service(
            id=2, name='watcher-applier', host='host2')
        fake_ap_service_obj1 = objects.Service(**fake_ap_service1)
        fake_ap_service_obj2 = objects.Service(**fake_ap_service2)

        m_service_list.return_value = [
            fake_ap_service_obj1, fake_ap_service_obj2]

        # First call: both ACTIVE
        # Second call: service1 FAILED, service2 ACTIVE
        m_get_service_status.side_effect = [
            objects.service.ServiceStatus.ACTIVE,  # service1 first call
            objects.service.ServiceStatus.ACTIVE,  # service2 first call
            objects.service.ServiceStatus.FAILED,  # service1 second call
            objects.service.ServiceStatus.ACTIVE   # service2 second call
        ]

        monitor = service_monitor.ApplierMonitor()

        # Set CONF.host to make this service the alive and leader one
        # after service1 is marked as failed.
        self.flags(host='host2')
        # First call: both ACTIVE
        monitor.monitor_services_status(self.context)
        self.assertEqual(monitor.services_status, {
            fake_ap_service_obj1.id: objects.service.ServiceStatus.ACTIVE,
            fake_ap_service_obj2.id: objects.service.ServiceStatus.ACTIVE
        })
        # Second call: service1 FAILED, service2 ACTIVE
        monitor.monitor_services_status(self.context)
        self.assertEqual(monitor.services_status, {
            fake_ap_service_obj1.id: objects.service.ServiceStatus.FAILED,
            fake_ap_service_obj2.id: objects.service.ServiceStatus.ACTIVE
        })

        m_send_notif.assert_called_once_with(
            self.context, fake_ap_service_obj1,
            state=objects.service.ServiceStatus.FAILED)
        # Verify ongoing action plan cancel is triggered for the failed
        # service
        m_sync_cancel.assert_called_once_with(mock.ANY, self.context, 'host1')
        # Verify pending action plan retrigger is started for the failed
        # service
        m_retrigger.assert_called_once_with(monitor, self.context, 'host1')

    @mock.patch.object(service_monitor.ApplierMonitor,
                       'get_service_status', autospec=True)
    @mock.patch.object(objects.Service, 'list', autospec=True)
    @mock.patch.object(service, 'send_service_update', autospec=True)
    @mock.patch.object(
        sync.Syncer,
        '_cancel_ongoing_actionplans', autospec=True)
    @mock.patch.object(service_monitor.ApplierMonitor,
                       '_retrigger_pending_actionplans', autospec=True)
    def test_nonleader_monitor_skips_on_failure(self, m_retrigger,
                                                m_sync_cancel,
                                                m_send_notif,
                                                m_service_list,
                                                m_get_service_status):
        # Create two applier services
        fake_ap_service1 = utils.get_test_service(
            id=1, name='watcher-applier', host='host1')
        fake_ap_service2 = utils.get_test_service(
            id=2, name='watcher-applier', host='host2')
        fake_ap_service3 = utils.get_test_service(
            id=3, name='watcher-applier', host='host3')
        fake_ap_service_obj1 = objects.Service(**fake_ap_service1)
        fake_ap_service_obj2 = objects.Service(**fake_ap_service2)
        fake_ap_service_obj3 = objects.Service(**fake_ap_service3)

        m_service_list.return_value = [
            fake_ap_service_obj1, fake_ap_service_obj2, fake_ap_service_obj3]

        # First call: both ACTIVE
        # Second call: service1 FAILED, service2 ACTIVE
        m_get_service_status.side_effect = [
            objects.service.ServiceStatus.ACTIVE,  # service1 first call
            objects.service.ServiceStatus.ACTIVE,  # service2 first call
            objects.service.ServiceStatus.ACTIVE,  # service3 first call
            objects.service.ServiceStatus.FAILED,  # service1 second call
            objects.service.ServiceStatus.ACTIVE,  # service2 second call
            objects.service.ServiceStatus.ACTIVE,  # service3 second call
        ]

        monitor = service_monitor.ApplierMonitor()

        # Set CONF.host to make this service the alive and leader one
        # after service1 is marked as failed.
        self.flags(host='host3')
        # First call: both ACTIVE
        monitor.monitor_services_status(self.context)
        self.assertEqual(monitor.services_status, {
            fake_ap_service_obj1.id: objects.service.ServiceStatus.ACTIVE,
            fake_ap_service_obj2.id: objects.service.ServiceStatus.ACTIVE,
            fake_ap_service_obj3.id: objects.service.ServiceStatus.ACTIVE
        })
        # Second call: service1 FAILED, service2 ACTIVE
        monitor.monitor_services_status(self.context)
        self.assertEqual(monitor.services_status, {
            fake_ap_service_obj1.id: objects.service.ServiceStatus.FAILED,
            fake_ap_service_obj2.id: objects.service.ServiceStatus.ACTIVE,
            fake_ap_service_obj3.id: objects.service.ServiceStatus.ACTIVE
        })

        # Only the leader should send notifications
        m_send_notif.assert_not_called()
        # Only the leader should cancel ongoing action plans
        m_sync_cancel.assert_not_called()
        # Only the leader should retrigger pending action plans
        m_retrigger.assert_not_called()

    @freezegun.freeze_time("2016-10-18T09:52:05.219414")
    def test_get_service_status_up(self):
        fake_service = utils.get_test_service(
            created_at=timeutils.utcnow(),
            last_seen_up=timeutils.utcnow())
        test_service = objects.Service(self.context, **fake_service)
        test_service.create()

        monitor = service_monitor.ApplierMonitor()
        status = monitor.get_service_status(self.context,
                                            test_service.id)

        self.assertEqual(objects.service.ServiceStatus.ACTIVE, status)

    @freezegun.freeze_time("2016-10-18T09:52:05.219414")
    def test_get_service_status_down(self):
        past = timeutils.utcnow() - datetime.timedelta(seconds=120)
        fake_service = utils.get_test_service(
            created_at=past,
            last_seen_up=past)
        test_service = objects.Service(self.context, **fake_service)
        test_service.create()

        monitor = service_monitor.ApplierMonitor()
        status = monitor.get_service_status(self.context,
                                            test_service.id)

        self.assertEqual(objects.service.ServiceStatus.FAILED, status)

    @freezegun.freeze_time("2016-10-18T09:52:05.219414")
    def test_get_service_status_down_last_seen_up_none(self):
        past = timeutils.utcnow() - datetime.timedelta(seconds=120)
        fake_service = utils.get_test_service(
            created_at=past,
            updated_at=past,
            last_seen_up=None)
        test_service = objects.Service(self.context, **fake_service)
        test_service.create()

        monitor = service_monitor.ApplierMonitor()
        status = monitor.get_service_status(self.context,
                                            test_service.id)

        self.assertEqual(objects.service.ServiceStatus.FAILED, status)

    @freezegun.freeze_time("2016-10-18T09:52:05.219414")
    def test_get_service_status_down_updated_at_none(self):
        past = timeutils.utcnow() - datetime.timedelta(seconds=120)
        fake_service = utils.get_test_service(
            created_at=past,
            updated_at=None,
            last_seen_up=None)
        test_service = objects.Service(self.context, **fake_service)
        test_service.create()

        monitor = service_monitor.ApplierMonitor()
        status = monitor.get_service_status(self.context,
                                            test_service.id)

        self.assertEqual(objects.service.ServiceStatus.FAILED, status)

    @freezegun.freeze_time("2016-10-18T09:52:05.219414")
    def test_get_service_status_with_string_last_seen_up(self):
        """Test that string timestamps are properly converted."""
        fake_service = utils.get_test_service(
            created_at=timeutils.utcnow(),
            last_seen_up="2016-10-18T09:52:05.219414")
        test_service = objects.Service(self.context, **fake_service)
        test_service.create()

        monitor = service_monitor.ApplierMonitor()
        status = monitor.get_service_status(self.context,
                                            test_service.id)

        self.assertEqual(objects.service.ServiceStatus.ACTIVE, status)

    def test_services_status_tracking(self):
        """Test that services_status dict properly tracks service states."""
        monitor = service_monitor.ApplierMonitor()

        # Initially empty
        self.assertEqual({}, monitor.services_status)

        # Add a service status
        monitor.services_status[1] = objects.service.ServiceStatus.ACTIVE
        self.assertEqual(
            {1: objects.service.ServiceStatus.ACTIVE},
            monitor.services_status
        )

    @mock.patch.object(service_monitor.ApplierMonitor,
                       'get_service_status')
    @mock.patch.object(objects.Service, 'list')
    def test_get_services_status_without_services_in_list(
            self, mock_get_list, mock_service_status):
        scheduler = service_monitor.ApplierMonitor()
        mock_get_list.return_value = []
        services_status = scheduler.get_services_status(mock.ANY)
        self.assertEqual([], services_status)
        mock_service_status.assert_not_called()

    @mock.patch.object(service_monitor.ApplierMonitor,
                       'get_service_status')
    @mock.patch.object(objects.Service, 'list')
    def test_get_services_status_with_services_in_list(
            self, m_service_list, m_get_service_status):
        """Test that get_services_status returns only the applier services."""
        # Create various services
        de_service1 = utils.get_test_service(
            id=1, name='watcher-applier', host='host1')
        de_service2 = utils.get_test_service(
            id=2, name='watcher-applier', host='host2')
        api_service = utils.get_test_service(
            id=3, name='watcher-api', host='host3')
        applier_service = utils.get_test_service(
            id=4, name='watcher-decision-engine', host='host4')

        m_service_list.return_value = [
            objects.Service(**de_service1),
            objects.Service(**de_service2),
            objects.Service(**api_service),
            objects.Service(**applier_service)
        ]
        m_get_service_status.side_effect = [
            objects.service.ServiceStatus.ACTIVE,
            objects.service.ServiceStatus.FAILED,
            objects.service.ServiceStatus.ACTIVE,
            objects.service.ServiceStatus.ACTIVE
        ]

        monitor = service_monitor.ApplierMonitor()
        result = monitor.get_services_status(self.context)

        # Should return only the applier services
        self.assertEqual(2, len(result))
        for wservice in result:
            match wservice.host:
                case 'host1':
                    self.assertEqual('watcher-applier', wservice.name)
                    self.assertEqual(
                        objects.service.ServiceStatus.ACTIVE, wservice.state)
                case 'host2':
                    self.assertEqual('watcher-applier', wservice.name)
                    self.assertEqual(
                        objects.service.ServiceStatus.FAILED, wservice.state)
                case _:
                    self.fail(f'Unexpected host: {wservice.host}')

    def test_am_i_leader_with_single_active_service(self):
        """Test leader election with single active service."""
        # Create service objects with state attribute
        service1 = objects.Service(
            id=1, name='watcher-applier', host='host1')
        service1.state = objects.service.ServiceStatus.ACTIVE

        monitor = service_monitor.ApplierMonitor()

        # Test when current host is the leader
        self.flags(host='host1')
        result = monitor._am_i_leader([service1])
        self.assertTrue(result)

        # Test when current host is not the leader
        self.flags(host='host2')
        result = monitor._am_i_leader([service1])
        self.assertFalse(result)

    def test_am_i_leader_with_multiple_active_services(self):
        """Test leader election with multiple active services."""
        # Create service objects with state attribute
        # sorted order: host1, host2, host3
        service1 = objects.Service(
            id=1, name='watcher-applier', host='host2')
        service1.state = objects.service.ServiceStatus.ACTIVE
        service2 = objects.Service(
            id=2, name='watcher-applier', host='host1')
        service2.state = objects.service.ServiceStatus.ACTIVE
        service3 = objects.Service(
            id=3, name='watcher-applier', host='host3')
        service3.state = objects.service.ServiceStatus.ACTIVE

        monitor = service_monitor.ApplierMonitor()

        # Leader should be host1 (alphabetically first)
        self.flags(host='host1')
        result = monitor._am_i_leader([service1, service2, service3])
        self.assertTrue(result)

        self.flags(host='host2')
        result = monitor._am_i_leader([service1, service2, service3])
        self.assertFalse(result)

        self.flags(host='host3')
        result = monitor._am_i_leader([service1, service2, service3])
        self.assertFalse(result)

    def test_am_i_leader_with_failed_services(self):
        """Test leader election ignores failed services."""
        # Create service objects with mixed states
        service1 = objects.Service(
            id=1, name='watcher-applier', host='host1')
        service1.state = objects.service.ServiceStatus.FAILED
        service2 = objects.Service(
            id=2, name='watcher-applier', host='host2')
        service2.state = objects.service.ServiceStatus.ACTIVE

        monitor = service_monitor.ApplierMonitor()

        # Leader should be host2 (only active service)
        self.flags(host='host2')
        result = monitor._am_i_leader([service1, service2])
        self.assertTrue(result)

        self.flags(host='host1')
        result = monitor._am_i_leader([service1, service2])
        self.assertFalse(result)

    def test_am_i_leader_with_no_active_services(self):
        """Test leader election when no services are active."""
        # Create service objects with all failed states
        service1 = objects.Service(
            id=1, name='watcher-applier', host='host1')
        service1.state = objects.service.ServiceStatus.FAILED
        service2 = objects.Service(
            id=2, name='watcher-applier', host='host2')
        service2.state = objects.service.ServiceStatus.FAILED

        monitor = service_monitor.ApplierMonitor()

        # Should return False when no services are active
        self.flags(host='host1')
        result = monitor._am_i_leader([service1, service2])
        self.assertFalse(result)
        self.flags(host='host2')
        result = monitor._am_i_leader([service1, service2])
        self.assertFalse(result)

    @mock.patch.object(rpcapi.ApplierAPI, 'launch_action_plan', autospec=True)
    @mock.patch.object(objects.ActionPlan, 'list', autospec=True)
    def test_retrigger_pending_actionplans_none(self, m_ap_list, m_launch):
        """No pending action plans: nothing is launched or saved."""
        m_ap_list.return_value = []
        monitor = service_monitor.ApplierMonitor()

        monitor._retrigger_pending_actionplans(self.context, 'host1')

        m_ap_list.assert_called_once_with(
            self.context,
            filters={
                'state': objects.action_plan.State.PENDING,
                'hostname': 'host1',
            },
            eager=True,
        )
        m_launch.assert_not_called()

    @mock.patch.object(rpcapi.ApplierAPI, 'launch_action_plan', autospec=True)
    @mock.patch.object(objects.ActionPlan, 'list', autospec=True)
    def test_retrigger_pending_actionplans_single(self, m_ap_list, m_launch):
        """Single pending action plan is unassigned and relaunched."""
        ap_uuid = common_utils.generate_uuid()
        ap_dict = utils.get_test_action_plan(
            uuid=ap_uuid,
            state=objects.action_plan.State.PENDING,
            hostname='host1',
        )
        ap = objects.ActionPlan(self.context, **ap_dict)
        # Avoid hitting DB on save
        ap.save = mock.MagicMock()
        m_ap_list.return_value = [ap]

        monitor = service_monitor.ApplierMonitor()

        monitor._retrigger_pending_actionplans(self.context, 'host1')

        m_ap_list.assert_called_once_with(
            self.context,
            filters={
                'state': objects.action_plan.State.PENDING,
                'hostname': 'host1',
            },
            eager=True,
        )
        # hostname should be cleared and object saved
        self.assertIsNone(ap.hostname)
        ap.save.assert_called_once_with()
        m_launch.assert_called_once_with(mock.ANY, self.context, ap_uuid)

    @mock.patch.object(rpcapi.ApplierAPI, 'launch_action_plan', autospec=True)
    @mock.patch.object(objects.ActionPlan, 'list', autospec=True)
    def test_retrigger_pending_actionplans_multiple(self, m_ap_list, m_launch):
        """Multiple pending action plans are all unassigned and relaunched."""
        ap1_uuid = common_utils.generate_uuid()
        ap1_dict = utils.get_test_action_plan(
            uuid=ap1_uuid,
            state=objects.action_plan.State.PENDING,
            hostname='host1',
        )
        ap1 = objects.ActionPlan(self.context, **ap1_dict)
        ap1.save = mock.MagicMock()

        ap2_uuid = common_utils.generate_uuid()
        ap2_dict = utils.get_test_action_plan(
            uuid=ap2_uuid,
            state=objects.action_plan.State.PENDING,
            hostname='host1',
        )
        ap2 = objects.ActionPlan(self.context, **ap2_dict)
        ap2.save = mock.MagicMock()
        m_ap_list.return_value = [ap1, ap2]

        monitor = service_monitor.ApplierMonitor()

        monitor._retrigger_pending_actionplans(self.context, 'host1')

        m_ap_list.assert_called_once_with(
            self.context,
            filters={
                'state': objects.action_plan.State.PENDING,
                'hostname': 'host1',
            },
            eager=True,
        )
        # Both action plans should be reset and saved
        self.assertIsNone(ap1.hostname)
        self.assertIsNone(ap2.hostname)
        ap1.save.assert_called_once_with()
        ap2.save.assert_called_once_with()
        m_launch.assert_has_calls(
            [
                mock.call(mock.ANY, self.context, ap1_uuid),
                mock.call(mock.ANY, self.context, ap2_uuid),
            ],
            any_order=True,
        )
        self.assertEqual(2, m_launch.call_count)
