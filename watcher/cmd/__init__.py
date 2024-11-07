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
# NOTE(sean-k-mooney) while ^ is true, since that was written asyncio was added
# to the code base in addition to apscheduler which provides native threads.
# As such we have a lot of technical debt to fix with regards to watchers
# concurrency model as we are mixing up to 3 models the same process.
# apscheduler does not technically support eventlet but it has mostly worked
# until now, apscheduler is used to provide a job schedulers which mixes
# monkey patched and non monkey patched code in the same process.
# That is problematic and can lead to errors on python 3.12+.
# The maas support added asyncio to the codebase which is unsafe to mix
# with eventlets by default.
from watcher import eventlet
eventlet.patch()
