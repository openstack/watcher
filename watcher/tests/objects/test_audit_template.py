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

import iso8601

from watcher.common import exception
from watcher.common import utils as w_utils
from watcher.db.sqlalchemy import api as db_api
from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils


class TestAuditTemplateObject(base.DbTestCase):

    goal_id = 1

    goal_data = utils.get_test_goal(
        id=goal_id, uuid=w_utils.generate_uuid(), name="DUMMY")

    scenarios = [
        ('non_eager', dict(
            eager=False,
            fake_audit_template=utils.get_test_audit_template(
                created_at=datetime.datetime.utcnow(),
                goal_id=goal_id))),
        ('eager_with_non_eager_load', dict(
            eager=True,
            fake_audit_template=utils.get_test_audit_template(
                created_at=datetime.datetime.utcnow(),
                goal_id=goal_id))),
        ('eager_with_eager_load', dict(
            eager=True,
            fake_audit_template=utils.get_test_audit_template(
                created_at=datetime.datetime.utcnow(),
                goal_id=goal_id, goal=goal_data))),
    ]

    def setUp(self):
        super(TestAuditTemplateObject, self).setUp()
        self.fake_goal = utils.create_test_goal(**self.goal_data)

    def eager_load_audit_template_assert(self, audit_template, goal):
        if self.eager:
            self.assertIsNotNone(audit_template.goal)
            fields_to_check = set(
                super(objects.Goal, objects.Goal).fields
            ).symmetric_difference(objects.Goal.fields)
            db_data = {
                k: v for k, v in goal.as_dict().items()
                if k in fields_to_check}
            object_data = {
                k: v for k, v in audit_template.goal.as_dict().items()
                if k in fields_to_check}
            self.assertEqual(db_data, object_data)

    @mock.patch.object(db_api.Connection, 'get_audit_template_by_id')
    def test_get_by_id(self, mock_get_audit_template):
        mock_get_audit_template.return_value = self.fake_audit_template
        audit_template_id = self.fake_audit_template['id']
        audit_template = objects.AuditTemplate.get(
            self.context, audit_template_id, eager=self.eager)
        mock_get_audit_template.assert_called_once_with(
            self.context, audit_template_id, eager=self.eager)
        self.assertEqual(self.context, audit_template._context)
        self.eager_load_audit_template_assert(audit_template, self.fake_goal)

    @mock.patch.object(db_api.Connection, 'get_audit_template_by_uuid')
    def test_get_by_uuid(self, mock_get_audit_template):
        mock_get_audit_template.return_value = self.fake_audit_template
        uuid = self.fake_audit_template['uuid']
        audit_template = objects.AuditTemplate.get(
            self.context, uuid, eager=self.eager)
        mock_get_audit_template.assert_called_once_with(
            self.context, uuid, eager=self.eager)
        self.assertEqual(self.context, audit_template._context)
        self.eager_load_audit_template_assert(audit_template, self.fake_goal)

    @mock.patch.object(db_api.Connection, 'get_audit_template_by_name')
    def test_get_by_name(self, mock_get_audit_template):
        mock_get_audit_template.return_value = self.fake_audit_template
        name = self.fake_audit_template['name']
        audit_template = objects.AuditTemplate.get_by_name(
            self.context, name, eager=self.eager)
        mock_get_audit_template.assert_called_once_with(
            self.context, name, eager=self.eager)
        self.assertEqual(self.context, audit_template._context)
        self.eager_load_audit_template_assert(audit_template, self.fake_goal)

    def test_get_bad_id_and_uuid(self):
        self.assertRaises(exception.InvalidIdentity,
                          objects.AuditTemplate.get,
                          self.context, 'not-a-uuid', eager=self.eager)

    @mock.patch.object(db_api.Connection, 'get_audit_template_list')
    def test_list(self, mock_get_list):
        mock_get_list.return_value = [self.fake_audit_template]
        audit_templates = objects.AuditTemplate.list(
            self.context, eager=self.eager)
        mock_get_list.assert_called_once_with(
            self.context, eager=self.eager, filters=None, limit=None,
            marker=None, sort_dir=None, sort_key=None)
        self.assertEqual(1, len(audit_templates))
        self.assertIsInstance(audit_templates[0], objects.AuditTemplate)
        self.assertEqual(self.context, audit_templates[0]._context)
        for audit_template in audit_templates:
            self.eager_load_audit_template_assert(
                audit_template, self.fake_goal)

    @mock.patch.object(db_api.Connection, 'update_audit_template')
    @mock.patch.object(db_api.Connection, 'get_audit_template_by_uuid')
    def test_save(self, mock_get_audit_template, mock_update_audit_template):
        mock_get_audit_template.return_value = self.fake_audit_template
        fake_saved_audit_template = self.fake_audit_template.copy()
        fake_saved_audit_template['updated_at'] = datetime.datetime.utcnow()
        mock_update_audit_template.return_value = fake_saved_audit_template
        uuid = self.fake_audit_template['uuid']
        audit_template = objects.AuditTemplate.get_by_uuid(
            self.context, uuid, eager=self.eager)
        audit_template.goal_id = self.fake_goal.id
        audit_template.save()

        mock_get_audit_template.assert_called_once_with(
            self.context, uuid, eager=self.eager)
        mock_update_audit_template.assert_called_once_with(
            uuid, {'goal_id': self.fake_goal.id})
        self.assertEqual(self.context, audit_template._context)
        self.eager_load_audit_template_assert(audit_template, self.fake_goal)

    @mock.patch.object(db_api.Connection, 'get_audit_template_by_uuid')
    def test_refresh(self, mock_get_audit_template):
        returns = [dict(self.fake_audit_template, name="first name"),
                   dict(self.fake_audit_template, name="second name")]
        mock_get_audit_template.side_effect = returns
        uuid = self.fake_audit_template['uuid']
        expected = [mock.call(self.context, uuid, eager=self.eager),
                    mock.call(self.context, uuid, eager=self.eager)]
        audit_template = objects.AuditTemplate.get(
            self.context, uuid, eager=self.eager)
        self.assertEqual("first name", audit_template.name)
        audit_template.refresh(eager=self.eager)
        self.assertEqual("second name", audit_template.name)
        self.assertEqual(expected, mock_get_audit_template.call_args_list)
        self.assertEqual(self.context, audit_template._context)
        self.eager_load_audit_template_assert(audit_template, self.fake_goal)


