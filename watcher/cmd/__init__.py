#
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

# NOTE(licanwei): Do eventlet monkey patching here, instead of in
# common/service.py.  This allows the API service to run without monkey
# patching under Apache (which uses its own concurrency model). Mixing
# concurrency models can cause undefined behavior and potentially API timeouts.
import eventlet

eventlet.monkey_patch()
