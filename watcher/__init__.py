# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import pbr.version

from oslo_service import backend


# NOTE(dviroel): the oslo service backend has to be selected before
# anything imports oslo_service.service or oslo_service.loopingcall:
# those modules resolve their components at import time and silently
# fall back to the EVENTLET default. Doing it in the top level package
# guarantees it runs before any other watcher module. It can be removed
# once oslo changes the default to THREADING.
backend.init_backend(backend.BackendType.THREADING)

__version__ = pbr.version.VersionInfo('python-watcher').version_string()
