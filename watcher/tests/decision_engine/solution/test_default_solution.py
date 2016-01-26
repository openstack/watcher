# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
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

from watcher.decision_engine.solution import default
from watcher.tests import base


class TestDefaultSolution(base.BaseTestCase):
    def test_default_solution(self):
        solution = default.DefaultSolution()
        parameters = {
            "src_uuid_hypervisor": "server1",
            "dst_uuid_hypervisor": "server2",
        }
        solution.add_action(action_type="nop",
                            resource_id="b199db0c-1408-4d52-b5a5-5ca14de0ff36",
                            input_parameters=parameters)
        self.assertEqual(len(solution.actions), 1)
        expected_action_type = "nop"
        expected_parameters = {
            "src_uuid_hypervisor": "server1",
            "dst_uuid_hypervisor": "server2",
            "resource_id": "b199db0c-1408-4d52-b5a5-5ca14de0ff36"
        }
        self.assertEqual(solution.actions[0].get('action_type'),
                         expected_action_type)
        self.assertEqual(solution.actions[0].get('input_parameters'),
                         expected_parameters)
