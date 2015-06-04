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


class TestAuditTemplateObject(base.DbTestCase):

    def setUp(self):
        super(TestAuditTemplateObject, self).setUp()
        self.fake_audit_template = utils.get_test_audit_template()

    def test_get_by_id(self):
        audit_template_id = self.fake_audit_template['id']
        with mock.patch.object(self.dbapi, 'get_audit_template_by_id',
                               autospec=True) as mock_get_audit_template:
            mock_get_audit_template.return_value = self.fake_audit_template
            audit_template = objects.AuditTemplate.get(self.context,
                                                       audit_template_id)
            mock_get_audit_template.assert_called_once_with(
                self.context, audit_template_id)
            self.assertEqual(self.context, audit_template._context)

    def test_get_by_uuid(self):
        uuid = self.fake_audit_template['uuid']
        with mock.patch.object(self.dbapi, 'get_audit_template_by_uuid',
                               autospec=True) as mock_get_audit_template:
            mock_get_audit_template.return_value = self.fake_audit_template
            audit_template = objects.AuditTemplate.get(self.context, uuid)
            mock_get_audit_template.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, audit_template._context)

    def test_get_by_name(self):
        name = self.fake_audit_template['name']
        with mock.patch.object(self.dbapi, 'get_audit_template_by_name',
                               autospec=True) as mock_get_audit_template:
            mock_get_audit_template.return_value = self.fake_audit_template
            audit_template = objects.AuditTemplate.get_by_name(
                self.context,
                name)
            mock_get_audit_template.assert_called_once_with(self.context, name)
            self.assertEqual(self.context, audit_template._context)

    def test_get_bad_id_and_uuid(self):
        self.assertRaises(exception.InvalidIdentity,
                          objects.AuditTemplate.get,
                          self.context, 'not-a-uuid')

    def test_list(self):
        with mock.patch.object(self.dbapi, 'get_audit_template_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_audit_template]
            audit_templates = objects.AuditTemplate.list(self.context)
            self.assertEqual(mock_get_list.call_count, 1)
            self.assertThat(audit_templates, HasLength(1))
            self.assertIsInstance(audit_templates[0], objects.AuditTemplate)
            self.assertEqual(self.context, audit_templates[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_audit_template',
                               autospec=True) as mock_create_audit_template:
            mock_create_audit_template.return_value = self.fake_audit_template
            audit_template = objects.AuditTemplate(self.context,
                                                   **self.fake_audit_template)
            audit_template.create()
            mock_create_audit_template.assert_called_once_with(
                self.fake_audit_template)
            self.assertEqual(self.context, audit_template._context)

    def test_destroy(self):
        uuid = self.fake_audit_template['uuid']
        with mock.patch.object(self.dbapi, 'get_audit_template_by_uuid',
                               autospec=True) as mock_get_audit_template:
            mock_get_audit_template.return_value = self.fake_audit_template
            with mock.patch.object(self.dbapi, 'destroy_audit_template',
                                   autospec=True) \
                    as mock_destroy_audit_template:
                audit_template = objects.AuditTemplate.get_by_uuid(
                    self.context, uuid)
                audit_template.destroy()
                mock_get_audit_template.assert_called_once_with(
                    self.context, uuid)
                mock_destroy_audit_template.assert_called_once_with(uuid)
                self.assertEqual(self.context, audit_template._context)

    def test_save(self):
        uuid = self.fake_audit_template['uuid']
        with mock.patch.object(self.dbapi, 'get_audit_template_by_uuid',
                               autospec=True) as mock_get_audit_template:
            mock_get_audit_template.return_value = self.fake_audit_template
            with mock.patch.object(self.dbapi, 'update_audit_template',
                                   autospec=True) \
                    as mock_update_audit_template:
                audit_template = objects.AuditTemplate.get_by_uuid(
                    self.context, uuid)
                audit_template.goal = 'SERVERS_CONSOLIDATION'
                audit_template.save()

                mock_get_audit_template.assert_called_once_with(
                    self.context, uuid)
                mock_update_audit_template.assert_called_once_with(
                    uuid, {'goal': 'SERVERS_CONSOLIDATION'})
                self.assertEqual(self.context, audit_template._context)

    def test_refresh(self):
        uuid = self.fake_audit_template['uuid']
        returns = [dict(self.fake_audit_template,
                        goal="SERVERS_CONSOLIDATION"),
                   dict(self.fake_audit_template, goal="BALANCE_LOAD")]
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        with mock.patch.object(self.dbapi, 'get_audit_template_by_uuid',
                               side_effect=returns,
                               autospec=True) as mock_get_audit_template:
            audit_template = objects.AuditTemplate.get(self.context, uuid)
            self.assertEqual("SERVERS_CONSOLIDATION", audit_template.goal)
            audit_template.refresh()
            self.assertEqual("BALANCE_LOAD", audit_template.goal)
            self.assertEqual(expected, mock_get_audit_template.call_args_list)
            self.assertEqual(self.context, audit_template._context)

    def test_soft_delete(self):
        uuid = self.fake_audit_template['uuid']
        with mock.patch.object(self.dbapi, 'get_audit_template_by_uuid',
                               autospec=True) as mock_get_audit_template:
            mock_get_audit_template.return_value = self.fake_audit_template
            with mock.patch.object(self.dbapi, 'soft_delete_audit_template',
                                   autospec=True) \
                    as mock_soft_delete_audit_template:
                audit_template = objects.AuditTemplate.get_by_uuid(
                    self.context, uuid)
                audit_template.soft_delete()
                mock_get_audit_template.assert_called_once_with(
                    self.context, uuid)
                mock_soft_delete_audit_template.assert_called_once_with(uuid)
                self.assertEqual(self.context, audit_template._context)
