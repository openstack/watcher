# Copyright 2015 OpenStack Foundation
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

import datetime
from unittest import mock

from oslo_utils import timeutils

from watcher.db.sqlalchemy import api as db_api
from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils


class TestServiceObject(base.DbTestCase):

    def setUp(self):
        super(TestServiceObject, self).setUp()
        self.fake_service = utils.get_test_service(
            created_at=timeutils.utcnow())

    @mock.patch.object(db_api.Connection, 'get_service_by_id')
    def test_get_by_id(self, mock_get_service):
        service_id = self.fake_service['id']
        mock_get_service.return_value = self.fake_service
        service = objects.Service.get(self.context, service_id)
        mock_get_service.assert_called_once_with(self.context, service_id)
        self.assertEqual(self.context, service._context)

    @mock.patch.object(db_api.Connection, 'get_service_list')
    def test_list(self, mock_get_list):
        mock_get_list.return_value = [self.fake_service]
        services = objects.Service.list(self.context)
        self.assertEqual(1, mock_get_list.call_count, 1)
        self.assertEqual(1, len(services))
        self.assertIsInstance(services[0], objects.Service)
        self.assertEqual(self.context, services[0]._context)

    @mock.patch.object(db_api.Connection, 'create_service')
    def test_create(self, mock_create_service):
        mock_create_service.return_value = self.fake_service
        service = objects.Service(self.context, **self.fake_service)

        service.create()
        expected_service = self.fake_service.copy()
        expected_service['created_at'] = expected_service[
            'created_at'].replace(tzinfo=datetime.timezone.utc)

        mock_create_service.assert_called_once_with(expected_service)
        self.assertEqual(self.context, service._context)

    @mock.patch.object(db_api.Connection, 'update_service')
    @mock.patch.object(db_api.Connection, 'get_service_by_id')
    def test_save(self, mock_get_service, mock_update_service):
        mock_get_service.return_value = self.fake_service
        fake_saved_service = self.fake_service.copy()
        fake_saved_service['updated_at'] = timeutils.utcnow()
        mock_update_service.return_value = fake_saved_service
        _id = self.fake_service['id']
        service = objects.Service.get(self.context, _id)
        service.name = 'UPDATED NAME'
        service.save()

        mock_get_service.assert_called_once_with(self.context, _id)
        mock_update_service.assert_called_once_with(
            _id, {'name': 'UPDATED NAME'})
        self.assertEqual(self.context, service._context)

    @mock.patch.object(db_api.Connection, 'get_service_by_id')
    def test_refresh(self, mock_get_service):
        returns = [dict(self.fake_service, name="first name"),
                   dict(self.fake_service, name="second name")]
        mock_get_service.side_effect = returns
        _id = self.fake_service['id']
        expected = [mock.call(self.context, _id),
                    mock.call(self.context, _id)]
        service = objects.Service.get(self.context, _id)
        self.assertEqual("first name", service.name)
        service.refresh()
        self.assertEqual("second name", service.name)
        self.assertEqual(expected, mock_get_service.call_args_list)
        self.assertEqual(self.context, service._context)

    @mock.patch.object(db_api.Connection, 'soft_delete_service')
    @mock.patch.object(db_api.Connection, 'get_service_by_id')
    def test_soft_delete(self, mock_get_service, mock_soft_delete):
        mock_get_service.return_value = self.fake_service
        fake_deleted_service = self.fake_service.copy()
        fake_deleted_service['deleted_at'] = timeutils.utcnow()
        mock_soft_delete.return_value = fake_deleted_service

        expected_service = fake_deleted_service.copy()
        expected_service['created_at'] = expected_service[
            'created_at'].replace(tzinfo=datetime.timezone.utc)
        expected_service['deleted_at'] = expected_service[
            'deleted_at'].replace(tzinfo=datetime.timezone.utc)

        _id = self.fake_service['id']
        service = objects.Service.get(self.context, _id)
        service.soft_delete()
        mock_get_service.assert_called_once_with(self.context, _id)
        mock_soft_delete.assert_called_once_with(_id)
        self.assertEqual(self.context, service._context)
        self.assertEqual(expected_service, service.as_dict())
