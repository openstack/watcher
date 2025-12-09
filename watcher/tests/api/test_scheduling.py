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

from unittest import mock

from apscheduler.schedulers import background
import freezegun
from oslo_utils import timeutils

from watcher.api import scheduling
from watcher.common import utils as common_utils
from watcher.notifications import service
from watcher import objects
from watcher.tests import base
from watcher.tests.db import base as db_base
from watcher.tests.db import utils


class TestSchedulingService(base.TestCase):

    @mock.patch.object(background.BackgroundScheduler, 'start')
    def test_start_scheduling_service(self, m_start):
        scheduler = scheduling.APISchedulingService()
        scheduler.start()
        m_start.assert_called_once_with(scheduler)
        jobs = scheduler.get_jobs()
        self.assertEqual(1, len(jobs))


class TestSchedulingServiceFunctions(db_base.DbTestCase):

    def setUp(self):
        super().setUp()
        fake_service = utils.get_test_service(
            created_at=timeutils.utcnow())
        self.fake_service = objects.Service(**fake_service)

    @mock.patch.object(scheduling.APISchedulingService, 'get_services_status')
    @mock.patch.object(service, 'send_service_update')
    def test_monitor_services_with_services_in_list_same_status(
            self, mock_service_update, mock_services_status):
        scheduler = scheduling.APISchedulingService()
        scheduler.services_status = {1: 'ACTIVE'}
        self.fake_service.state = 'ACTIVE'
        mock_services_status.return_value = [self.fake_service]
        scheduler.monitor_services_status(mock.ANY)
        mock_services_status.assert_called_once_with(mock.ANY)
        mock_service_update.assert_not_called()

    @mock.patch.object(scheduling.APISchedulingService, 'get_services_status')
    @mock.patch.object(objects.Service, 'list')
    @mock.patch.object(service, 'send_service_update')
    def test_monitor_services_with_services_in_list_diff_status(
            self, mock_service_update, mock_get_list, mock_services_status):
        scheduler = scheduling.APISchedulingService()
        mock_get_list.return_value = [self.fake_service]
        scheduler.services_status = {1: 'FAILED'}
        self.fake_service.state = 'ACTIVE'
        mock_services_status.return_value = [self.fake_service]

        scheduler.monitor_services_status(mock.ANY)
        mock_services_status.assert_called_once_with(mock.ANY)

        mock_service_update.assert_called_once_with(mock.ANY,
                                                    self.fake_service,
                                                    state='ACTIVE')

    @mock.patch.object(objects.Service, 'get')
    def test_get_service_status_failed_service(
            self, mock_get):
        scheduler = scheduling.APISchedulingService()
        mock_get.return_value = self.fake_service
        service_status = scheduler.get_service_status(mock.ANY,
                                                      self.fake_service.id)
        mock_get.assert_called_once_with(mock.ANY,
                                         self.fake_service.id)
        self.assertEqual('FAILED', service_status)

    @freezegun.freeze_time('2016-09-22T08:32:26.219414')
    @mock.patch.object(objects.Service, 'get')
    def test_get_service_status_failed_active(
            self, mock_get):
        scheduler = scheduling.APISchedulingService()
        mock_get.return_value = self.fake_service
        service_status = scheduler.get_service_status(mock.ANY,
                                                      self.fake_service.id)
        mock_get.assert_called_once_with(mock.ANY,
                                         self.fake_service.id)
        self.assertEqual('ACTIVE', service_status)

    @mock.patch.object(scheduling.APISchedulingService, 'get_service_status')
    @mock.patch.object(objects.Service, 'list')
    @mock.patch.object(service, 'send_service_update')
    def test_get_services_status_without_services_in_list(
            self, mock_service_update, mock_get_list, mock_service_status):
        scheduler = scheduling.APISchedulingService()
        mock_get_list.return_value = []
        services_status = scheduler.get_services_status(mock.ANY)
        self.assertEqual([], services_status)
        mock_service_status.assert_not_called()

    @mock.patch.object(scheduling.APISchedulingService, 'get_service_status')
    @mock.patch.object(objects.Service, 'list')
    def test_get_services_status_with_services_in_list(
            self, m_service_list, m_get_service_status):
        """Test that get_services_status returns only decision-engines."""
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

        scheduler = scheduling.APISchedulingService()
        result = scheduler.get_services_status(self.context)

        # Verify the calls to get_service_status
        m_get_service_status.assert_has_calls([
            mock.call(self.context, 1),
            mock.call(self.context, 2),
            mock.call(self.context, 3),
            mock.call(self.context, 4)
        ])

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
        scheduler = scheduling.APISchedulingService()
        # Prepare three ongoing audits with the same failed host
        uuid_prefix = common_utils.generate_uuid()[:-1]
        audits = [
            objects.Audit(context=self.context,
                          uuid=f'{uuid_prefix}{i}',
                          hostname='failed-host')
            for i in range(3)
        ]

        alive_services = ['hostA', 'hostB']

        with mock.patch.object(scheduling, 'LOG') as m_log:
            with mock.patch.object(objects.Audit, 'save') as m_save:
                scheduler._migrate_audits_to_new_host(audits, alive_services)

        # Round-robin expected: hostA, hostB, hostA
        self.assertEqual('hostA', audits[0].hostname)
        self.assertEqual('hostB', audits[1].hostname)
        self.assertEqual('hostA', audits[2].hostname)

        # Each audit must be saved once
        self.assertEqual(3, m_save.call_count)

        # A log must be emitted per audit
        self.assertEqual(3, m_log.info.call_count)

    def test_migrate_audits_logs_expected_payload(self):
        scheduler = scheduling.APISchedulingService()
        # Prepare audits with distinct failed hosts to validate payload
        uuid_prefix = common_utils.generate_uuid()[:-1]
        audits = [
            objects.Audit(context=self.context,
                          uuid=f'{uuid_prefix}{i}',
                          hostname=f'failed-{i}')
            for i in range(2)
        ]

        alive_services = ['host1', 'host2']

        with mock.patch.object(scheduling, 'LOG') as m_log:
            with mock.patch.object(objects.Audit, 'save') as m_save:
                scheduler._migrate_audits_to_new_host(audits, alive_services)

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
