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

from oslo_log import log

from watcher.applier.primitive.base import PrimitiveCommand
from watcher.applier.promise import Promise


LOG = log.getLogger(__name__)


class NopCommand(PrimitiveCommand):
    def __init__(self):
        pass

    @Promise
    def execute(self):
        LOG.debug("executing NOP command")
        return True

    @Promise
    def undo(self):
        LOG.debug("undo NOP command")
        return True
