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

from oslo_config import cfg
import wsme

from watcher.api.controllers.v1 import utils as v1_utils
from watcher.tests import base


class TestApiUtilsValidScenarios(base.TestCase):

    scenarios = [
        ("limit=None + max_limit=None",
            {"limit": None, "max_limit": None, "expected": None}),
        ("limit=None + max_limit=1",
            {"limit": None, "max_limit": 1, "expected": 1}),
        # ("limit=0 + max_limit=None",
        #     {"limit": 0, "max_limit": None, "expected": 0}),
        ("limit=1 + max_limit=None",
            {"limit": 1, "max_limit": None, "expected": 1}),
        ("limit=1 + max_limit=1",
            {"limit": 1, "max_limit": 1, "expected": 1}),
        ("limit=2 + max_limit=1",
            {"limit": 2, "max_limit": 1, "expected": 1}),
    ]

    def test_validate_limit(self):
        cfg.CONF.set_override("max_limit", self.max_limit, group="api")
        actual_limit = v1_utils.validate_limit(self.limit)
        self.assertEqual(self.expected, actual_limit)


class TestApiUtilsInvalidScenarios(base.TestCase):

    scenarios = [
        ("limit=0 + max_limit=None", {"limit": 0, "max_limit": None}),
    ]

    def test_validate_limit_invalid_cases(self):
        cfg.CONF.set_override("max_limit", self.max_limit, group="api")
        self.assertRaises(
            wsme.exc.ClientSideError, v1_utils.validate_limit, self.limit
        )
