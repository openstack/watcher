# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
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
#
from watcher.decision_engine.model import compute_resource
from watcher.tests import base


class TestNamedElement(base.BaseTestCase):
    def test_namedelement(self):
        id = compute_resource.ComputeResource()
        id.uuid = "BLABLABLA"
        self.assertEqual("BLABLABLA", id.uuid)

    def test_set_get_human_id(self):
        id = compute_resource.ComputeResource()
        id.human_id = "BLABLABLA"
        self.assertEqual("BLABLABLA", id.human_id)
