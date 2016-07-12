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

import mock
from stevedore import extension

from watcher import opts
from watcher.tests import base
from watcher.tests.decision_engine import fake_strategies


class TestListOpts(base.TestCase):
    def setUp(self):
        super(TestListOpts, self).setUp()
        self.base_sections = [
            'api', 'watcher_decision_engine', 'watcher_applier',
            'watcher_planner', 'nova_client', 'glance_client',
            'cinder_client', 'ceilometer_client', 'neutron_client',
            'watcher_clients_auth', 'watcher_planners.default']

    def test_run_list_opts(self):
        expected_sections = self.base_sections

        result = opts.list_opts()

        self.assertIsNotNone(result)
        for section_name, options in result:
            self.assertIn(section_name, expected_sections)
            self.assertTrue(len(options))

    def test_list_opts_no_opts(self):
        expected_sections = self.base_sections
        # Set up the fake Stevedore extensions
        fake_extmanager_call = extension.ExtensionManager.make_test_instance(
            extensions=[extension.Extension(
                name=fake_strategies.FakeDummy1Strategy2.get_name(),
                entry_point="%s:%s" % (
                    fake_strategies.FakeDummy1Strategy2.__module__,
                    fake_strategies.FakeDummy1Strategy2.__name__),
                plugin=fake_strategies.FakeDummy1Strategy2,
                obj=None,
            )],
            namespace="watcher_strategies",
        )

        def m_list_available(namespace):
            if namespace == "watcher_strategies":
                return fake_extmanager_call
            else:
                return extension.ExtensionManager.make_test_instance(
                    extensions=[], namespace=namespace)

        with mock.patch.object(extension, "ExtensionManager") as m_ext_manager:
            m_ext_manager.side_effect = m_list_available
            result = opts.list_opts()

        self.assertIsNotNone(result)
        for section_name, options in result:
            self.assertIn(section_name, expected_sections)
            self.assertTrue(len(options))

    def test_list_opts_with_opts(self):
        expected_sections = self.base_sections + [
            'watcher_strategies.strategy_1']
        # Set up the fake Stevedore extensions
        fake_extmanager_call = extension.ExtensionManager.make_test_instance(
            extensions=[extension.Extension(
                name=fake_strategies.FakeDummy1Strategy1.get_name(),
                entry_point="%s:%s" % (
                    fake_strategies.FakeDummy1Strategy1.__module__,
                    fake_strategies.FakeDummy1Strategy1.__name__),
                plugin=fake_strategies.FakeDummy1Strategy1,
                obj=None,
            )],
            namespace="watcher_strategies",
        )

        def m_list_available(namespace):
            if namespace == "watcher_strategies":
                return fake_extmanager_call
            else:
                return extension.ExtensionManager.make_test_instance(
                    extensions=[], namespace=namespace)

        with mock.patch.object(extension, "ExtensionManager") as m_ext_manager:
            m_ext_manager.side_effect = m_list_available
            result = opts.list_opts()

        self.assertIsNotNone(result)
        for section_name, options in result:
            self.assertIn(section_name, expected_sections)
            self.assertTrue(len(options))

        result_map = dict(result)
        strategy_opts = result_map['watcher_strategies.strategy_1']
        self.assertEqual(['test_opt'], [opt.name for opt in strategy_opts])


class TestPlugins(base.TestCase):

    def test_show_plugins(self):
        # Set up the fake Stevedore extensions
        fake_extmanager_call = extension.ExtensionManager.make_test_instance(
            extensions=[extension.Extension(
                name=fake_strategies.FakeDummy1Strategy1.get_name(),
                entry_point="%s:%s" % (
                    fake_strategies.FakeDummy1Strategy1.__module__,
                    fake_strategies.FakeDummy1Strategy1.__name__),
                plugin=fake_strategies.FakeDummy1Strategy1,
                obj=None,
            )],
            namespace="watcher_strategies",
        )

        def m_list_available(namespace):
            if namespace == "watcher_strategies":
                return fake_extmanager_call
            else:
                return extension.ExtensionManager.make_test_instance(
                    extensions=[], namespace=namespace)

        with mock.patch.object(extension, "ExtensionManager") as m_ext_manager:
            with mock.patch.object(
                opts, "_show_plugins_ascii_table"
            ) as m_show:
                m_ext_manager.side_effect = m_list_available
                opts.show_plugins()
                m_show.assert_called_once_with(
                    [('watcher_strategies.strategy_1', 'strategy_1',
                      'watcher.tests.decision_engine.'
                      'fake_strategies.FakeDummy1Strategy1')])
