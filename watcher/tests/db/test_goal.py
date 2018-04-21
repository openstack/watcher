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

"""Tests for manipulating Goal via the DB API"""

import freezegun
import six

from watcher.common import exception
from watcher.common import utils as w_utils
from watcher.tests.db import base
from watcher.tests.db import utils


class TestDbGoalFilters(base.DbTestCase):

    FAKE_OLDER_DATE = '2014-01-01T09:52:05.219414'
    FAKE_OLD_DATE = '2015-01-01T09:52:05.219414'
    FAKE_TODAY = '2016-02-24T09:52:05.219414'

    def setUp(self):
        super(TestDbGoalFilters, self).setUp()
        self.context.show_deleted = True
        self._data_setup()

    def _data_setup(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.goal1 = utils.create_test_goal(
                id=1, uuid=w_utils.generate_uuid(), name="GOAL_1",
                display_name="Goal 1")
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.goal2 = utils.create_test_goal(
                id=2, uuid=w_utils.generate_uuid(),
                name="GOAL_2", display_name="Goal 2")
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.goal3 = utils.create_test_goal(
                id=3, uuid=w_utils.generate_uuid(),
                name="GOAL_3", display_name="Goal 3")

    def _soft_delete_goals(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_goal(self.goal1.id)
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.dbapi.soft_delete_goal(self.goal2.id)
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.dbapi.soft_delete_goal(self.goal3.id)

    def _update_goals(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.update_goal(
                self.goal1.uuid, values={"display_name": "goal1"})
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.dbapi.update_goal(
                self.goal2.uuid, values={"display_name": "goal2"})
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.dbapi.update_goal(
                self.goal3.uuid, values={"display_name": "goal3"})

    def test_get_goal_list_filter_deleted_true(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_goal(self.goal1.id)

        res = self.dbapi.get_goal_list(
            self.context, filters={'deleted': True})

        self.assertEqual([self.goal1.uuid], [r.uuid for r in res])

    def test_get_goal_list_filter_deleted_false(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_goal(self.goal1.id)

        res = self.dbapi.get_goal_list(
            self.context, filters={'deleted': False})

        self.assertEqual(
            set([self.goal2.uuid, self.goal3.uuid]),
            set([r.uuid for r in res]))

    def test_get_goal_list_filter_deleted_at_eq(self):
        self._soft_delete_goals()

        res = self.dbapi.get_goal_list(
            self.context, filters={'deleted_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.goal1.uuid], [r.uuid for r in res])

    def test_get_goal_list_filter_deleted_at_lt(self):
        self._soft_delete_goals()

        res = self.dbapi.get_goal_list(
            self.context, filters={'deleted_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            set([self.goal2.uuid, self.goal3.uuid]),
            set([r.uuid for r in res]))

    def test_get_goal_list_filter_deleted_at_lte(self):
        self._soft_delete_goals()

        res = self.dbapi.get_goal_list(
            self.context, filters={'deleted_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.goal2.uuid, self.goal3.uuid]),
            set([r.uuid for r in res]))

    def test_get_goal_list_filter_deleted_at_gt(self):
        self._soft_delete_goals()

        res = self.dbapi.get_goal_list(
            self.context, filters={'deleted_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.goal1.uuid], [r.uuid for r in res])

    def test_get_goal_list_filter_deleted_at_gte(self):
        self._soft_delete_goals()

        res = self.dbapi.get_goal_list(
            self.context, filters={'deleted_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.goal1.uuid, self.goal2.uuid]),
            set([r.uuid for r in res]))

    # created_at #

    def test_get_goal_list_filter_created_at_eq(self):
        res = self.dbapi.get_goal_list(
            self.context, filters={'created_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.goal1.uuid], [r.uuid for r in res])

    def test_get_goal_list_filter_created_at_lt(self):
        res = self.dbapi.get_goal_list(
            self.context, filters={'created_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            set([self.goal2.uuid, self.goal3.uuid]),
            set([r.uuid for r in res]))

    def test_get_goal_list_filter_created_at_lte(self):
        res = self.dbapi.get_goal_list(
            self.context, filters={'created_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.goal2.uuid, self.goal3.uuid]),
            set([r.uuid for r in res]))

    def test_get_goal_list_filter_created_at_gt(self):
        res = self.dbapi.get_goal_list(
            self.context, filters={'created_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.goal1.uuid], [r.uuid for r in res])

    def test_get_goal_list_filter_created_at_gte(self):
        res = self.dbapi.get_goal_list(
            self.context, filters={'created_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.goal1.uuid, self.goal2.uuid]),
            set([r.uuid for r in res]))

    # updated_at #

    def test_get_goal_list_filter_updated_at_eq(self):
        self._update_goals()

        res = self.dbapi.get_goal_list(
            self.context, filters={'updated_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.goal1.uuid], [r.uuid for r in res])

    def test_get_goal_list_filter_updated_at_lt(self):
        self._update_goals()

        res = self.dbapi.get_goal_list(
            self.context, filters={'updated_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            set([self.goal2.uuid, self.goal3.uuid]),
            set([r.uuid for r in res]))

    def test_get_goal_list_filter_updated_at_lte(self):
        self._update_goals()

        res = self.dbapi.get_goal_list(
            self.context, filters={'updated_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.goal2.uuid, self.goal3.uuid]),
            set([r.uuid for r in res]))

    def test_get_goal_list_filter_updated_at_gt(self):
        self._update_goals()

        res = self.dbapi.get_goal_list(
            self.context, filters={'updated_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.goal1.uuid], [r.uuid for r in res])

    def test_get_goal_list_filter_updated_at_gte(self):
        self._update_goals()

        res = self.dbapi.get_goal_list(
            self.context, filters={'updated_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.goal1.uuid, self.goal2.uuid]),
            set([r.uuid for r in res]))


class DbGoalTestCase(base.DbTestCase):

    def test_get_goal_list(self):
        uuids = []
        for i in range(1, 4):
            goal = utils.create_test_goal(
                id=i,
                uuid=w_utils.generate_uuid(),
                name="GOAL_%s" % i,
                display_name='My Goal %s' % i)
            uuids.append(six.text_type(goal['uuid']))
        goals = self.dbapi.get_goal_list(self.context)
        goal_uuids = [g.uuid for g in goals]
        self.assertEqual(sorted(uuids), sorted(goal_uuids))

    def test_get_goal_list_with_filters(self):
        goal1 = utils.create_test_goal(
            id=1,
            uuid=w_utils.generate_uuid(),
            name="GOAL_1",
            display_name='Goal 1',
        )
        goal2 = utils.create_test_goal(
            id=2,
            uuid=w_utils.generate_uuid(),
            name="GOAL_2",
            display_name='Goal 2',
        )
        goal3 = utils.create_test_goal(
            id=3,
            uuid=w_utils.generate_uuid(),
            name="GOAL_3",
            display_name='Goal 3',
        )

        self.dbapi.soft_delete_goal(goal3['uuid'])

        res = self.dbapi.get_goal_list(
            self.context, filters={'display_name': 'Goal 1'})
        self.assertEqual([goal1['uuid']], [r.uuid for r in res])

        res = self.dbapi.get_goal_list(
            self.context, filters={'display_name': 'Goal 3'})
        self.assertEqual([], [r.uuid for r in res])

        res = self.dbapi.get_goal_list(
            self.context, filters={'name': 'GOAL_1'})
        self.assertEqual([goal1['uuid']], [r.uuid for r in res])

        res = self.dbapi.get_goal_list(
            self.context, filters={'display_name': 'Goal 2'})
        self.assertEqual([goal2['uuid']], [r.uuid for r in res])

        res = self.dbapi.get_goal_list(
            self.context, filters={'uuid': goal3['uuid']})
        self.assertEqual([], [r.uuid for r in res])

    def test_get_goal_by_uuid(self):
        efficacy_spec = [{"unit": "%", "name": "dummy",
                          "schema": "Range(min=0, max=100, min_included=True, "
                                    "max_included=True, msg=None)",
                          "description": "Dummy indicator"}]
        created_goal = utils.create_test_goal(
            efficacy_specification=efficacy_spec)
        goal = self.dbapi.get_goal_by_uuid(self.context, created_goal['uuid'])
        self.assertEqual(goal.uuid, created_goal['uuid'])

    def test_get_goal_that_does_not_exist(self):
        random_uuid = w_utils.generate_uuid()
        self.assertRaises(exception.GoalNotFound,
                          self.dbapi.get_goal_by_uuid,
                          self.context, random_uuid)

    def test_update_goal(self):
        goal = utils.create_test_goal()
        res = self.dbapi.update_goal(goal['uuid'],
                                     {'display_name': 'updated-model'})
        self.assertEqual('updated-model', res.display_name)

    def test_update_goal_id(self):
        goal = utils.create_test_goal()
        self.assertRaises(exception.Invalid,
                          self.dbapi.update_goal, goal['uuid'],
                          {'uuid': 'NEW_GOAL'})

    def test_update_goal_that_does_not_exist(self):
        random_uuid = w_utils.generate_uuid()
        self.assertRaises(exception.GoalNotFound,
                          self.dbapi.update_goal,
                          random_uuid,
                          {'display_name': ''})

    def test_destroy_goal(self):
        goal = utils.create_test_goal()
        self.dbapi.destroy_goal(goal['uuid'])
        self.assertRaises(exception.GoalNotFound,
                          self.dbapi.get_goal_by_uuid,
                          self.context, goal['uuid'])

    def test_destroy_goal_that_does_not_exist(self):
        random_uuid = w_utils.generate_uuid()
        self.assertRaises(exception.GoalNotFound,
                          self.dbapi.destroy_goal, random_uuid)

    def test_create_goal_already_exists(self):
        goal_uuid = w_utils.generate_uuid()
        utils.create_test_goal(uuid=goal_uuid)
        self.assertRaises(exception.GoalAlreadyExists,
                          utils.create_test_goal,
                          uuid=goal_uuid)
