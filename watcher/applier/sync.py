# -*- encoding: utf-8 -*-
# Copyright (c) 2017 ZTE
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

from watcher.applier.loading import default
from watcher.common import context
from watcher.common import exception
from watcher import objects


class Syncer(object):
    """Syncs all available actions with the Watcher DB"""

    def sync(self):
        ctx = context.make_context()
        action_loader = default.DefaultActionLoader()
        available_actions = action_loader.list_available()
        for action_type in available_actions.keys():
            load_action = action_loader.load(action_type)
            load_description = load_action.get_description()
            try:
                action_desc = objects.ActionDescription.get_by_type(
                    ctx, action_type)
                if action_desc.description != load_description:
                    action_desc.description = load_description
                    action_desc.save()
            except exception.ActionDescriptionNotFound:
                obj_action_desc = objects.ActionDescription(ctx)
                obj_action_desc.action_type = action_type
                obj_action_desc.description = load_description
                obj_action_desc.create()
