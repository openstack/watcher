# -*- encoding: utf-8 -*-
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

from apscheduler.schedulers import background
import datetime
import freezegun
from unittest import mock

from watcher.api import scheduling
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
        super(TestSchedulingServiceFunctions, self).setUp()
        fake_service = utils.get_test_service(
            created_at=datetime.datetime.utcnow())
        self.fake_service = objects.Service(**fake_service)

    @mock.patch.object(scheduling.APISchedulingService, 'get_service_status')
    @mock.patch.object(objects.Service, 'list')
    @mock.patch.object(service, 'send_service_update')
    def test_get_services_status_without_services_in_list(
            self, mock_service_update, mock_get_list, mock_service_status):
        scheduler = scheduling.APISchedulingService()
        mock_get_list.return_value = [self.fake_service]
        mock_service_status.return_value = 'ACTIVE'
        scheduler.get_services_status(mock.ANY)
        mock_service_status.assert_called_once_with(mock.ANY,
                                                    self.fake_service.id)

        mock_service_update.assert_not_called()

    @mock.patch.object(scheduling.APISchedulingService, 'get_service_status')
    @mock.patch.object(objects.Service, 'list')
    @mock.patch.object(service, 'send_service_update')
    def test_get_services_status_with_services_in_list_same_status(
            self, mock_service_update, mock_get_list, mock_service_status):
        scheduler = scheduling.APISchedulingService()
        mock_get_list.return_value = [self.fake_service]
        scheduler.services_status = {1: 'ACTIVE'}
        mock_service_status.return_value = 'ACTIVE'
        scheduler.get_services_status(mock.ANY)
        mock_service_status.assert_called_once_with(mock.ANY,
                                                    self.fake_service.id)

        mock_service_update.assert_not_called()

    @mock.patch.object(scheduling.APISchedulingService, 'get_service_status')
    @mock.patch.object(objects.Service, 'list')
    @mock.patch.object(service, 'send_service_update')
    def test_get_services_status_with_services_in_list_diff_status(
            self, mock_service_update, mock_get_list, mock_service_status):
        scheduler = scheduling.APISchedulingService()
        mock_get_list.return_value = [self.fake_service]
        scheduler.services_status = {1: 'FAILED'}
        mock_service_status.return_value = 'ACTIVE'
        scheduler.get_services_status(mock.ANY)
        mock_service_status.assert_called_once_with(mock.ANY,
                                                    self.fake_service.id)

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
