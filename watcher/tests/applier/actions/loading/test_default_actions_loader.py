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

from watcher.applier.actions import base as abase
from watcher.applier.loading import default
from watcher.tests import base


class TestDefaultActionLoader(base.TestCase):
    def setUp(self):
        super(TestDefaultActionLoader, self).setUp()
        self.loader = default.DefaultActionLoader()

    def test_endpoints(self):
        for endpoint in self.loader.list_available():
            loaded = self.loader.load(endpoint)
            self.assertIsNotNone(loaded)
            self.assertIsInstance(loaded, abase.BaseAction)
