# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

from tempest import test

from watcher_tempest_plugin.tests.api.admin import base


class TestShowListGoal(base.BaseInfraOptimTest):
    """Tests for goals"""

    DUMMY_GOAL = "dummy"

    @classmethod
    def resource_setup(cls):
        super(TestShowListGoal, cls).resource_setup()

    def assert_expected(self, expected, actual,
                        keys=('created_at', 'updated_at', 'deleted_at')):
        super(TestShowListGoal, self).assert_expected(
            expected, actual, keys)

    @test.attr(type='smoke')
    def test_show_goal(self):
        _, goal = self.client.show_goal(self.DUMMY_GOAL)

        self.assertEqual(self.DUMMY_GOAL, goal['name'])
        self.assertIn("display_name", goal.keys())

    @test.attr(type='smoke')
    def test_show_goal_with_links(self):
        _, goal = self.client.show_goal(self.DUMMY_GOAL)
        self.assertIn('links', goal.keys())
        self.assertEqual(2, len(goal['links']))
        self.assertIn(goal['uuid'],
                      goal['links'][0]['href'])

    @test.attr(type="smoke")
    def test_list_goals(self):
        _, body = self.client.list_goals()
        self.assertIn(self.DUMMY_GOAL,
                      [i['name'] for i in body['goals']])

        # Verify self links.
        for goal in body['goals']:
            self.validate_self_link('goals', goal['uuid'],
                                    goal['links'][0]['href'])
