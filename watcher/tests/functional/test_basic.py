# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from watcher.tests.functional import base


class TestBasicFunctional(base.WatcherFunctionalTestCase):
    """Basic smoke tests for functional test infrastructure.

    These tests validate that the test fixtures are wired correctly
    and the API is reachable, without starting background services.
    """

    START_DECISION_ENGINE = False
    START_APPLIER = False

    def test_api_root(self):
        resp = self.api.get('/')
        self.assertEqual(200, resp.status_code)

    def test_list_goals(self):
        resp = self.api.get('/goals')
        self.assertEqual(200, resp.status_code)
        body = resp.json()
        self.assertIn('goals', body)
        self.assertGreater(len(body['goals']), 0)

        goal_names = {g['name'] for g in body['goals']}
        for expected in ('dummy', 'unclassified', 'server_consolidation'):
            self.assertIn(expected, goal_names)

        goal = body['goals'][0]
        for field in ('uuid', 'name', 'display_name', 'links'):
            self.assertIn(field, goal)
        self.assertIsInstance(goal['links'], list)
        self.assertGreater(len(goal['links']), 0)

    def test_get_goal_detail(self):
        resp = self.api.get('/goals/dummy')
        self.assertEqual(200, resp.status_code)
        goal = resp.json()
        self.assertEqual('dummy', goal['name'])
        for field in (
            'uuid',
            'name',
            'display_name',
            'efficacy_specification',
            'links',
        ):
            self.assertIn(field, goal)
        self.assertIsInstance(goal['efficacy_specification'], list)

    def test_get_goal_not_found(self):
        resp = self.api.get('/goals/nonexistent')
        self.assertEqual(404, resp.status_code)

    def test_list_goals_detail(self):
        resp = self.api.get('/goals/detail')
        self.assertEqual(200, resp.status_code)
        body = resp.json()
        self.assertIn('goals', body)
        goal = body['goals'][0]
        self.assertIn('efficacy_specification', goal)

    def test_list_strategies(self):
        resp = self.api.get('/strategies')
        self.assertEqual(200, resp.status_code)
        body = resp.json()
        self.assertIn('strategies', body)
        self.assertGreater(len(body['strategies']), 0)

        strategy_names = {s['name'] for s in body['strategies']}
        for expected in ('dummy', 'actuator', 'basic'):
            self.assertIn(expected, strategy_names)

        strategy = body['strategies'][0]
        for field in (
            'uuid',
            'name',
            'display_name',
            'goal_uuid',
            'goal_name',
            'links',
        ):
            self.assertIn(field, strategy)

    def test_get_strategy_detail(self):
        resp = self.api.get('/strategies/dummy')
        self.assertEqual(200, resp.status_code)
        strategy = resp.json()
        self.assertEqual('dummy', strategy['name'])
        self.assertEqual('dummy', strategy['goal_name'])
        for field in (
            'uuid',
            'name',
            'display_name',
            'goal_uuid',
            'goal_name',
            'parameters_spec',
            'links',
        ):
            self.assertIn(field, strategy)
        self.assertIsInstance(strategy['parameters_spec'], dict)

    def test_get_strategy_not_found(self):
        resp = self.api.get('/strategies/nonexistent')
        self.assertEqual(404, resp.status_code)

    def test_list_strategies_detail(self):
        resp = self.api.get('/strategies/detail')
        self.assertEqual(200, resp.status_code)
        body = resp.json()
        self.assertIn('strategies', body)
        strategy = body['strategies'][0]
        self.assertIn('parameters_spec', strategy)

    def test_strategy_goal_relationship(self):
        resp = self.api.get('/strategies/dummy')
        self.assertEqual(200, resp.status_code)
        strategy = resp.json()
        goal_uuid = strategy['goal_uuid']

        resp = self.api.get('/goals/%s' % goal_uuid)
        self.assertEqual(200, resp.status_code)
        goal = resp.json()
        self.assertEqual('dummy', goal['name'])

    def test_list_audits_empty(self):
        resp = self.api.get('/audits')
        self.assertEqual(200, resp.status_code)
        body = resp.json()
        self.assertEqual([], body['audits'])


class TestServicesRunning(base.WatcherFunctionalTestCase):
    """Tests that verify services can start alongside the API."""

    START_DECISION_ENGINE = True
    START_APPLIER = True

    def test_services_started(self):
        self.assertIsNotNone(self.de_fixture.service)
        self.assertIsNotNone(self.applier_fixture.service)

    def test_api_with_services(self):
        resp = self.api.get('/goals')
        self.assertEqual(200, resp.status_code)
