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

from oslo_log import log
from oslo_service import backend

from watcher import eventlet as eventlet_helper

LOG = log.getLogger(__name__)


def init_oslo_service_backend():
    if eventlet_helper.is_patched():
        backend.init_backend(backend.BackendType.EVENTLET)
        LOG.warning(
            "Service is starting with Eventlet based service backend.")
    else:
        backend.init_backend(backend.BackendType.THREADING)
        LOG.warning(
            "Service is starting with Threading based service backend. "
            "This is an experimental feature, do not use it in production.")
