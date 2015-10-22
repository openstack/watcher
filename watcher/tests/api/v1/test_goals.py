# Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

from oslo_config import cfg
from watcher.tests.api import base as api_base

CONF = cfg.CONF


class TestListGoal(api_base.FunctionalTest):

    def setUp(self):
        super(TestListGoal, self).setUp()

    def _assert_goal_fields(self, goal):
        goal_fields = ['name', 'strategy']
        for field in goal_fields:
            self.assertIn(field, goal)

    def test_one(self):
        response = self.get_json('/goals')
        self._assert_goal_fields(response['goals'][0])

    def test_get_one(self):
        goal_name = CONF.watcher_goals.goals.keys()[0]
        response = self.get_json('/goals/%s' % goal_name)
        self.assertEqual(goal_name, response['name'])
        self._assert_goal_fields(response)

    def test_detail(self):
        goal_name = CONF.watcher_goals.goals.keys()[0]
        response = self.get_json('/goals/detail')
        self.assertEqual(goal_name, response['goals'][0]["name"])
        self._assert_goal_fields(response['goals'][0])

    def test_detail_against_single(self):
        goal_name = CONF.watcher_goals.goals.keys()[0]
        response = self.get_json('/goals/%s/detail' % goal_name,
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_many(self):
        response = self.get_json('/goals')
        self.assertEqual(len(CONF.watcher_goals.goals),
                         len(response['goals']))

    def test_collection_links(self):
        response = self.get_json('/goals/?limit=2')
        self.assertEqual(2, len(response['goals']))

    def test_collection_links_default_limit(self):
        cfg.CONF.set_override('max_limit', 3, 'api')
        response = self.get_json('/goals')
        self.assertEqual(3, len(response['goals']))
