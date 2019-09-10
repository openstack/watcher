# -*- encoding: utf-8 -*-
# Copyright (c) 2017 b<>com
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

from watcher._i18n import _
from watcher.decision_engine.strategy.strategies import base


class Actuator(base.UnclassifiedStrategy):
    """Actuator

    Actuator that simply executes the actions given as parameter

    This strategy allows anyone to create an action plan with a predefined
    set of actions. This strategy can be used for 2 different purposes:

    - Test actions
    - Use this strategy based on an event trigger to perform some explicit task

    """

    @classmethod
    def get_name(cls):
        return "actuator"

    @classmethod
    def get_display_name(cls):
        return _("Actuator")

    @classmethod
    def get_translatable_display_name(cls):
        return "Actuator"

    @classmethod
    def get_schema(cls):
        # Mandatory default setting for each element
        return {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "type": "object",
            "properties": {
                "actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action_type": {
                                "type": "string"
                            },
                            "resource_id": {
                                "type": "string"
                            },
                            "input_parameters": {
                                "type": "object",
                                "properties": {},
                                "additionalProperties": True
                            }
                        },
                        "required": [
                            "action_type", "input_parameters"
                        ],
                        "additionalProperties": True,
                    }
                }
            },
            "required": [
                "actions"
            ]
        }

    @classmethod
    def get_config_opts(cls):
        """Override base class config options as do not use datasource """

        return []

    @property
    def actions(self):
        return self.input_parameters.get('actions', [])

    def pre_execute(self):
        self._pre_execute()

    def do_execute(self, audit=None):
        for action in self.actions:
            self.solution.add_action(**action)

    def post_execute(self):
        pass
