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

from watcher.common import utils as common_utils
from watcher.decision_engine import service_monitor
from watcher.notifications import service
from watcher import objects
from watcher.tests import base
from watcher.tests.db import base as db_base
from watcher.tests.db import utils


class TestServiceMonitoringService(base.TestCase):

    @mock.patch.object(background.BackgroundScheduler, 'start')
    def test_start_service_monitoring_service(self, m_start):
        scheduler = service_monitor.ServiceMonitoringService()
        scheduler.start()
        m_start.assert_called_once_with(scheduler)
        jobs = scheduler.get_jobs()
        self.assertEqual(1, len(jobs))

    @mock.patch.object(background.BackgroundScheduler, 'shutdown')
    def test_stop_service_monitoring_service(self, m_shutdown):
        scheduler = service_monitor.ServiceMonitoringService()
        scheduler.stop()
        m_shutdown.assert_called_once_with()

    def test_wait_service_monitoring_service(self):
        scheduler = service_monitor.ServiceMonitoringService()
        # Should not raise any exception
        scheduler.wait()

    def test_reset_service_monitoring_service(self):
        scheduler = service_monitor.ServiceMonitoringService()
        # Should not raise any exception
        scheduler.reset()


class TestServiceMonitoringServiceFunctions(db_base.DbTestCase):

    def setUp(self):
        super().setUp()
        fake_service = utils.get_test_service(
            created_at=timeutils.utcnow())
        self.fake_service = objects.Service(**fake_service)

    @mock.patch.object(service_monitor.ServiceMonitoringService,
                       'get_service_status')
    @mock.patch.object(objects.Service, 'list')
    @mock.patch.object(service, 'send_service_update')
    @mock.patch.object(objects.Audit, 'list')
    def test_monitor_not_send_notification_on_active(self, m_audit_list,
                                                     m_send_notif,
                                                     m_service_list,
                                                     m_get_service_status):
        # Create two decision-engine services
        fake_de_service1 = utils.get_test_service(
            id=1, name='watcher-decision-engine', host='host1')
        fake_de_service2 = utils.get_test_service(
            id=2, name='watcher-decision-engine', host='host2')
        fake_de_service_obj1 = objects.Service(**fake_de_service1)
        fake_de_service_obj2 = objects.Service(**fake_de_service2)

        m_service_list.return_value = [
            fake_de_service_obj1, fake_de_service_obj2]

        # First call: both ACTIVE in first and second call
        m_get_service_status.side_effect = [
            objects.service.ServiceStatus.ACTIVE,  # service1 first call
            objects.service.ServiceStatus.ACTIVE,  # service2 first call
            objects.service.ServiceStatus.ACTIVE,  # service1 second call
            objects.service.ServiceStatus.ACTIVE   # service2 second call
        ]

        monitor = service_monitor.ServiceMonitoringService()

        # Mock CONF.host to make this service the leader
        with mock.patch.object(service_monitor.CONF, 'host', 'host2'):
            # First call: both ACTIVE
            monitor.monitor_services_status(self.context)
            self.assertEqual(monitor.services_status, {
                fake_de_service_obj1.id: objects.service.ServiceStatus.ACTIVE,
                fake_de_service_obj2.id: objects.service.ServiceStatus.ACTIVE
            })
            # Second call: both ACTIVE
            monitor.monitor_services_status(self.context)
            self.assertEqual(monitor.services_status, {
                fake_de_service_obj1.id: objects.service.ServiceStatus.ACTIVE,
                fake_de_service_obj2.id: objects.service.ServiceStatus.ACTIVE
            })

        m_send_notif.assert_not_called()
        m_audit_list.assert_not_called()

    @mock.patch.object(service_monitor.ServiceMonitoringService,
                       'get_service_status')
    @mock.patch.object(objects.Service, 'list')
    @mock.patch.object(service, 'send_service_update')
    def test_monitor_send_notification_on_failure(self, m_send_notif,
                                                  m_service_list,
                                                  m_get_service_status):
        # Create two decision-engine services
        fake_de_service1 = utils.get_test_service(
            id=1, name='watcher-decision-engine', host='host1')
        fake_de_service2 = utils.get_test_service(
            id=2, name='watcher-decision-engine', host='host2')
        fake_de_service_obj1 = objects.Service(**fake_de_service1)
        fake_de_service_obj2 = objects.Service(**fake_de_service2)

        m_service_list.return_value = [
            fake_de_service_obj1, fake_de_service_obj2]

        # First call: both ACTIVE
        # Second call: service1 FAILED, service2 ACTIVE
        m_get_service_status.side_effect = [
            objects.service.ServiceStatus.ACTIVE,  # service1 first call
            objects.service.ServiceStatus.ACTIVE,  # service2 first call
            objects.service.ServiceStatus.FAILED,  # service1 second call
            objects.service.ServiceStatus.ACTIVE   # service2 second call
        ]

        monitor = service_monitor.ServiceMonitoringService()

        # Mock CONF.host to make this service the alive and leader one
        # after service1 is marked as failed.
        with mock.patch.object(service_monitor.CONF, 'host', 'host2'):
            # First call: both ACTIVE
            monitor.monitor_services_status(self.context)
            self.assertEqual(monitor.services_status, {
                fake_de_service_obj1.id: objects.service.ServiceStatus.ACTIVE,
                fake_de_service_obj2.id: objects.service.ServiceStatus.ACTIVE
            })
            # Second call: service1 FAILED, service2 ACTIVE
            monitor.monitor_services_status(self.context)
            self.assertEqual(monitor.services_status, {
                fake_de_service_obj1.id: objects.service.ServiceStatus.FAILED,
                fake_de_service_obj2.id: objects.service.ServiceStatus.ACTIVE
            })

        m_send_notif.assert_called_once_with(
            self.context, fake_de_service_obj1,
            state=objects.service.ServiceStatus.FAILED)

    @mock.patch.object(service_monitor.ServiceMonitoringService,
                       'get_service_status')
    @mock.patch.object(objects.Service, 'list')
    @mock.patch.object(objects.Audit, 'list')
    @mock.patch.object(service, 'send_service_update')
    def test_monitor_migrate_audits_when_decision_engine_fails(
            self, m_send_notif, m_audit_list, m_service_list,
            m_get_service_status):

        # Create test services
        failed_de_service = utils.get_test_service(
            id=1, name='watcher-decision-engine', host='host1')
        active_de_service = utils.get_test_service(
            id=2, name='watcher-decision-engine', host='host2')

        m_service_list.return_value = [
            objects.Service(**failed_de_service),
            objects.Service(**active_de_service)
        ]

        # First call: both ACTIVE
        # Second call: service1 FAILED, service2 ACTIVE
        m_get_service_status.side_effect = [
            objects.service.ServiceStatus.ACTIVE,  # service1 first call
            objects.service.ServiceStatus.ACTIVE,  # service2 first call
            objects.service.ServiceStatus.FAILED,  # service1 second call
            objects.service.ServiceStatus.ACTIVE   # service2 second call
        ]

        # Create test continuous audit on the failed host
        fake_audit = utils.get_test_audit(
            id=1,
            audit_type=objects.audit.AuditType.CONTINUOUS.value,
            state=objects.audit.State.ONGOING,
            hostname='host1'
        )
        audit_obj = objects.Audit(self.context, **fake_audit)
        m_audit_list.return_value = [audit_obj]

        monitor = service_monitor.ServiceMonitoringService()

        # Mock CONF.host to make this service the leader
        with mock.patch.object(service_monitor.CONF, 'host', 'host2'):
            # First call: both ACTIVE
            monitor.monitor_services_status(self.context)
            self.assertEqual(monitor.services_status, {
                failed_de_service['id']: objects.service.ServiceStatus.ACTIVE,
                active_de_service['id']: objects.service.ServiceStatus.ACTIVE
            })
            # Mock the audit.save() method
            with mock.patch.object(audit_obj, 'save') as m_save:
                # Second call: service1 FAILED, service2 ACTIVE
                monitor.monitor_services_status(self.context)

            self.assertEqual(monitor.services_status, {
                failed_de_service['id']: objects.service.ServiceStatus.FAILED,
                active_de_service['id']: objects.service.ServiceStatus.ACTIVE
            })

        # Verify audit was migrated to the active SERVICE
        m_save.assert_called_once_with()
        self.assertEqual(active_de_service['host'], audit_obj.hostname)

    @mock.patch.object(service_monitor.ServiceMonitoringService,
                       'get_service_status')
    @mock.patch.object(objects.Service, 'list')
    @mock.patch.object(objects.Audit, 'list')
    @mock.patch.object(service, 'send_service_update')
    def test_monitor_no_migration_when_no_active_services(
            self, m_send_notif, m_audit_list, m_service_list,
            m_get_service_status):

        # Create test service that fails
        failed_de_service = utils.get_test_service(
            id=1, name='watcher-decision-engine', host='host1')

        m_service_list.return_value = [objects.Service(**failed_de_service)]

        # First call returns ACTIVE, second call returns FAILED
        m_get_service_status.side_effect = [
            objects.service.ServiceStatus.ACTIVE,
            objects.service.ServiceStatus.FAILED
        ]

        # Create test continuous audit
        fake_audit = utils.get_test_audit(
            id=1,
            audit_type=objects.audit.AuditType.CONTINUOUS.value,
            state=objects.audit.State.ONGOING,
            hostname='host1'
        )
        audit_obj = objects.Audit(self.context, **fake_audit)
        m_audit_list.return_value = [audit_obj]

        monitor = service_monitor.ServiceMonitoringService()

        # Mock CONF.host to make this service the leader
        with mock.patch.object(service_monitor.CONF, 'host', 'host1'):
            # First call: both ACTIVE
            monitor.monitor_services_status(self.context)

            # Mock the audit.save() method
            with mock.patch.object(audit_obj, 'save') as m_save:
                # Second call should detect the failure but
                # not migrate (no active services)
                monitor.monitor_services_status(self.context)
                # Verify audit was not migrated (no active services available)
                m_save.assert_not_called()
                self.assertEqual('host1', audit_obj.hostname)

    @mock.patch.object(service_monitor.ServiceMonitoringService,
                       'get_service_status')
    @mock.patch.object(objects.Service, 'list')
    @mock.patch.object(service, 'send_service_update')
    @mock.patch.object(objects.Audit, 'list')
    def test_nonleader_not_send_notification_on_failure(self, m_audit_list,
                                                        m_send_notif,
                                                        m_service_list,
                                                        m_get_service_status):
        # Create three decision-engine services
        fake_de_service1 = utils.get_test_service(
            id=1, name='watcher-decision-engine', host='host1')
        fake_de_service2 = utils.get_test_service(
            id=2, name='watcher-decision-engine', host='host2')
        fake_de_service3 = utils.get_test_service(
            id=3, name='watcher-decision-engine', host='host3')

        fake_de_service_obj1 = objects.Service(**fake_de_service1)
        fake_de_service_obj2 = objects.Service(**fake_de_service2)
        fake_de_service_obj3 = objects.Service(**fake_de_service3)

        m_service_list.return_value = [
            fake_de_service_obj1, fake_de_service_obj2, fake_de_service_obj3]

        # First call: all ACTIVE
        # Second call: service1 FAILED, service2 ACTIVE, service3 ACTIVE
        m_get_service_status.side_effect = [
            objects.service.ServiceStatus.ACTIVE,  # service1 first call
            objects.service.ServiceStatus.ACTIVE,  # service2 first call
            objects.service.ServiceStatus.ACTIVE,  # service3 first call
            objects.service.ServiceStatus.FAILED,  # service1 second call
            objects.service.ServiceStatus.ACTIVE,   # service2 second call
            objects.service.ServiceStatus.ACTIVE   # service3 second call
        ]

        monitor = service_monitor.ServiceMonitoringService()

        # Mock CONF.host to make this service non-leader (host2 is the
        # leader after service1 is failed)
        with mock.patch.object(service_monitor.CONF, 'host', 'host3'):
            # First call: all ACTIVE
            monitor.monitor_services_status(self.context)
            # Second call: service1 FAILED, service2 and 3 still ACTIVE
            monitor.monitor_services_status(self.context)

        m_send_notif.assert_not_called()
        m_audit_list.assert_not_called()

    @mock.patch.object(service_monitor.ServiceMonitoringService,
                       'get_service_status')
    @mock.patch.object(objects.Service, 'list')
    @mock.patch.object(objects.Audit, 'list')
    @mock.patch.object(service, 'send_service_update')
    def test_nonleader_monitor_not_migrate_audits_when_decision_engine_fails(
            self, m_send_notif, m_audit_list, m_service_list,
            m_get_service_status):

        # Create test services
        failed_de_service = utils.get_test_service(
            id=1, name='watcher-decision-engine', host='host1')
        active_de_service2 = utils.get_test_service(
            id=2, name='watcher-decision-engine', host='host2')
        active_de_service3 = utils.get_test_service(
            id=3, name='watcher-decision-engine', host='host3')

        m_service_list.return_value = [
            objects.Service(**failed_de_service),
            objects.Service(**active_de_service2),
            objects.Service(**active_de_service3)
        ]

        # First call: all ACTIVE
        # Second call: service1 FAILED, service2 ACTIVE, service3 ACTIVE
        m_get_service_status.side_effect = [
            objects.service.ServiceStatus.ACTIVE,  # service1 first call
            objects.service.ServiceStatus.ACTIVE,  # service2 first call
            objects.service.ServiceStatus.ACTIVE,  # service3 first call
            objects.service.ServiceStatus.FAILED,  # service1 second call
            objects.service.ServiceStatus.ACTIVE,  # service2 second call
            objects.service.ServiceStatus.ACTIVE   # service3 second call
        ]

        # Create test continuous audit on the failed host
        fake_audit = utils.get_test_audit(
            id=1,
            audit_type=objects.audit.AuditType.CONTINUOUS.value,
            state=objects.audit.State.ONGOING,
            hostname='host1'
        )
        audit_obj = objects.Audit(self.context, **fake_audit)
        m_audit_list.return_value = [audit_obj]

        monitor = service_monitor.ServiceMonitoringService()

        # Mock CONF.host to make this service non-leader (host2 is the
        # leader after service1 is failed)
        with mock.patch.object(service_monitor.CONF, 'host', 'host3'):
            # First call: all ACTIVE
            monitor.monitor_services_status(self.context)
            # Mock the audit.save() method
            with mock.patch.object(audit_obj, 'save') as m_save:
                # Second call: service1 FAILED, service2 and service3 ACTIVE
                monitor.monitor_services_status(self.context)
                # Verify audit 1 was migrated to the active host
        m_save.assert_not_called()
        self.assertEqual('host1', audit_obj.hostname)

    @freezegun.freeze_time("2016-10-18T09:52:05.219414")
    def test_get_service_status_up(self):
        fake_service = utils.get_test_service(
            created_at=timeutils.utcnow(),
            last_seen_up=timeutils.utcnow())
        test_service = objects.Service(self.context, **fake_service)
        test_service.create()

        monitor = service_monitor.ServiceMonitoringService()
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

        monitor = service_monitor.ServiceMonitoringService()
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

        monitor = service_monitor.ServiceMonitoringService()
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

        monitor = service_monitor.ServiceMonitoringService()
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

        monitor = service_monitor.ServiceMonitoringService()
        status = monitor.get_service_status(self.context,
                                            test_service.id)

        self.assertEqual(objects.service.ServiceStatus.ACTIVE, status)

    def test_services_status_tracking(self):
        """Test that services_status dict properly tracks service states."""
        monitor = service_monitor.ServiceMonitoringService()

        # Initially empty
        self.assertEqual({}, monitor.services_status)

        # Add a service status
        monitor.services_status[1] = objects.service.ServiceStatus.ACTIVE
        self.assertEqual(
            {1: objects.service.ServiceStatus.ACTIVE},
            monitor.services_status
        )

    @mock.patch.object(service_monitor.ServiceMonitoringService,
                       'get_service_status')
    @mock.patch.object(objects.Service, 'list')
    def test_get_services_status_without_services_in_list(
            self, mock_get_list, mock_service_status):
        scheduler = service_monitor.ServiceMonitoringService()
        mock_get_list.return_value = []
        services_status = scheduler.get_services_status(mock.ANY)
        self.assertEqual([], services_status)
        mock_service_status.assert_not_called()

    @mock.patch.object(service_monitor.ServiceMonitoringService,
                       'get_service_status')
    @mock.patch.object(objects.Service, 'list')
    def test_get_services_status_with_services_in_list(
            self, m_service_list, m_get_service_status):
        """Test that get_services_status returns all the services."""
        # Create various services
        de_service1 = utils.get_test_service(
            id=1, name='watcher-decision-engine', host='host1')
        de_service2 = utils.get_test_service(
            id=2, name='watcher-decision-engine', host='host2')
        api_service = utils.get_test_service(
            id=3, name='watcher-api', host='host3')
        applier_service = utils.get_test_service(
            id=4, name='watcher-applier', host='host4')

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

        monitor = service_monitor.ServiceMonitoringService()
        result = monitor.get_services_status(self.context)

        # Should return all services
        self.assertEqual(4, len(result))
        for wservice in result:
            match wservice.host:
                case 'host1':
                    self.assertEqual('watcher-decision-engine', wservice.name)
                    self.assertEqual(
                        objects.service.ServiceStatus.ACTIVE, wservice.state)
                case 'host2':
                    self.assertEqual('watcher-decision-engine', wservice.name)
                    self.assertEqual(
                        objects.service.ServiceStatus.FAILED, wservice.state)
                case 'host3':
                    self.assertEqual('watcher-api', wservice.name)
                    self.assertEqual(
                        objects.service.ServiceStatus.ACTIVE, wservice.state)
                case 'host4':
                    self.assertEqual('watcher-applier', wservice.name)
                    self.assertEqual(
                        objects.service.ServiceStatus.ACTIVE, wservice.state)
                case _:
                    self.fail(f'Unexpected host: {wservice.host}')

    def test_migrate_audits_round_robin_assigns_hosts_and_saves(self):
        monitor = service_monitor.ServiceMonitoringService()
        # Prepare three ongoing audits with the same failed host
        uuid_prefix = common_utils.generate_uuid()[:-1]
        audits = [
            objects.Audit(context=self.context,
                          uuid=f'{uuid_prefix}{i}',
                          hostname='failed-host')
            for i in range(3)
        ]

        alive_services = ['hostA', 'hostB']

        with mock.patch.object(service_monitor, 'LOG') as m_log:
            with mock.patch.object(objects.Audit, 'save') as m_save:
                monitor._migrate_audits_to_new_host(audits, alive_services)

        # Round-robin expected: hostA, hostB, hostA
        self.assertEqual('hostA', audits[0].hostname)
        self.assertEqual('hostB', audits[1].hostname)
        self.assertEqual('hostA', audits[2].hostname)

        # Each audit must be saved once
        self.assertEqual(3, m_save.call_count)

        # A log must be emitted per audit
        self.assertEqual(3, m_log.info.call_count)

    def test_migrate_audits_logs_expected_payload(self):
        monitor = service_monitor.ServiceMonitoringService()
        # Prepare audits with distinct failed hosts to validate payload
        uuid_prefix = common_utils.generate_uuid()[:-1]
        audits = [
            objects.Audit(context=self.context,
                          uuid=f'{uuid_prefix}{i}',
                          hostname=f'failed-{i}')
            for i in range(2)
        ]

        alive_services = ['host1', 'host2']

        with mock.patch.object(service_monitor, 'LOG') as m_log:
            with mock.patch.object(objects.Audit, 'save') as m_save:
                monitor._migrate_audits_to_new_host(audits, alive_services)

        # Each audit must be saved once
        self.assertEqual(2, m_save.call_count)

        # Validate payloads of log calls
        calls = m_log.info.call_args_list
        self.assertEqual(2, len(calls))

        # First audit migrated to host1
        args0, _ = calls[0]
        payload0 = args0[1]
        self.assertEqual(f'{uuid_prefix}0', payload0['audit'])
        self.assertEqual('host1', payload0['host'])
        self.assertEqual('failed-0', payload0['failed_host'])
        self.assertEqual(objects.service.ServiceStatus.FAILED,
                         payload0['state'])

        # Second audit migrated to host2
        args1, _ = calls[1]
        payload1 = args1[1]
        self.assertEqual(f'{uuid_prefix}1', payload1['audit'])
        self.assertEqual('host2', payload1['host'])
        self.assertEqual('failed-1', payload1['failed_host'])
        self.assertEqual(objects.service.ServiceStatus.FAILED,
                         payload1['state'])

    def test_am_i_leader_with_single_active_service(self):
        """Test leader election with single active service."""
        # Create service objects with state attribute
        service1 = objects.Service(
            id=1, name='watcher-decision-engine', host='host1')
        service1.state = objects.service.ServiceStatus.ACTIVE

        monitor = service_monitor.ServiceMonitoringService()

        # Test when current host is the leader
        with mock.patch.object(service_monitor.CONF, 'host', 'host1'):
            result = monitor._am_i_leader([service1])
            self.assertTrue(result)

        # Test when current host is not the leader
        with mock.patch.object(service_monitor.CONF, 'host', 'host2'):
            result = monitor._am_i_leader([service1])
            self.assertFalse(result)

    def test_am_i_leader_with_multiple_active_services(self):
        """Test leader election with multiple active services."""
        # Create service objects with state attribute
        # sorted order: host1, host2, host3
        service1 = objects.Service(
            id=1, name='watcher-decision-engine', host='host2')
        service1.state = objects.service.ServiceStatus.ACTIVE
        service2 = objects.Service(
            id=2, name='watcher-decision-engine', host='host1')
        service2.state = objects.service.ServiceStatus.ACTIVE
        service3 = objects.Service(
            id=3, name='watcher-decision-engine', host='host3')
        service3.state = objects.service.ServiceStatus.ACTIVE

        monitor = service_monitor.ServiceMonitoringService()

        # Leader should be host1 (alphabetically first)
        with mock.patch.object(service_monitor.CONF, 'host', 'host1'):
            result = monitor._am_i_leader([service1, service2, service3])
            self.assertTrue(result)

        with mock.patch.object(service_monitor.CONF, 'host', 'host2'):
            result = monitor._am_i_leader([service1, service2, service3])
            self.assertFalse(result)

        with mock.patch.object(service_monitor.CONF, 'host', 'host3'):
            result = monitor._am_i_leader([service1, service2, service3])
            self.assertFalse(result)

    def test_am_i_leader_with_failed_services(self):
        """Test leader election ignores failed services."""
        # Create service objects with mixed states
        service1 = objects.Service(
            id=1, name='watcher-decision-engine', host='host1')
        service1.state = objects.service.ServiceStatus.FAILED
        service2 = objects.Service(
            id=2, name='watcher-decision-engine', host='host2')
        service2.state = objects.service.ServiceStatus.ACTIVE

        monitor = service_monitor.ServiceMonitoringService()

        # Leader should be host2 (only active service)
        with mock.patch.object(service_monitor.CONF, 'host', 'host2'):
            result = monitor._am_i_leader([service1, service2])
            self.assertTrue(result)

        with mock.patch.object(service_monitor.CONF, 'host', 'host1'):
            result = monitor._am_i_leader([service1, service2])
            self.assertFalse(result)

    def test_am_i_leader_with_no_active_services(self):
        """Test leader election when no services are active."""
        # Create service objects with all failed states
        service1 = objects.Service(
            id=1, name='watcher-decision-engine', host='host1')
        service1.state = objects.service.ServiceStatus.FAILED
        service2 = objects.Service(
            id=2, name='watcher-decision-engine', host='host2')
        service2.state = objects.service.ServiceStatus.FAILED

        monitor = service_monitor.ServiceMonitoringService()

        # Should return False when no services are active
        with mock.patch.object(service_monitor.CONF, 'host', 'host1'):
            result = monitor._am_i_leader([service1, service2])
            self.assertFalse(result)
