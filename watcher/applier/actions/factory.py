# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
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

from watcher.applier.loading import default

LOG = log.getLogger(__name__)


class ActionFactory(object):
    def __init__(self):
        self.action_loader = default.DefaultActionLoader()

    def make_action(self, object_action, osc=None):
        LOG.debug("Creating instance of %s", object_action.action_type)
        loaded_action = self.action_loader.load(name=object_action.action_type,
                                                osc=osc)
        loaded_action.input_parameters = object_action.input_parameters
        LOG.debug("Checking the input parameters")
        # NOTE(jed) if we change the schema of an action and we try to reload
        # an older version of the Action, the validation can fail.
        # We need to add the versioning of an Action or a migration tool.
        # We can also create an new Action which extends the previous one.
        loaded_action.validate_parameters()
        return loaded_action