class TestCreateDeleteAuditTemplateObject(base.DbTestCase):

    def setUp(self):
        super(TestCreateDeleteAuditTemplateObject, self).setUp()
        self.fake_audit_template = utils.get_test_audit_template(
            created_at=datetime.datetime.utcnow())

    @mock.patch.object(db_api.Connection, 'create_audit_template')
    def test_create(self, mock_create_audit_template):
        goal = utils.create_test_goal()
        self.fake_audit_template['goal_id'] = goal.id
        mock_create_audit_template.return_value = self.fake_audit_template
        audit_template = objects.AuditTemplate(
            self.context, **self.fake_audit_template)
        audit_template.create()
        expected_audit_template = self.fake_audit_template.copy()
        expected_audit_template['created_at'] = expected_audit_template[
            'created_at'].replace(tzinfo=iso8601.UTC)
        mock_create_audit_template.assert_called_once_with(
            expected_audit_template)
        self.assertEqual(self.context, audit_template._context)

    @mock.patch.object(db_api.Connection, 'soft_delete_audit_template')
    @mock.patch.object(db_api.Connection, 'get_audit_template_by_uuid')
    def test_soft_delete(self, m_get_audit_template,
                         m_soft_delete_audit_template):
        m_get_audit_template.return_value = self.fake_audit_template
        fake_deleted_audit_template = self.fake_audit_template.copy()
        fake_deleted_audit_template['deleted_at'] = datetime.datetime.utcnow()
        m_soft_delete_audit_template.return_value = fake_deleted_audit_template

        expected_audit_template = fake_deleted_audit_template.copy()
        expected_audit_template['created_at'] = expected_audit_template[
            'created_at'].replace(tzinfo=iso8601.UTC)
        expected_audit_template['deleted_at'] = expected_audit_template[
            'deleted_at'].replace(tzinfo=iso8601.UTC)
        del expected_audit_template['goal']
        del expected_audit_template['strategy']

        uuid = self.fake_audit_template['uuid']
        audit_template = objects.AuditTemplate.get_by_uuid(self.context, uuid)
        audit_template.soft_delete()
        m_get_audit_template.assert_called_once_with(
            self.context, uuid, eager=False)
        m_soft_delete_audit_template.assert_called_once_with(uuid)
        self.assertEqual(self.context, audit_template._context)
        self.assertEqual(expected_audit_template, audit_template.as_dict())

    @mock.patch.object(db_api.Connection, 'destroy_audit_template')
    @mock.patch.object(db_api.Connection, 'get_audit_template_by_uuid')
    def test_destroy(self, mock_get_audit_template,
                     mock_destroy_audit_template):
        mock_get_audit_template.return_value = self.fake_audit_template
        uuid = self.fake_audit_template['uuid']
        audit_template = objects.AuditTemplate.get_by_uuid(self.context, uuid)
        audit_template.destroy()
        mock_get_audit_template.assert_called_once_with(
            self.context, uuid, eager=False)
        mock_destroy_audit_template.assert_called_once_with(uuid)
        self.assertEqual(self.context, audit_template._context)
