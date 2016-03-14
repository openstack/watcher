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

from oslotest.base import BaseTestCase
from stevedore.driver import DriverManager
from stevedore.extension import Extension

from watcher.common import exception
from watcher.common.loader.default import DefaultLoader
from watcher.tests.common.loader.FakeLoadable import FakeLoadable


class TestLoader(BaseTestCase):
    @mock.patch("watcher.common.loader.default.DriverManager")
    def test_load_driver_no_opt(self, m_driver_manager):
        m_driver_manager.return_value = DriverManager.make_test_instance(
            extension=Extension(name=FakeLoadable.get_name(),
                                entry_point="%s:%s" % (
                                FakeLoadable.__module__,
                                FakeLoadable.__name__),
                                plugin=FakeLoadable,
                                obj=None),
            namespace=FakeLoadable.namespace())

        loader_manager = DefaultLoader(namespace='TESTING')
        loaded_driver = loader_manager.load(name='fake')

        self.assertEqual(FakeLoadable.get_name(), loaded_driver.get_name())

    @mock.patch("watcher.common.loader.default.DriverManager")
    def test_load_driver_bad_plugin(self, m_driver_manager):
        m_driver_manager.side_effect = Exception()

        loader_manager = DefaultLoader(namespace='TESTING')
        self.assertRaises(exception.LoadingError, loader_manager.load,
                          name='bad_driver')
