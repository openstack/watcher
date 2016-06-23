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

from __future__ import unicode_literals

import mock

from oslo_config import cfg
from stevedore import driver as drivermanager
from stevedore import extension as stevedore_extension

from watcher.common import exception
from watcher.common.loader import default
from watcher.common.loader import loadable
from watcher.tests import base


class FakeLoadable(loadable.Loadable):

    @classmethod
    def get_config_opts(cls):
        return []


class FakeLoadableWithOpts(loadable.Loadable):

    @classmethod
    def get_config_opts(cls):
        return [
            cfg.StrOpt("test_opt", default="fake_with_opts"),
        ]


class TestLoader(base.TestCase):

    def setUp(self):
        super(TestLoader, self).setUp()

        def _fake_parse(self, *args, **kw):
            return cfg.ConfigOpts._parse_cli_opts(cfg.CONF, [])

        cfg.CONF._parse_cli_opts = _fake_parse

    def test_load_loadable_no_opt(self):
        fake_driver = drivermanager.DriverManager.make_test_instance(
            extension=stevedore_extension.Extension(
                name="fake",
                entry_point="%s:%s" % (FakeLoadable.__module__,
                                       FakeLoadable.__name__),
                plugin=FakeLoadable,
                obj=None),
            namespace="TESTING")

        loader_manager = default.DefaultLoader(namespace='TESTING')
        with mock.patch.object(drivermanager,
                               "DriverManager") as m_driver_manager:
            m_driver_manager.return_value = fake_driver
            loaded_driver = loader_manager.load(name='fake')

        self.assertIsInstance(loaded_driver, FakeLoadable)

    @mock.patch("watcher.common.loader.default.drivermanager.DriverManager")
    def test_load_loadable_bad_plugin(self, m_driver_manager):
        m_driver_manager.side_effect = Exception()

        loader_manager = default.DefaultLoader(namespace='TESTING')
        self.assertRaises(exception.LoadingError, loader_manager.load,
                          name='bad_driver')

    def test_load_loadable_with_opts(self):
        fake_driver = drivermanager.DriverManager.make_test_instance(
            extension=stevedore_extension.Extension(
                name="fake",
                entry_point="%s:%s" % (FakeLoadableWithOpts.__module__,
                                       FakeLoadableWithOpts.__name__),
                plugin=FakeLoadableWithOpts,
                obj=None),
            namespace="TESTING")

        loader_manager = default.DefaultLoader(namespace='TESTING')
        with mock.patch.object(drivermanager,
                               "DriverManager") as m_driver_manager:
            m_driver_manager.return_value = fake_driver
            loaded_driver = loader_manager.load(name='fake')

        self.assertIsInstance(loaded_driver, FakeLoadableWithOpts)

        self.assertEqual(
            "fake_with_opts", loaded_driver.config.get("test_opt"))

        self.assertEqual(
            "fake_with_opts", loaded_driver.config.test_opt)
