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

from unittest import mock

from oslo_service import backend

from watcher.common import oslo_service_helper
from watcher import eventlet as eventlet_helper
from watcher.tests.unit import base


class TestOsloServiceHelper(base.TestCase):

    @mock.patch.object(eventlet_helper, 'is_patched')
    @mock.patch.object(backend, 'init_backend')
    def test_init_oslo_backend_eventlet(self, mock_init_backend,
                                        mock_is_patched):

        mock_is_patched.return_value = True

        oslo_service_helper.init_oslo_service_backend()

        mock_init_backend.assert_called_once_with(
            backend.BackendType.EVENTLET
        )

    @mock.patch.object(eventlet_helper, 'is_patched')
    @mock.patch.object(backend, 'init_backend')
    def test_init_oslo_backend_threading(self, mock_init_backend,
                                         mock_is_patched):

        mock_is_patched.return_value = False

        oslo_service_helper.init_oslo_service_backend()

        mock_init_backend.assert_called_once_with(
            backend.BackendType.THREADING
        )
