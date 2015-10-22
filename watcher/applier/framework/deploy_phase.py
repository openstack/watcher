# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from watcher.openstack.common import log
LOG = log.getLogger(__name__)


class DeployPhase(object):
    def __init__(self, executor):
        # todo(jed) oslo_conf 10 secondes
        self.maxTimeout = 100000
        self.commands = []
        self.executor = executor

    def set_max_time(self, mt):
        self.maxTimeout = mt

    def get_max_time(self):
        return self.maxTimeout

    def populate(self, action):
        self.commands.append(action)

    def execute_primitive(self, primitive):
        futur = primitive.execute(primitive)
        return futur.result(self.get_max_time())

    def rollback(self):
        reverted = sorted(self.commands, reverse=True)
        for primitive in reverted:
            try:
                self.execute_primitive(primitive)
            except Exception as e:
                LOG.error(e)
