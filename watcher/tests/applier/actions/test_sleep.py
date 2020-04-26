# Copyright (c) 2016 b<>com
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import jsonschema
from unittest import mock

from watcher.applier.actions import sleep
from watcher.tests import base


class TestSleep(base.TestCase):
    def setUp(self):
        super(TestSleep, self).setUp()
        self.s = sleep.Sleep(mock.Mock())

    def test_parameters_duration(self):
        self.s.input_parameters = {self.s.DURATION: 1.0}
        self.assertTrue(self.s.validate_parameters())

    def test_parameters_duration_empty(self):
        self.s.input_parameters = {self.s.DURATION: None}
        self.assertRaises(jsonschema.ValidationError,
                          self.s.validate_parameters)

    def test_parameters_wrong_parameter(self):
        self.s.input_parameters = {self.s.DURATION: "ef"}
        self.assertRaises(jsonschema.ValidationError,
                          self.s.validate_parameters)

    def test_parameters_add_field(self):
        self.s.input_parameters = {self.s.DURATION: 1.0, "not_required": "nop"}
        self.assertRaises(jsonschema.ValidationError,
                          self.s.validate_parameters)
