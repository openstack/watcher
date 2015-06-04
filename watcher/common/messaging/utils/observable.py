# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from watcher.common.messaging.utils.synchronization import \
    Synchronization
from watcher.openstack.common import log

LOG = log.getLogger(__name__)


class Observable(Synchronization):
    def __init__(self):
        self.__observers = []
        self.changed = 0
        Synchronization.__init__(self)

    def set_changed(self):
        self.changed = 1

    def clear_changed(self):
        self.changed = 0

    def has_changed(self):
        return self.changed

    def register_observer(self, observer):
        if observer not in self.__observers:
            self.__observers.append(observer)

    def unregister_observer(self, observer):
        try:
            self.__observers.remove(observer)
        except ValueError:
            pass

    def notify(self, ctx=None, publisherid=None, event_type=None,
               metadata=None, payload=None, modifier=None):
        self.mutex.acquire()
        try:
            if not self.changed:
                return
            for observer in self.__observers:
                if modifier != observer:
                    observer.update(self, ctx, metadata, publisherid,
                                    event_type, payload)
            self.clear_changed()
        finally:
            self.mutex.release()
