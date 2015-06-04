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
from watcher.common.messaging.messaging_core import MessagingCore
from watcher.decision_engine.api.selector.selector import Selector


class ClientSelectorStrategy(Selector, MessagingCore):

    """Trigger an audit (a request for optimizing a cluster)
    :param goal: the strategy selected by the strategy selector
    :param hosts:  the list of hypervisors where a nova-compute service
    is running (host aggregate)
    :return: None
    """
    def launch_audit(self, goal):
        # TODO(jed):
        # client = ClientScheduler()
        pass
