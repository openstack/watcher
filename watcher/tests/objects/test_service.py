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

import mock

from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils


class TestServiceObject(base.DbTestCase):

    def setUp(self):
        super(TestServiceObject, self).setUp()
        self.fake_service = utils.get_test_service()

    def test_get_by_id(self):
        service_id = self.fake_service['id']
        with mock.patch.object(self.dbapi, 'get_service_by_id',
                               autospec=True) as mock_get_service:
            mock_get_service.return_value = self.fake_service
            service = objects.Service.get(self.context, service_id)
            mock_get_service.assert_called_once_with(self.context,
                                                     service_id)
            self.assertEqual(self.context, service._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'get_service_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_service]
            services = objects.Service.list(self.context)
            self.assertEqual(1, mock_get_list.call_count, 1)
            self.assertEqual(1, len(services))
            self.assertIsInstance(services[0], objects.Service)
            self.assertEqual(self.context, services[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_service',
                               autospec=True) as mock_create_service:
            mock_create_service.return_value = self.fake_service
            service = objects.Service(self.context, **self.fake_service)

            fake_service = utils.get_test_service()

            service.create()
            mock_create_service.assert_called_once_with(fake_service)
            self.assertEqual(self.context, service._context)

    def test_save(self):
        _id = self.fake_service['id']
        with mock.patch.object(self.dbapi, 'get_service_by_id',
                               autospec=True) as mock_get_service:
            mock_get_service.return_value = self.fake_service
            with mock.patch.object(self.dbapi, 'update_service',
                                   autospec=True) as mock_update_service:
                service = objects.Service.get(self.context, _id)
                service.name = 'UPDATED NAME'
                service.save()

                mock_get_service.assert_called_once_with(self.context, _id)
                mock_update_service.assert_called_once_with(
                    _id, {'name': 'UPDATED NAME'})
                self.assertEqual(self.context, service._context)

    def test_refresh(self):
        _id = self.fake_service['id']
        returns = [dict(self.fake_service, name="first name"),
                   dict(self.fake_service, name="second name")]
        expected = [mock.call(self.context, _id),
                    mock.call(self.context, _id)]
        with mock.patch.object(self.dbapi, 'get_service_by_id',
                               side_effect=returns,
                               autospec=True) as mock_get_service:
            service = objects.Service.get(self.context, _id)
            self.assertEqual("first name", service.name)
            service.refresh()
            self.assertEqual("second name", service.name)
            self.assertEqual(expected, mock_get_service.call_args_list)
            self.assertEqual(self.context, service._context)

    def test_soft_delete(self):
        _id = self.fake_service['id']
        with mock.patch.object(self.dbapi, 'get_service_by_id',
                               autospec=True) as mock_get_service:
            mock_get_service.return_value = self.fake_service
            with mock.patch.object(self.dbapi, 'soft_delete_service',
                                   autospec=True) as mock_soft_delete:
                service = objects.Service.get(self.context, _id)
                service.soft_delete()
                mock_get_service.assert_called_once_with(self.context, _id)
                mock_soft_delete.assert_called_once_with(_id)
                self.assertEqual(self.context, service._context)
