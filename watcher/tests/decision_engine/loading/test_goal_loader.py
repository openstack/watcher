# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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

from stevedore import extension
from unittest import mock

from watcher.common import exception
from watcher.decision_engine.goal import goals
from watcher.decision_engine.loading import default as default_loading
from watcher.tests import base


class TestDefaultGoalLoader(base.TestCase):

    def setUp(self):
        super(TestDefaultGoalLoader, self).setUp()
        self.goal_loader = default_loading.DefaultGoalLoader()

    def test_load_goal_with_empty_model(self):
        self.assertRaises(
            exception.LoadingError, self.goal_loader.load, None)

    def test_goal_loader(self):
        dummy_goal_name = "dummy"
        # Set up the fake Stevedore extensions
        fake_extmanager_call = extension.ExtensionManager.make_test_instance(
            extensions=[extension.Extension(
                name=dummy_goal_name,
                entry_point="%s:%s" % (
                    goals.Dummy.__module__,
                    goals.Dummy.__name__),
                plugin=goals.Dummy,
                obj=None,
            )],
            namespace="watcher_goals",
        )

        with mock.patch.object(extension, "ExtensionManager") as m_ext_manager:
            m_ext_manager.return_value = fake_extmanager_call
            loaded_goal = self.goal_loader.load("dummy")

        self.assertEqual("dummy", loaded_goal.name)
        self.assertEqual("Dummy goal", loaded_goal.display_name)

    def test_load_dummy_goal(self):
        goal_loader = default_loading.DefaultGoalLoader()
        loaded_goal = goal_loader.load("dummy")
        self.assertIsInstance(loaded_goal, goals.Dummy)


class TestLoadGoalsWithDefaultGoalLoader(base.TestCase):

    goal_loader = default_loading.DefaultGoalLoader()

    # test matrix (1 test execution per goal entry point)
    scenarios = [
        (goal_name,
         {"goal_name": goal_name, "goal_cls": goal_cls})
        for goal_name, goal_cls
        in goal_loader.list_available().items()]

    def test_load_goals(self):
        goal = self.goal_loader.load(self.goal_name)
        self.assertIsNotNone(goal)
        self.assertEqual(self.goal_name, goal.name)
