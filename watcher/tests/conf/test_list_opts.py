# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
# Copyright (c) 2016 Intel Corp
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

from unittest import mock

from oslo_config import cfg
from stevedore import extension

from watcher.conf import opts
from watcher.conf import plugins
from watcher.tests import base
from watcher.tests.decision_engine import fake_strategies


class TestListOpts(base.TestCase):
    def setUp(self):
        super(TestListOpts, self).setUp()
        # These option groups will be registered using strings instead of
        # OptGroup objects this should be avoided if possible.
        self.none_objects = ['DEFAULT', 'watcher_clients_auth',
                             'watcher_strategies.strategy_1']

        self.base_sections = [
            'DEFAULT', 'api', 'database', 'watcher_decision_engine',
            'watcher_applier', 'watcher_datasources', 'watcher_planner',
            'nova_client', 'glance_client', 'gnocchi_client', 'grafana_client',
            'grafana_translators', 'cinder_client',
            'monasca_client', 'ironic_client', 'keystone_client',
            'neutron_client', 'watcher_clients_auth', 'collector',
            'placement_client']
        self.opt_sections = list(dict(opts.list_opts()).keys())

    def _assert_name_or_group(self, actual_sections, expected_sections):
        for name_or_group, options in actual_sections:
            section_name = name_or_group
            if isinstance(name_or_group, cfg.OptGroup):
                section_name = name_or_group.name
            elif section_name in self.none_objects:
                pass
            else:
                # All option groups should be added to list_otps with an
                # OptGroup object for some exceptions this is not possible but
                # new groups should use OptGroup
                raise Exception(
                    "Invalid option group: {0} should be of type OptGroup not "
                    "string.".format(section_name))

        self.assertIn(section_name, expected_sections)
        self.assertTrue(len(options))

    def test_run_list_opts(self):
        expected_sections = self.opt_sections

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
            self._assert_name_or_group(result, expected_sections)

        self.assertIsNotNone(result)

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
        self._assert_name_or_group(result, expected_sections)

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
                plugins, "_show_plugins_ascii_table"
            ) as m_show:
                m_ext_manager.side_effect = m_list_available
                plugins.show_plugins()
                m_show.assert_called_once_with(
                    [('watcher_strategies.strategy_1', 'strategy_1',
                      'watcher.tests.decision_engine.'
                      'fake_strategies.FakeDummy1Strategy1')])
