# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import os


MONKEY_PATCHED = False


def is_patched():
    return MONKEY_PATCHED


def _monkey_patch():
    if is_patched():
        return
    # Anything imported here will not be monkey patched. It is
    # important to take care not to import anything here which requires monkey
    # patching. eventlet processes environment variables at import-time.
    # as such any eventlet configuration should happen here if needed.
    import eventlet
    eventlet.monkey_patch()


def patch():
    # This is only for debugging, this should not be used in production.
    if (os.environ.get('OS_WATCHER_DISABLE_EVENTLET_PATCHING', '').lower()
            not in ('1', 'true', 'yes', 'y')):
        _monkey_patch()
        global MONKEY_PATCHED
        MONKEY_PATCHED = True
