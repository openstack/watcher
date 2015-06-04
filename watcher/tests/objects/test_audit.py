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
from testtools.matchers import HasLength

from watcher.common import exception
# from watcher.common import utils as w_utils
from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils


class TestAuditObject(base.DbTestCase):

    def setUp(self):
        super(TestAuditObject, self).setUp()
        self.fake_audit = utils.get_test_audit()

    def test_get_by_id(self):
        audit_id = self.fake_audit['id']
        with mock.patch.object(self.dbapi, 'get_audit_by_id',
                               autospec=True) as mock_get_audit:
            mock_get_audit.return_value = self.fake_audit
            audit = objects.Audit.get(self.context, audit_id)
            mock_get_audit.assert_called_once_with(self.context,
                                                   audit_id)
            self.assertEqual(self.context, audit._context)

    def test_get_by_uuid(self):
        uuid = self.fake_audit['uuid']
        with mock.patch.object(self.dbapi, 'get_audit_by_uuid',
                               autospec=True) as mock_get_audit:
            mock_get_audit.return_value = self.fake_audit
            audit = objects.Audit.get(self.context, uuid)
            mock_get_audit.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, audit._context)

    def test_get_bad_id_and_uuid(self):
        self.assertRaises(exception.InvalidIdentity,
                          objects.Audit.get, self.context, 'not-a-uuid')

    def test_list(self):
        with mock.patch.object(self.dbapi, 'get_audit_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_audit]
            audits = objects.Audit.list(self.context)
            self.assertEqual(mock_get_list.call_count, 1)
            self.assertThat(audits, HasLength(1))
            self.assertIsInstance(audits[0], objects.Audit)
            self.assertEqual(self.context, audits[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_audit',
                               autospec=True) as mock_create_audit:
            mock_create_audit.return_value = self.fake_audit
            audit = objects.Audit(self.context, **self.fake_audit)

            audit.create()
            mock_create_audit.assert_called_once_with(self.fake_audit)
            self.assertEqual(self.context, audit._context)

    def test_destroy(self):
        uuid = self.fake_audit['uuid']
        with mock.patch.object(self.dbapi, 'get_audit_by_uuid',
                               autospec=True) as mock_get_audit:
            mock_get_audit.return_value = self.fake_audit
            with mock.patch.object(self.dbapi, 'destroy_audit',
                                   autospec=True) as mock_destroy_audit:
                audit = objects.Audit.get_by_uuid(self.context, uuid)
                audit.destroy()
                mock_get_audit.assert_called_once_with(self.context, uuid)
                mock_destroy_audit.assert_called_once_with(uuid)
                self.assertEqual(self.context, audit._context)

    def test_save(self):
        uuid = self.fake_audit['uuid']
        with mock.patch.object(self.dbapi, 'get_audit_by_uuid',
                               autospec=True) as mock_get_audit:
            mock_get_audit.return_value = self.fake_audit
            with mock.patch.object(self.dbapi, 'update_audit',
                                   autospec=True) as mock_update_audit:
                audit = objects.Audit.get_by_uuid(self.context, uuid)
                audit.state = 'SUCCESS'
                audit.save()

                mock_get_audit.assert_called_once_with(self.context, uuid)
                mock_update_audit.assert_called_once_with(
                    uuid, {'state': 'SUCCESS'})
                self.assertEqual(self.context, audit._context)

    def test_refresh(self):
        uuid = self.fake_audit['uuid']
        returns = [dict(self.fake_audit, state="first state"),
                   dict(self.fake_audit, state="second state")]
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        with mock.patch.object(self.dbapi, 'get_audit_by_uuid',
                               side_effect=returns,
                               autospec=True) as mock_get_audit:
            audit = objects.Audit.get(self.context, uuid)
            self.assertEqual("first state", audit.state)
            audit.refresh()
            self.assertEqual("second state", audit.state)
            self.assertEqual(expected, mock_get_audit.call_args_list)
            self.assertEqual(self.context, audit._context)
