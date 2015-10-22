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

from watcher.decision_engine.api.solution.solution import Solution as sol
from watcher.decision_engine.api.solution.solution_comparator import Solution
from watcher.tests import base


class test_Solution_Comparator(base.TestCase):
    def test_compare(self):
        sol1 = sol()
        sol2 = sol()
        solution_comparator = Solution()
        self.assertRaises(NotImplementedError,
                          solution_comparator.compare,
                          sol1,
                          sol2)
