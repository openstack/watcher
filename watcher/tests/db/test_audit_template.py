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

"""Tests for manipulating AuditTemplate via the DB API"""

import six
from watcher.common import exception
from watcher.common import utils as w_utils
from watcher.tests.db import base
from watcher.tests.db import utils


class DbAuditTemplateTestCase(base.DbTestCase):

    def _create_test_audit_template(self, **kwargs):
        audit_template = utils.get_test_audit_template(**kwargs)
        self.dbapi.create_audit_template(audit_template)
        return audit_template

    def test_get_audit_template_list(self):
        uuids = []
        for i in range(1, 6):
            audit_template = utils.create_test_audit_template(
                uuid=w_utils.generate_uuid(),
                name='My Audit Template ' + str(i))
            uuids.append(six.text_type(audit_template['uuid']))
        res = self.dbapi.get_audit_template_list(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(uuids.sort(), res_uuids.sort())

    def test_get_audit_template_list_with_filters(self):
        audit_template1 = self._create_test_audit_template(
            id=1,
            uuid=w_utils.generate_uuid(),
            name='My Audit Template 1',
            description='Description of my audit template 1',
            host_aggregate=5,
            goal='SERVERS_CONSOLIDATION',
            extra={'automatic': True})
        audit_template2 = self._create_test_audit_template(
            id=2,
            uuid=w_utils.generate_uuid(),
            name='My Audit Template 2',
            description='Description of my audit template 2',
            host_aggregate=3,
            goal='SERVERS_CONSOLIDATION',
            extra={'automatic': True})

        res = self.dbapi.get_audit_template_list(self.context,
                                                 filters={'host_aggregate': 5})
        self.assertEqual([audit_template1['id']], [r.id for r in res])

        res = self.dbapi.get_audit_template_list(self.context,
                                                 filters={'host_aggregate': 1})
        self.assertEqual([], [r.id for r in res])

        res = self.dbapi.get_audit_template_list(
            self.context,
            filters={'goal': 'SERVERS_CONSOLIDATION'})
        self.assertEqual([audit_template1['id'], audit_template2['id']],
                         [r.id for r in res])

        res = self.dbapi.get_audit_template_list(
            self.context,
            filters={'name': 'My Audit Template 2'})
        self.assertEqual([audit_template2['id']], [r.id for r in res])

    def test_get_audit_template_by_id(self):
        audit_template = self._create_test_audit_template()
        audit_template = self.dbapi.get_audit_template_by_id(
            self.context, audit_template['id'])
        self.assertEqual(audit_template['uuid'], audit_template.uuid)

    def test_get_audit_template_by_uuid(self):
        audit_template = self._create_test_audit_template()
        audit_template = self.dbapi.get_audit_template_by_uuid(
            self.context, audit_template['uuid'])
        self.assertEqual(audit_template['id'], audit_template.id)

    def test_get_audit_template_that_does_not_exist(self):
        self.assertRaises(exception.AuditTemplateNotFound,
                          self.dbapi.get_audit_template_by_id,
                          self.context, 1234)

    def test_update_audit_template(self):
        audit_template = self._create_test_audit_template()
        res = self.dbapi.update_audit_template(audit_template['id'],
                                               {'name': 'updated-model'})
        self.assertEqual('updated-model', res.name)

    def test_update_audit_template_that_does_not_exist(self):
        self.assertRaises(exception.AuditTemplateNotFound,
                          self.dbapi.update_audit_template, 1234, {'name': ''})

    def test_update_audit_template_uuid(self):
        audit_template = self._create_test_audit_template()
        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.update_audit_template,
                          audit_template['id'],
                          {'uuid': 'hello'})

    def test_destroy_audit_template(self):
        audit_template = self._create_test_audit_template()
        self.dbapi.destroy_audit_template(audit_template['id'])
        self.assertRaises(exception.AuditTemplateNotFound,
                          self.dbapi.get_audit_template_by_id,
                          self.context, audit_template['id'])

    def test_destroy_audit_template_by_uuid(self):
        uuid = w_utils.generate_uuid()
        self._create_test_audit_template(uuid=uuid)
        self.assertIsNotNone(self.dbapi.get_audit_template_by_uuid(
            self.context, uuid))
        self.dbapi.destroy_audit_template(uuid)
        self.assertRaises(exception.AuditTemplateNotFound,
                          self.dbapi.get_audit_template_by_uuid,
                          self.context, uuid)

    def test_destroy_audit_template_that_does_not_exist(self):
        self.assertRaises(exception.AuditTemplateNotFound,
                          self.dbapi.destroy_audit_template, 1234)

    # def test_destroy_audit_template_that_referenced_by_goals(self):
    #     audit_template = self._create_test_audit_template()
    #     goal = utils.create_test_goal(audit_template=audit_template['uuid'])
    #     self.assertEqual(audit_template['uuid'], goal.audit_template)
    #     self.assertRaises(exception.AuditTemplateReferenced,
    #                       self.dbapi.destroy_audit_template,
    #                       audit_template['id'])

    def test_create_audit_template_already_exists(self):
        uuid = w_utils.generate_uuid()
        self._create_test_audit_template(id=1, uuid=uuid)
        self.assertRaises(exception.AuditTemplateAlreadyExists,
                          self._create_test_audit_template,
                          id=2, uuid=uuid)

    def test_audit_template_create_same_name(self):
        audit_template1 = utils.create_test_audit_template(
            uuid=w_utils.generate_uuid(),
            name='audit_template_name')
        self.assertEqual(audit_template1['uuid'], audit_template1.uuid)
        self.assertRaises(
            exception.AuditTemplateAlreadyExists,
            utils.create_test_audit_template,
            uuid=w_utils.generate_uuid(),
            name='audit_template_name')

    def test_audit_template_create_same_uuid(self):
        uuid = w_utils.generate_uuid()
        audit_template1 = utils.create_test_audit_template(
            uuid=uuid,
            name='audit_template_name_1')
        self.assertEqual(audit_template1['uuid'], audit_template1.uuid)
        self.assertRaises(
            exception.AuditTemplateAlreadyExists,
            utils.create_test_audit_template,
            uuid=uuid,
            name='audit_template_name_2')
