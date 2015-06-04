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


from watcher.decision_engine.framework.messaging.events import Events
from watcher.openstack.common import log

LOG = log.getLogger(__name__)


class EventDispatcher(object):
    """Generic event dispatcher which listen and dispatch events"""

    def __init__(self):
        self._events = dict()

    def __del__(self):
        self._events = None

    def has_listener(self, event_type, listener):
        """Return true if listener is register to event_type """
        # Check for event type and for the listener
        if event_type in self._events.keys():
            return listener in self._events[event_type]
        else:
            return False

    def dispatch_event(self, event):
        LOG.debug("dispatch evt : %s" % str(event.get_type()))
        """
        Dispatch an instance of Event class
        """
        if Events.ALL in self._events.keys():
            listeners = self._events[Events.ALL]
            for listener in listeners:
                listener(event)

        # Dispatch the event to all the associated listeners
        if event.get_type() in self._events.keys():
            listeners = self._events[event.get_type()]
            for listener in listeners:
                listener(event)

    def add_event_listener(self, event_type, listener):
        """Add an event listener for an event type"""
        # Add listener to the event type
        if not self.has_listener(event_type, listener):
            listeners = self._events.get(event_type, [])
            listeners.append(listener)
            self._events[event_type] = listeners

    def remove_event_listener(self, event_type, listener):
        """Remove event listener. """
        # Remove the listener from the event type
        if self.has_listener(event_type, listener):
            listeners = self._events[event_type]

            if len(listeners) == 1:
                # Only this listener remains so remove the key
                del self._events[event_type]

            else:
                # Update listeners chain
                listeners.remove(listener)
                self._events[event_type] = listeners
