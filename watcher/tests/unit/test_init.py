# Copyright 2025 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_service import backend

from watcher.tests.unit import base


class TestOsloServiceBackend(base.TestCase):
    def test_threading_backend_is_selected(self):
        # Importing the watcher package selects the backend, so by the time
        # any test runs it must already be the threading one. Anything that
        # imports oslo_service.service or oslo_service.loopingcall before
        # watcher would latch the eventlet default instead.
        self.assertEqual(
            backend.BackendType.THREADING, backend.get_backend_type()
        )
