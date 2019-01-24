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

import freezegun
import six

from watcher.common import exception
from watcher.common import utils as w_utils
from watcher.tests.db import base
from watcher.tests.db import utils


class TestDbAuditTemplateFilters(base.DbTestCase):

    FAKE_OLDER_DATE = '2014-01-01T09:52:05.219414'
    FAKE_OLD_DATE = '2015-01-01T09:52:05.219414'
    FAKE_TODAY = '2016-02-24T09:52:05.219414'

    def setUp(self):
        super(TestDbAuditTemplateFilters, self).setUp()
        self.context.show_deleted = True
        self._data_setup()

    def _data_setup(self):

        def gen_name():
            return "Audit Template %s" % w_utils.generate_uuid()

        self.audit_template1_name = gen_name()
        self.audit_template2_name = gen_name()
        self.audit_template3_name = gen_name()

        with freezegun.freeze_time(self.FAKE_TODAY):
            self.audit_template1 = utils.create_test_audit_template(
                name=self.audit_template1_name, id=1, uuid=None)
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.audit_template2 = utils.create_test_audit_template(
                name=self.audit_template2_name, id=2, uuid=None)
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.audit_template3 = utils.create_test_audit_template(
                name=self.audit_template3_name, id=3, uuid=None)

    def _soft_delete_audit_templates(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_audit_template(self.audit_template1.uuid)
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.dbapi.soft_delete_audit_template(self.audit_template2.uuid)
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.dbapi.soft_delete_audit_template(self.audit_template3.uuid)

    def _update_audit_templates(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.update_audit_template(
                self.audit_template1.uuid, values={"name": "audit_template1"})
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.dbapi.update_audit_template(
                self.audit_template2.uuid, values={"name": "audit_template2"})
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.dbapi.update_audit_template(
                self.audit_template3.uuid, values={"name": "audit_template3"})

    def test_get_audit_template_list_filter_deleted_true(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_audit_template(self.audit_template1.uuid)

        res = self.dbapi.get_audit_template_list(
            self.context, filters={'deleted': True})

        self.assertEqual([self.audit_template1['id']], [r.id for r in res])

    def test_get_audit_template_list_filter_deleted_false(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_audit_template(self.audit_template1.uuid)

        res = self.dbapi.get_audit_template_list(
            self.context, filters={'deleted': False})

        self.assertEqual(
            [self.audit_template2['id'], self.audit_template3['id']],
            [r.id for r in res])

    def test_get_audit_template_list_filter_deleted_at_eq(self):
        self._soft_delete_audit_templates()

        res = self.dbapi.get_audit_template_list(
            self.context, filters={'deleted_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.audit_template1['id']], [r.id for r in res])

    def test_get_audit_template_list_filter_deleted_at_lt(self):
        self._soft_delete_audit_templates()

        res = self.dbapi.get_audit_template_list(
            self.context, filters={'deleted_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            [self.audit_template2['id'], self.audit_template3['id']],
            [r.id for r in res])

    def test_get_audit_template_list_filter_deleted_at_lte(self):
        self._soft_delete_audit_templates()

        res = self.dbapi.get_audit_template_list(
            self.context, filters={'deleted_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.audit_template2['id'], self.audit_template3['id']],
            [r.id for r in res])

    def test_get_audit_template_list_filter_deleted_at_gt(self):
        self._soft_delete_audit_templates()

        res = self.dbapi.get_audit_template_list(
            self.context, filters={'deleted_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.audit_template1['id']], [r.id for r in res])

    def test_get_audit_template_list_filter_deleted_at_gte(self):
        self._soft_delete_audit_templates()

        res = self.dbapi.get_audit_template_list(
            self.context, filters={'deleted_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.audit_template1['id'], self.audit_template2['id']],
            [r.id for r in res])

    # created_at #

    def test_get_audit_template_list_filter_created_at_eq(self):
        res = self.dbapi.get_audit_template_list(
            self.context, filters={'created_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.audit_template1['id']], [r.id for r in res])

    def test_get_audit_template_list_filter_created_at_lt(self):
        res = self.dbapi.get_audit_template_list(
            self.context, filters={'created_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            [self.audit_template2['id'], self.audit_template3['id']],
            [r.id for r in res])

    def test_get_audit_template_list_filter_created_at_lte(self):
        res = self.dbapi.get_audit_template_list(
            self.context, filters={'created_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.audit_template2['id'], self.audit_template3['id']],
            [r.id for r in res])

    def test_get_audit_template_list_filter_created_at_gt(self):
        res = self.dbapi.get_audit_template_list(
            self.context, filters={'created_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.audit_template1['id']], [r.id for r in res])

    def test_get_audit_template_list_filter_created_at_gte(self):
        res = self.dbapi.get_audit_template_list(
            self.context, filters={'created_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.audit_template1['id'], self.audit_template2['id']],
            [r.id for r in res])

    # updated_at #

    def test_get_audit_template_list_filter_updated_at_eq(self):
        self._update_audit_templates()

        res = self.dbapi.get_audit_template_list(
            self.context, filters={'updated_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.audit_template1['id']], [r.id for r in res])

    def test_get_audit_template_list_filter_updated_at_lt(self):
        self._update_audit_templates()

        res = self.dbapi.get_audit_template_list(
            self.context, filters={'updated_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            [self.audit_template2['id'], self.audit_template3['id']],
            [r.id for r in res])

    def test_get_audit_template_list_filter_updated_at_lte(self):
        self._update_audit_templates()

        res = self.dbapi.get_audit_template_list(
            self.context, filters={'updated_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.audit_template2['id'], self.audit_template3['id']],
            [r.id for r in res])

    def test_get_audit_template_list_filter_updated_at_gt(self):
        self._update_audit_templates()

        res = self.dbapi.get_audit_template_list(
            self.context, filters={'updated_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.audit_template1['id']], [r.id for r in res])

    def test_get_audit_template_list_filter_updated_at_gte(self):
        self._update_audit_templates()

        res = self.dbapi.get_audit_template_list(
            self.context, filters={'updated_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.audit_template1['id'], self.audit_template2['id']],
            [r.id for r in res])


class DbAuditTemplateTestCase(base.DbTestCase):

    def test_get_audit_template_list(self):
        uuids = []
        for i in range(1, 4):
            audit_template = utils.create_test_audit_template(
                id=i,
                uuid=w_utils.generate_uuid(),
                name='My Audit Template {0}'.format(i))
            uuids.append(six.text_type(audit_template['uuid']))
        audit_templates = self.dbapi.get_audit_template_list(self.context)
        audit_template_uuids = [at.uuid for at in audit_templates]
        self.assertEqual(sorted(uuids), sorted(audit_template_uuids))
        for audit_template in audit_templates:
            self.assertIsNone(audit_template.goal)
            self.assertIsNone(audit_template.strategy)

    def test_get_audit_template_list_eager(self):
        _goal = utils.get_test_goal()
        goal = self.dbapi.create_goal(_goal)
        _strategy = utils.get_test_strategy()
        strategy = self.dbapi.create_strategy(_strategy)

        uuids = []
        for i in range(1, 4):
            audit_template = utils.create_test_audit_template(
                id=i, uuid=w_utils.generate_uuid(),
                name='My Audit Template {0}'.format(i),
                goal_id=goal.id, strategy_id=strategy.id)
            uuids.append(six.text_type(audit_template['uuid']))
        audit_templates = self.dbapi.get_audit_template_list(
            self.context, eager=True)
        audit_template_map = {a.uuid: a for a in audit_templates}
        self.assertEqual(sorted(uuids), sorted(audit_template_map.keys()))
        eager_audit_template = audit_template_map[audit_template.uuid]
        self.assertEqual(goal.as_dict(), eager_audit_template.goal.as_dict())
        self.assertEqual(
            strategy.as_dict(), eager_audit_template.strategy.as_dict())

    def test_get_audit_template_list_with_filters(self):
        goal = utils.create_test_goal(name='DUMMY')

        audit_template1 = utils.create_test_audit_template(
            id=1,
            uuid=w_utils.generate_uuid(),
            name='My Audit Template 1',
            description='Description of my audit template 1',
            goal_id=goal['id'])
        audit_template2 = utils.create_test_audit_template(
            id=2,
            uuid=w_utils.generate_uuid(),
            name='My Audit Template 2',
            description='Description of my audit template 2',
            goal_id=goal['id'])
        audit_template3 = utils.create_test_audit_template(
            id=3,
            uuid=w_utils.generate_uuid(),
            name='My Audit Template 3',
            description='Description of my audit template 3',
            goal_id=goal['id'])

        self.dbapi.soft_delete_audit_template(audit_template3['uuid'])

        res = self.dbapi.get_audit_template_list(
            self.context,
            filters={'name': 'My Audit Template 1'})
        self.assertEqual([audit_template1['id']], [r.id for r in res])

        res = self.dbapi.get_audit_template_list(
            self.context,
            filters={'name': 'Does not exist'})
        self.assertEqual([], [r.id for r in res])

        res = self.dbapi.get_audit_template_list(
            self.context,
            filters={'goal_name': 'DUMMY'})
        self.assertEqual(
            sorted([audit_template1['id'], audit_template2['id']]),
            sorted([r.id for r in res]))

        temp_context = self.context
        temp_context.show_deleted = True
        res = self.dbapi.get_audit_template_list(
            temp_context,
            filters={'goal_name': 'DUMMY'})
        self.assertEqual(
            sorted([audit_template1['id'], audit_template2['id'],
                    audit_template3['id']]),
            sorted([r.id for r in res]))

        res = self.dbapi.get_audit_template_list(
            self.context,
            filters={'name': 'My Audit Template 2'})
        self.assertEqual([audit_template2['id']], [r.id for r in res])

    def test_get_audit_template_list_with_filter_by_uuid(self):
        audit_template = utils.create_test_audit_template()
        res = self.dbapi.get_audit_template_list(
            self.context, filters={'uuid': audit_template["uuid"]})

        self.assertEqual(len(res), 1)
        self.assertEqual(audit_template['uuid'], res[0].uuid)

    def test_get_audit_template_by_id(self):
        audit_template = utils.create_test_audit_template()
        audit_template = self.dbapi.get_audit_template_by_id(
            self.context, audit_template['id'])
        self.assertEqual(audit_template['uuid'], audit_template.uuid)

    def test_get_audit_template_by_uuid(self):
        audit_template = utils.create_test_audit_template()
        audit_template = self.dbapi.get_audit_template_by_uuid(
            self.context, audit_template['uuid'])
        self.assertEqual(audit_template['id'], audit_template.id)

    def test_get_audit_template_that_does_not_exist(self):
        self.assertRaises(exception.AuditTemplateNotFound,
                          self.dbapi.get_audit_template_by_id,
                          self.context, 1234)

    def test_update_audit_template(self):
        audit_template = utils.create_test_audit_template()
        res = self.dbapi.update_audit_template(audit_template['id'],
                                               {'name': 'updated-model'})
        self.assertEqual('updated-model', res.name)

    def test_update_audit_template_that_does_not_exist(self):
        self.assertRaises(exception.AuditTemplateNotFound,
                          self.dbapi.update_audit_template, 1234, {'name': ''})

    def test_update_audit_template_uuid(self):
        audit_template = utils.create_test_audit_template()
        self.assertRaises(exception.Invalid,
                          self.dbapi.update_audit_template,
                          audit_template['id'],
                          {'uuid': 'hello'})

    def test_destroy_audit_template(self):
        audit_template = utils.create_test_audit_template()
        self.dbapi.destroy_audit_template(audit_template['id'])
        self.assertRaises(exception.AuditTemplateNotFound,
                          self.dbapi.get_audit_template_by_id,
                          self.context, audit_template['id'])

    def test_destroy_audit_template_by_uuid(self):
        uuid = w_utils.generate_uuid()
        utils.create_test_audit_template(uuid=uuid)
        self.assertIsNotNone(self.dbapi.get_audit_template_by_uuid(
            self.context, uuid))
        self.dbapi.destroy_audit_template(uuid)
        self.assertRaises(exception.AuditTemplateNotFound,
                          self.dbapi.get_audit_template_by_uuid,
                          self.context, uuid)

    def test_destroy_audit_template_that_does_not_exist(self):
        self.assertRaises(exception.AuditTemplateNotFound,
                          self.dbapi.destroy_audit_template, 1234)

    def test_create_audit_template_already_exists(self):
        uuid = w_utils.generate_uuid()
        utils.create_test_audit_template(id=1, uuid=uuid)
        self.assertRaises(exception.AuditTemplateAlreadyExists,
                          utils.create_test_audit_template,
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
